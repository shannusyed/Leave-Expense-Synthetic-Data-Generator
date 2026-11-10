"""
engine.py – Rule-driven decision engine for leave and expense approvals.

Every approval / rejection decision is deterministic: it is computed from
the data, not randomly chosen.  Random numbers are only used to *generate*
the synthetic inputs; once the inputs exist, the engine applies pure
business rules.

Public API
----------
decide_leave(request, employee, balances, all_approved_leaves, holidays)
    → (status, reason_code, reason_text)

decide_expense_claim(claim, lines, employee, policy_map, all_reimbursements)
    → (status, reason_code, reason_text, line_issues)

route_approval(entity_type, value, days=None)
    → list of approver roles

compute_business_days(start, end, holidays)
    → int
"""

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import config as cfg

# ── Holiday helpers ─────────────────────────────────────────────────

_HOLIDAYS_SET = frozenset(date.fromisoformat(h) for h in cfg.HOLIDAYS)


def is_business_day(d: date) -> bool:
    return d.weekday() < 5 and d not in _HOLIDAYS_SET


def compute_business_days(start: date, end: date) -> int:
    """Count of business days in [start, end] inclusive."""
    if end < start:
        return 0
    count = 0
    cur = start
    while cur <= end:
        if is_business_day(cur):
            count += 1
        cur += timedelta(days=1)
    return count


def spans_holiday(start: date, end: date) -> bool:
    """True if the date range [start, end] includes at least one holiday."""
    cur = start
    while cur <= end:
        if cur in _HOLIDAYS_SET:
            return True
        cur += timedelta(days=1)
    return False


# ── Approval routing ────────────────────────────────────────────────

def route_leave_approval(days: int) -> List[str]:
    """Return the ordered list of approver roles for a leave request."""
    if days <= 3:
        return ["Manager"]
    elif days <= 7:
        return ["Manager", "Senior Manager"]
    else:
        return ["Manager", "Senior Manager", "Director"]


def route_expense_approval(total_amount: float) -> List[str]:
    """Return the ordered list of approver roles for an expense claim."""
    if total_amount <= 5000:
        return ["Manager"]
    elif total_amount <= 20000:
        return ["Manager", "Senior Manager"]
    else:
        return ["Manager", "Senior Manager", "Director"]


# ── Leave decision engine ──────────────────────────────────────────

def decide_leave(
    request: dict,
    employee: dict,
    balance_remaining: float,
    approved_leaves: List[dict],
    policy: dict,
) -> Tuple[str, str, str]:
    """
    Evaluate a leave request against business rules.

    Parameters
    ----------
    request : dict with keys start_date, end_date, leave_type, employee_id,
              applied_date, days_requested
    employee : dict with keys employee_id, hire_date, termination_date,
               designation, manager_id
    balance_remaining : float – current balance for this leave type
    approved_leaves : list[dict] – already-approved leaves for same employee
    policy : dict – the leave policy row

    Returns
    -------
    (final_status, reason_code, reason_text)
    """
    start = request["start_date"]
    end   = request["end_date"]
    days  = request["days_requested"]
    applied = request["applied_date"]

    # Rule 1 – Employment dates
    hire = employee["hire_date"]
    term = employee.get("termination_date")
    if start < hire:
        return ("Rejected", "BEFORE_HIRE", f"Leave starts before hire date {hire}")
    if term and end > term:
        return ("Rejected", "AFTER_TERMINATION", f"Leave extends past termination date {term}")

    # Rule 2 – Self-approval (flagged but not auto-rejected; engine records it)
    # Self-approval is an anomaly — it should still be decided by other rules.

    # Rule 3 – Insufficient balance
    if days > balance_remaining:
        return ("Rejected", "INSUFFICIENT_BALANCE",
                f"Requested {days} days but only {balance_remaining} available")

    # Rule 4 – Exceeds max consecutive days
    max_consec = policy["max_consecutive_days"]
    if days > max_consec:
        return ("Rejected", "EXCEEDS_MAX_CONSECUTIVE",
                f"Requested {days} days exceeds max consecutive {max_consec}")

    # Rule 5 – Notice period violation
    min_notice = policy["min_notice_days"]
    if min_notice > 0:
        notice_given = (start - applied).days
        if notice_given < min_notice:
            return ("Rejected", "INSUFFICIENT_NOTICE",
                    f"Notice {notice_given}d < required {min_notice}d")

    # Rule 6 – Overlapping approved leave
    for prev in approved_leaves:
        if prev["leave_request_id"] == request.get("leave_request_id"):
            continue
        if start <= prev["end_date"] and end >= prev["start_date"]:
            return ("Rejected", "OVERLAPPING_LEAVE",
                    f"Overlaps with approved leave {prev['leave_request_id']}")

    return ("Approved", "RULES_PASSED", "All business rules satisfied")


