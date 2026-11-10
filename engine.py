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

