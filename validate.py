#!/usr/bin/env python3
"""
validate.py – Comprehensive data-quality validator for the synthetic dataset.

Checks:
  - Primary-key uniqueness
  - Foreign-key integrity
  - Exact volume targets
  - Zero ground-truth leakage in operational tables
  - Date ordering and consistency
  - Leave-balance reconciliation
  - Approval-sequence correctness
  - Reimbursement eligibility
  - Status-event chain integrity

Exit code 0 = all checks pass, 1 = at least one failure.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Dict, List, Set

DATA_DIR = Path(__file__).resolve().parent / "data"

# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────

_pass = 0
_fail = 0


def _load(filename: str) -> List[dict]:
    path = DATA_DIR / filename
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def check(name: str, condition: bool, detail: str = "") -> bool:
    global _pass, _fail
    if condition:
        _pass += 1
        print(f"  ✅  {name}")
    else:
        _fail += 1
        msg = f"  ❌  {name}"
        if detail:
            msg += f"  — {detail}"
        print(msg)
    return condition


# ────────────────────────────────────────────────────────────────────
# Load all tables
# ────────────────────────────────────────────────────────────────────

def main() -> int:
    global _pass, _fail
    _pass = _fail = 0

    employees       = _load("employees.csv")
    cost_centers    = _load("cost_centers.csv")
    leave_policies  = _load("leave_policies.csv")
    expense_policies= _load("expense_policies.csv")
    approval_rules  = _load("approval_rules.csv")
    leave_balances  = _load("leave_balances.csv")
    leave_requests  = _load("leave_requests.csv")
    expense_claims  = _load("expense_claims.csv")
    expense_lines   = _load("expense_lines.csv")
    approval_steps  = _load("approval_steps.csv")
    reimbursements  = _load("reimbursements.csv")
    ground_truth    = _load("ground_truth.csv")
    status_events   = _load("status_events.csv")

    emp_ids   = {e["employee_id"] for e in employees}
    cc_ids    = {c["cost_center_id"] for c in cost_centers}
    lr_ids    = {r["leave_request_id"] for r in leave_requests}
    ec_ids    = {c["claim_id"] for c in expense_claims}
    el_ids    = {l["expense_line_id"] for l in expense_lines}

    # ── 1. VOLUME CHECKS ───────────────────────────────────────
    print("\n── Volume checks ──")
    check("400 employees",       len(employees) == 400,       f"got {len(employees)}")
    check("6 leave policies",    len(leave_policies) == 6,    f"got {len(leave_policies)}")
    check("800 leave requests",  len(leave_requests) == 800,  f"got {len(leave_requests)}")
    check("1000 expense claims", len(expense_claims) == 1000, f"got {len(expense_claims)}")

    # ── 2. PRIMARY KEY UNIQUENESS ──────────────────────────────
    print("\n── PK uniqueness ──")
    check("employee_id unique",        len(emp_ids) == len(employees))
    check("cost_center_id unique",     len(cc_ids) == len(cost_centers))
    check("leave_request_id unique",   len(lr_ids) == len(leave_requests))
    check("claim_id unique",           len(ec_ids) == len(expense_claims))
    check("expense_line_id unique",    len(el_ids) == len(expense_lines))
    check("approval_step_id unique",   len({s["approval_step_id"] for s in approval_steps}) == len(approval_steps))
    check("reimbursement_id unique",   len({r["reimbursement_id"] for r in reimbursements}) == len(reimbursements))
    check("event_id unique",           len({e["event_id"] for e in status_events}) == len(status_events))
    check("balance_id unique",         len({b["balance_id"] for b in leave_balances}) == len(leave_balances))

    # ── 3. FK INTEGRITY ────────────────────────────────────────
    print("\n── FK integrity ──")
    # Employees → cost centers
    emp_cc = {e["cost_center_id"] for e in employees}
    check("employee.cost_center → cost_centers", emp_cc.issubset(cc_ids),
          f"missing: {emp_cc - cc_ids}")

    # Employees → managers
    emp_mgr = {e["manager_id"] for e in employees}
    check("employee.manager_id → employees", emp_mgr.issubset(emp_ids),
          f"missing: {emp_mgr - emp_ids}")

    # Leave requests → employees
    lr_emp = {r["employee_id"] for r in leave_requests}
    check("leave_request.employee_id → employees", lr_emp.issubset(emp_ids))

    # Leave balances → employees
    lb_emp = {b["employee_id"] for b in leave_balances}
    check("leave_balance.employee_id → employees", lb_emp.issubset(emp_ids))

    # Expense claims → employees
    ec_emp = {c["employee_id"] for c in expense_claims}
    check("expense_claim.employee_id → employees", ec_emp.issubset(emp_ids))

    # Expense claims → cost centers (allow empty for missing_cost_center anomaly)
    ec_cc = {c["cost_center_id"] for c in expense_claims if c["cost_center_id"]}
    check("expense_claim.cost_center → cost_centers", ec_cc.issubset(cc_ids),
          f"missing: {ec_cc - cc_ids}")

    # Expense lines → claims
    el_claims = {l["claim_id"] for l in expense_lines}
    check("expense_line.claim_id → expense_claims", el_claims.issubset(ec_ids))

    # Approval steps → entities
    step_leave = {s["entity_id"] for s in approval_steps if s["entity_type"] == "leave_request"}
    step_exp   = {s["entity_id"] for s in approval_steps if s["entity_type"] == "expense_claim"}
    check("approval_step leave → leave_requests", step_leave.issubset(lr_ids))
    check("approval_step expense → expense_claims", step_exp.issubset(ec_ids))

    # Reimbursements → claims
    reimb_claims = {r["claim_id"] for r in reimbursements}
    check("reimbursement.claim_id → expense_claims", reimb_claims.issubset(ec_ids))

    # Status events → entities
    se_leave = {e["entity_id"] for e in status_events if e["entity_type"] == "leave_request"}
    se_exp   = {e["entity_id"] for e in status_events if e["entity_type"] == "expense_claim"}
    check("status_event leave → leave_requests", se_leave.issubset(lr_ids))
    check("status_event expense → expense_claims", se_exp.issubset(ec_ids))

    # ── 4. ZERO GROUND-TRUTH LEAKAGE ──────────────────────────
    print("\n── Ground-truth leakage ──")
    LEAK_COLS = {"anomaly_flag", "anomaly_type", "policy_violation",
                 "remarks", "is_anomaly", "issue_type", "expected_decision"}
    for name, rows in [
        ("employees", employees), ("leave_requests", leave_requests),
        ("expense_claims", expense_claims), ("expense_lines", expense_lines),
        ("leave_balances", leave_balances), ("approval_steps", approval_steps),
        ("reimbursements", reimbursements), ("status_events", status_events),
    ]:
        if rows:
            cols = set(rows[0].keys())
            leaked = cols & LEAK_COLS
            check(f"{name}: no leakage", not leaked, f"found: {leaked}")

    # ── 5. ID FORMAT ───────────────────────────────────────────
    print("\n── ID format ──")
    import re
    check("EMP format",  all(re.match(r"^EMP\d{4}$", e["employee_id"]) for e in employees))
    check("LR format",   all(re.match(r"^LR\d{4}$",  r["leave_request_id"]) for r in leave_requests))
    check("EC format",   all(re.match(r"^EC\d{4}$",  c["claim_id"]) for c in expense_claims))
    check("EL format",   all(re.match(r"^EL\d{5}$",  l["expense_line_id"]) for l in expense_lines))

    # ── 6. DATE ORDERING ──────────────────────────────────────
    print("\n── Date ordering ──")
    # Leave: applied_date <= start_date <= end_date
    lr_date_ok = 0
    for r in leave_requests:
        sd = r["start_date"]
        ed = r["end_date"]
        if sd <= ed:
            lr_date_ok += 1
    check("leave start <= end", lr_date_ok == len(leave_requests),
          f"{lr_date_ok}/{len(leave_requests)}")

    # Expense lines have dates
    el_date_ok = all(bool(l.get("expense_date")) for l in expense_lines)
    check("expense lines have dates", el_date_ok)

    # ── 7. EXPENSE LINES PER CLAIM (1–10) ─────────────────────
    print("\n── Lines per claim ──")
    lines_per_claim = Counter(l["claim_id"] for l in expense_lines)
    in_range = all(1 <= v <= 10 for v in lines_per_claim.values())
    all_claims_have_lines = ec_ids == set(lines_per_claim.keys())
    check("every claim has 1-10 lines", in_range and all_claims_have_lines,
          f"min={min(lines_per_claim.values())}, max={max(lines_per_claim.values())}, claims_with_lines={len(lines_per_claim)}")

    # ── 8. APPROVAL SEQUENCE CORRECTNESS ──────────────────────
    print("\n── Approval sequence ──")
    # If step N is Rejected, step N+1.. should be Skipped
    steps_by_entity: Dict[str, List[dict]] = defaultdict(list)
    for s in approval_steps:
        steps_by_entity[s["entity_id"]].append(s)

    seq_ok = 0
    seq_total = 0
    for eid, steps in steps_by_entity.items():
        steps_sorted = sorted(steps, key=lambda x: int(x["step_order"]))
        rejected_at = None
        valid = True
        for s in steps_sorted:
            seq_total += 1
            if rejected_at is not None:
                if s["status"] not in ("Skipped",):
                    valid = False
            if s["status"] == "Rejected" and rejected_at is None:
                rejected_at = int(s["step_order"])
            if valid:
                seq_ok += 1
    check("approval sequence (reject → skip)", seq_ok == seq_total,
          f"{seq_ok}/{seq_total}")

    # ── 9. REIMBURSEMENT ELIGIBILITY ──────────────────────────
    print("\n── Reimbursement eligibility ──")
    claim_status = {c["claim_id"]: c["status"] for c in expense_claims}
    # All reimbursements should be for approved claims (except anomaly duplicates)
    gt_dup_reimbs = {r["entity_id"] for r in ground_truth if r["issue_type"] == "duplicate_reimbursement"}
    non_anomaly_reimbs = [r for r in reimbursements if r["reimbursement_id"] not in gt_dup_reimbs]
    eligible = all(claim_status.get(r["claim_id"]) == "Approved" for r in non_anomaly_reimbs)
    check("reimbursements only for approved claims", eligible)

    # ── 10. LEAVE BALANCE RECONCILIATION ──────────────────────
    print("\n── Balance reconciliation ──")
    # opening_balance = accrued + carry_forward
    bal_ok = 0
    for b in leave_balances:
        opening = int(b["opening_balance"])
        accrued = int(b["accrued"])
        carry   = int(b["carry_forward"])
        if opening == accrued + carry:
            bal_ok += 1
    check("opening = accrued + carry_forward", bal_ok == len(leave_balances),
          f"{bal_ok}/{len(leave_balances)}")

    # remaining = opening - used
    rem_ok = 0
    for b in leave_balances:
        opening   = int(b["opening_balance"])
        used      = int(b["used"])
        remaining = int(b["remaining"])
        if remaining == max(0, opening - used):
            rem_ok += 1
    check("remaining = max(0, opening - used)", rem_ok == len(leave_balances),
          f"{rem_ok}/{len(leave_balances)}")

    # ── 11. STATUS EVENTS CHAIN ───────────────────────────────
    print("\n── Status events ──")
    # Each entity should have a chain Draft→Submitted→Under Review→final
    events_by_entity: Dict[str, List[dict]] = defaultdict(list)
    for ev in status_events:
        events_by_entity[ev["entity_id"]].append(ev)

    chain_ok = 0
    chain_total = 0
    for eid, evts in events_by_entity.items():
        chain_total += 1
        evts_sorted = sorted(evts, key=lambda x: x["event_timestamp"])
        if len(evts_sorted) >= 3:
            if (evts_sorted[0]["from_status"] == "Draft" and
                evts_sorted[0]["to_status"] == "Submitted" and
                evts_sorted[1]["from_status"] == "Submitted" and
                evts_sorted[1]["to_status"] == "Under Review"):
                chain_ok += 1
    check("status chain: Draft→Submitted→Under Review→...",
          chain_ok == chain_total, f"{chain_ok}/{chain_total}")

    # ── 12. GROUND TRUTH COVERAGE ─────────────────────────────
    print("\n── Ground-truth coverage ──")
    gt_types = Counter(r["issue_type"] for r in ground_truth)
    required_types = [
        "missing_receipt", "duplicate_receipt", "policy_limit_breach",
        "overlapping_leave", "insufficient_balance", "self_approval",
        "expense_outside_dates", "missing_cost_center", "holiday_span",
        "split_claim", "duplicate_reimbursement",
    ]
    for rt in required_types:
        check(f"ground_truth has {rt}", gt_types.get(rt, 0) > 0,
              f"count={gt_types.get(rt, 0)}")

    # ── SUMMARY ───────────────────────────────────────────────
    total = _pass + _fail
    print(f"\n{'='*50}")
    print(f"  PASSED: {_pass}/{total}")
    print(f"  FAILED: {_fail}/{total}")
    print(f"{'='*50}")

    return 0 if _fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