# ── Expense decision engine ────────────────────────────────────────

def evaluate_expense_lines(
    lines: List[dict],
    policy_map: Dict[str, dict],
) -> List[dict]:
    """
    Check each expense line against its category policy.

    Returns a list of issue dicts (empty list = all lines OK).
    Each issue: {line_id, issue_type, description}
    """
    issues = []
    for ln in lines:
        cat = ln["category"]
        pol = policy_map.get(cat)
        if not pol:
            issues.append({
                "line_id": ln["expense_line_id"],
                "issue_type": "UNKNOWN_CATEGORY",
                "description": f"No policy for category '{cat}'",
            })
            continue

        # Single-receipt limit breach
        if ln["amount"] > pol["single_receipt_limit"]:
            issues.append({
                "line_id": ln["expense_line_id"],
                "issue_type": "POLICY_LIMIT_BREACH",
                "description": (f"Amount {ln['amount']:.2f} > limit "
                                f"{pol['single_receipt_limit']} for {cat}"),
            })

        # Missing receipt when required
        if ln["amount"] > pol["receipt_required_above"] and not ln["has_receipt"]:
            issues.append({
                "line_id": ln["expense_line_id"],
                "issue_type": "MISSING_RECEIPT",
                "description": (f"Receipt required for {cat} above "
                                f"{pol['receipt_required_above']} but missing"),
            })

    return issues


def decide_expense_claim(
    claim: dict,
    lines: List[dict],
    employee: dict,
    policy_map: Dict[str, dict],
) -> Tuple[str, str, str, List[dict]]:
    """
    Evaluate an expense claim and its lines.

    Returns
    -------
    (final_status, reason_code, reason_text, line_issues)
    """
    # Rule 1 – Employment date check
    claim_date = claim["claim_date"]
    hire = employee["hire_date"]
    term = employee.get("termination_date")
    if claim_date < hire:
        return ("Rejected", "BEFORE_HIRE",
                f"Claim date before hire {hire}", [])
    if term and claim_date > term:
        return ("Rejected", "AFTER_TERMINATION",
                f"Claim date after termination {term}", [])

    # Rule 2 – Missing cost center
    if not claim.get("cost_center_id"):
        return ("Rejected", "MISSING_COST_CENTER",
                "No cost center assigned", [])

    # Rule 3 – Line-level issues
    line_issues = evaluate_expense_lines(lines, policy_map)
    blocking = [i for i in line_issues
                if i["issue_type"] in ("POLICY_LIMIT_BREACH", "MISSING_RECEIPT",
                                        "UNKNOWN_CATEGORY")]
    if blocking:
        return ("Rejected", "LINE_POLICY_VIOLATION",
                f"{len(blocking)} line(s) violate policy", line_issues)

    # Rule 4 – Duplicate receipt hash detection is done at injection time
    # and flagged in ground_truth; the engine sees the has_receipt field.

    return ("Approved", "RULES_PASSED", "All business rules satisfied", line_issues)


def should_create_reimbursement(claim_status: str) -> bool:
    """Reimbursement is only created for fully approved claims."""
    return claim_status == "Approved"



# ══════════════════════════════════════════════════════════════════════
# RUNTIME ANOMALY DETECTION
# ══════════════════════════════════════════════════════════════════════
# These functions detect anomalies in operational data at runtime,
# complementing the ground-truth labels generated during data creation.

def detect_duplicate_receipts(
    claims: List[dict],
    lines: List[dict],
) -> List[dict]:
    """
    Find expense lines with identical receipt hashes across different claims.
    
    Returns list of anomalies: [
        {
            "anomaly_type": "duplicate_receipt",
            "severity": "HIGH",
            "line_ids": ["EL00120", "EL00095"],
            "claim_ids": ["EC0040", "EC0035"],
            "receipt_hash": "abc123def456...",
            "description": "Same receipt used on 2 different claims"
        }
    ]
    """
    anomalies = []
    receipt_index = {}  # receipt_hash → [(claim_id, line_id, amount), ...]
    
    for line in lines:
        if not line.get("has_receipt") or not line.get("receipt_hash"):
            continue
        receipt = line["receipt_hash"]
        claim_id = line["claim_id"]
        line_id = line["expense_line_id"]
        amount = float(line.get("amount", 0))
        
        if receipt not in receipt_index:
            receipt_index[receipt] = []
        receipt_index[receipt].append((claim_id, line_id, amount))
    
    # Flag duplicates
    for receipt_hash, entries in receipt_index.items():
        if len(entries) > 1:
            line_ids = [e[1] for e in entries]
            claim_ids = list(set(e[0] for e in entries))
            amounts = [e[2] for e in entries]
            
            anomalies.append({
                "anomaly_type": "duplicate_receipt",
                "severity": "HIGH",
                "line_ids": line_ids,
                "claim_ids": claim_ids,
                "receipt_hash": receipt_hash,
                "amount_variance": max(amounts) - min(amounts),
                "count": len(entries),
                "description": f"Receipt {receipt_hash[:8]}... used on {len(entries)} lines across {len(claim_ids)} claims"
            })
    
    return anomalies


def detect_split_claims(
    claims: List[dict],
    lines: List[dict],
) -> List[dict]:
    """
    Detect claims split to evade approval thresholds.
    
    Logic: Group claims by (employee, cost_center) within 7 days.
    If group total > 20k threshold AND individual claims ≤ 20k → suspicious.
    """
    from datetime import timedelta, date as dt_date
    from collections import defaultdict
    
    anomalies = []
    
    # Group by (employee, cost_center) within 7-day window
    groups = defaultdict(list)
    for claim in sorted(claims, key=lambda c: c["claim_date"]):
        emp_id = claim["employee_id"]
        cc_id = claim.get("cost_center_id", "")
        claim_date = claim["claim_date"]
        key = (emp_id, cc_id)
        
        # Parse date string if needed
        if isinstance(claim_date, str):
            claim_date = dt_date.fromisoformat(claim_date)
        
        # Add to group if within 7 days of last claim in group
        if key in groups:
            last_date = groups[key][-1][1]  # (claim_dict, date)
            if (claim_date - last_date).days <= 7:
                groups[key].append((claim, claim_date))
            else:
                # Start new group
                groups[key] = [(claim, claim_date)]
        else:
            groups[key] = [(claim, claim_date)]
    
    # Analyze groups for suspicious splits
    for (emp_id, cc_id), group_pairs in groups.items():
        if len(group_pairs) < 2:
            continue
        
        group_claims = [g[0] for g in group_pairs]
        total_amount = sum(float(c.get("total_amount", 0)) for c in group_claims)
        individual_max = max(float(c.get("total_amount", 0)) for c in group_claims)
        
        # Threshold for 3-level approval is 20000
        if individual_max <= 20000 and total_amount > 20000:
            claim_ids = [c["claim_id"] for c in group_claims]
            date_range = f"{group_pairs[0][1]} to {group_pairs[-1][1]}"
            anomalies.append({
                "anomaly_type": "split_claim",
                "severity": "MEDIUM",
                "claim_ids": claim_ids,
                "employee_id": emp_id,
                "cost_center_id": cc_id,
                "individual_max": individual_max,
                "group_total": total_amount,
                "count": len(group_claims),
                "date_range": date_range,
                "description": f"{len(group_claims)} claims totaling ₹{total_amount:.0f} (individual max ₹{individual_max:.0f}; threshold ₹20,000)"
            })
    
    return anomalies


def detect_self_approval(
    approval_steps: List[dict],
    claims: List[dict],
    employees: List[dict],
) -> List[dict]:
    """
    Detect where employee is their own approver.
    """
    anomalies = []
    emp_lookup = {e["employee_id"]: e for e in employees}
    
    for claim in claims:
        emp_id = claim["employee_id"]
        emp = emp_lookup.get(emp_id)
        if not emp:
            continue
        
        # Find first approval step (step_order=1)
        first_step = next(
            (s for s in approval_steps 
             if s["entity_id"] == claim["claim_id"] and str(s["step_order"]) == "1"),
            None
        )
        if not first_step:
            continue
        
        if first_step["approver_id"] == emp_id:
            anomalies.append({
                "anomaly_type": "self_approval",
                "severity": "HIGH",
                "employee_id": emp_id,
                "claim_id": claim["claim_id"],
                "approver_role": first_step.get("approver_role", "Manager"),
                "description": f"Employee {emp_id} is first-level approver for their own claim {claim['claim_id']}"
            })
    
    return anomalies


def detect_duplicate_reimbursements(
    reimbursements: List[dict],
) -> List[dict]:
    """
    Detect same claim reimbursed multiple times.
    """
    anomalies = []
    claim_count = {}
    
    for reimb in reimbursements:
        claim_id = reimb["claim_id"]
        if claim_id not in claim_count:
            claim_count[claim_id] = []
        claim_count[claim_id].append(reimb["reimbursement_id"])
    
    for claim_id, reimb_ids in claim_count.items():
        if len(reimb_ids) > 1:
            anomalies.append({
                "anomaly_type": "duplicate_reimbursement",
                "severity": "CRITICAL",
                "claim_id": claim_id,
                "reimbursement_ids": reimb_ids,
                "count": len(reimb_ids),
                "description": f"Claim {claim_id} reimbursed {len(reimb_ids)} times: {', '.join(reimb_ids)}"
            })
    
    return anomalies


def run_all_anomaly_detection(
    employees: List[dict],
    claims: List[dict],
    lines: List[dict],
    approval_steps: List[dict],
    reimbursements: List[dict],
) -> dict:
    """
    Run all anomaly detection checks and return comprehensive results.
    
    Returns: {
        "duplicate_receipts": [...],
        "split_claims": [...],
        "self_approvals": [...],
        "duplicate_reimbursements": [...],
        "total_anomalies": int,
        "summary": str
    }
    """
    results = {
        "duplicate_receipts": detect_duplicate_receipts(claims, lines),
        "split_claims": detect_split_claims(claims, lines),
        "self_approvals": detect_self_approval(approval_steps, claims, employees),
        "duplicate_reimbursements": detect_duplicate_reimbursements(reimbursements),
    }
    
    total = sum(len(v) for k, v in results.items() if k not in ["summary", "total_anomalies"])
    results["total_anomalies"] = total
    results["summary"] = (
        f"Detected {total} runtime anomalies: "
        f"{len(results['duplicate_receipts'])} duplicate receipts, "
        f"{len(results['split_claims'])} split claims, "
        f"{len(results['self_approvals'])} self-approvals, "
        f"{len(results['duplicate_reimbursements'])} duplicate reimbursements"
    )
    
    return results
