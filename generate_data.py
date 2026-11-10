#!/usr/bin/env python3
"""
generate_data.py – Deterministic synthetic-data generator for a Leave &
Expense Management system.

Design principles
-----------------
1. **Single RNG**:  A numpy ``Generator`` seeded with ``config.SEED`` is the
   only source of randomness.  Every helper that needs randomness receives
   this generator as an argument — nothing creates its own.
2. **Sorted intermediates**:  Wherever we iterate over sets or dicts whose
   order might vary between runs, we explicitly sort first.
3. **Anomaly injection in-place**:  Anomalies are injected by *mutating*
   existing rows (or reserving slots up front), never by appending extra
   rows.  Final volumes are therefore exactly 800 leave requests and
   1 000 expense claims.
4. **Zero ground-truth leakage**:  Main CSV tables contain only operational
   columns.  All anomaly metadata lives exclusively in ``ground_truth.csv``.
5. **Rule-driven decisions**:  ``engine.py`` evaluates every leave request
   and expense claim against deterministic business rules.
"""

from __future__ import annotations

import csv
import hashlib
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

import config as cfg
import engine

# ────────────────────────────────────────────────────────────────────
# Globals
# ────────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).resolve().parent / "data"
RNG: np.random.Generator = np.random.default_rng(cfg.SEED)

FISCAL_START = date.fromisoformat(cfg.FISCAL_YEAR_START)
FISCAL_END   = date.fromisoformat(cfg.FISCAL_YEAR_END)
HIRE_LO      = date.fromisoformat(cfg.HIRE_DATE_RANGE[0])
HIRE_HI      = date.fromisoformat(cfg.HIRE_DATE_RANGE[1])

# ────────────────────────────────────────────────────────────────────
# Deterministic helpers
# ────────────────────────────────────────────────────────────────────

def _rand_date(lo: date, hi: date) -> date:
    """Return a random date in [lo, hi] using the global RNG."""
    span = (hi - lo).days
    if span <= 0:
        return lo
    return lo + timedelta(days=int(RNG.integers(0, span + 1)))


def _rand_date_range(lo: date, hi: date, min_days: int, max_days: int) -> Tuple[date, date]:
    start = _rand_date(lo, hi - timedelta(days=min_days))
    duration = int(RNG.integers(min_days, max_days + 1))
    end = start + timedelta(days=duration - 1)
    if end > hi:
        end = hi
    return start, end


def _receipt_hash(claim_id: str, line_idx: int, amount: float) -> str:
    raw = f"{claim_id}-{line_idx}-{amount:.2f}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _rand_choice(options: list) -> Any:
    """Deterministic choice from a list."""
    idx = int(RNG.integers(0, len(options)))
    return options[idx]


def _rand_subset(options: list, n: int) -> list:
    """Deterministic sample without replacement."""
    indices = RNG.choice(len(options), size=min(n, len(options)), replace=False)
    indices = sorted(indices)  # deterministic order
    return [options[i] for i in indices]


def _timestamp_from_date(d: date, base_hour: int = 9) -> str:
    """Create a deterministic timestamp from a date."""
    hour = base_hour + int(RNG.integers(0, 8))
    minute = int(RNG.integers(0, 60))
    second = int(RNG.integers(0, 60))
    return f"{d.isoformat()}T{hour:02d}:{minute:02d}:{second:02d}"


# ────────────────────────────────────────────────────────────────────
# 1. Employees
# ────────────────────────────────────────────────────────────────────

def generate_employees() -> List[dict]:
    """Generate exactly NUM_EMPLOYEES employees with a manager hierarchy."""
    employees: List[dict] = []
    first_names = [
        "Aarav","Aditi","Aditya","Akash","Amara","Amit","Ananya","Anil","Anjali","Arjun",
        "Bhavya","Chandra","Deepa","Deepak","Divya","Esha","Gaurav","Geeta","Hari","Isha",
        "Jaya","Karan","Kavita","Krishna","Lakshmi","Manish","Meera","Mohan","Nandini","Naveen",
        "Neha","Nikhil","Pallavi","Pooja","Pradeep","Priya","Rahul","Rajesh","Ravi","Rekha",
        "Rohan","Sachin","Sandeep","Sanjay","Sapna","Seema","Shiva","Shreya","Sneha","Sunil",
        "Suresh","Tanvi","Uma","Varun","Vijay","Vinay","Vishal","Vivek","Yash","Zara",
    ]
    last_names = [
        "Agarwal","Bhat","Chopra","Das","Desai","Dutta","Gandhi","Gupta","Iyer","Jain",
        "Joshi","Kapoor","Khan","Kumar","Malhotra","Mehta","Mishra","Nair","Pandey","Patel",
        "Rao","Reddy","Saxena","Shah","Sharma","Singh","Srivastava","Thakur","Verma","Yadav",
    ]

    for i in range(cfg.NUM_EMPLOYEES):
        emp_id = f"EMP{str(i + 1).zfill(4)}"
        fname = _rand_choice(first_names)
        lname = _rand_choice(last_names)
        dept = _rand_choice(cfg.DEPARTMENTS)
        hire_date = _rand_date(HIRE_LO, HIRE_HI)

        # ~5% have a termination date
        if RNG.random() < 0.05:
            term_date = _rand_date(hire_date + timedelta(days=90), FISCAL_END)
        else:
            term_date = None

        # Designation – weighted toward junior roles
        weights = np.array([30, 25, 15, 12, 8, 6, 4], dtype=float)
        weights /= weights.sum()
        des_idx = int(RNG.choice(len(cfg.DESIGNATIONS), p=weights))
        designation = cfg.DESIGNATIONS[des_idx]

        # Cost center from department
        cc = next(c for c in cfg.COST_CENTERS if c["name"] == dept)

        employees.append({
            "employee_id": emp_id,
            "first_name": fname,
            "last_name": lname,
            "email": f"{fname.lower()}.{lname.lower()}.{i+1}@company.com",
            "department": dept,
            "designation": designation,
            "cost_center_id": cc["cost_center_id"],
            "hire_date": hire_date,
            "termination_date": term_date,
        })

    # Assign managers (deterministic)
    _assign_managers(employees)
    return employees


def _assign_managers(employees: List[dict]) -> None:
    """
    Assign each employee a manager from the same department with a
    higher designation level.  Top-level people manage themselves
    (manager_id = own id).
    """
    by_dept: Dict[str, List[dict]] = {}
    for e in employees:
        by_dept.setdefault(e["department"], []).append(e)

    for dept in sorted(by_dept.keys()):
        dept_emps = by_dept[dept]
        # Sort by designation level descending, then emp_id for determinism
        dept_emps.sort(
            key=lambda x: (-cfg.DESIGNATION_LEVEL[x["designation"]], x["employee_id"])
        )
        top = dept_emps[0]
        top["manager_id"] = top["employee_id"]  # self-manages
        for e in dept_emps[1:]:
            # find the nearest senior
            my_level = cfg.DESIGNATION_LEVEL[e["designation"]]
            candidates = [
                c for c in dept_emps
                if cfg.DESIGNATION_LEVEL[c["designation"]] > my_level
            ]
            if candidates:
                e["manager_id"] = _rand_choice(candidates)["employee_id"]
            else:
                e["manager_id"] = top["employee_id"]


# ────────────────────────────────────────────────────────────────────
# 2. Cost Centres  (static from config)
# ────────────────────────────────────────────────────────────────────

def generate_cost_centers() -> List[dict]:
    return list(cfg.COST_CENTERS)


# ────────────────────────────────────────────────────────────────────
# 3. Leave Policies  (static from config)
# ────────────────────────────────────────────────────────────────────

def generate_leave_policies() -> List[dict]:
    return list(cfg.LEAVE_TYPES)


# ────────────────────────────────────────────────────────────────────
# 4. Expense Policies (static from config)
# ────────────────────────────────────────────────────────────────────

def generate_expense_policies() -> List[dict]:
    return list(cfg.EXPENSE_POLICIES)


# ────────────────────────────────────────────────────────────────────
# 5. Approval Rules (static from config)
# ────────────────────────────────────────────────────────────────────

def generate_approval_rules() -> List[dict]:
    return list(cfg.APPROVAL_RULES)


# ────────────────────────────────────────────────────────────────────
# 6. Leave Balances
# ────────────────────────────────────────────────────────────────────

def generate_leave_balances(employees: List[dict]) -> Dict[str, Dict[str, dict]]:
    """
    For every (employee, leave_type) pair, create an initial balance row.
    Returns a nested dict:  balances[emp_id][leave_type] = balance_row
    Also returns a flat list for CSV output.
    """
    balances: Dict[str, Dict[str, dict]] = {}
    flat: List[dict] = []
    bal_id = 0

    for emp in employees:
        balances[emp["employee_id"]] = {}
        for pol in cfg.LEAVE_TYPES:
            bal_id += 1
            annual = pol["annual_quota"]
            # Small carry-forward for eligible types
            carry = 0
            if pol["carry_forward"]:
                carry = int(RNG.integers(0, min(6, annual) + 1))
            # Random used days 0..annual//2 for realism
            used = int(RNG.integers(0, annual // 2 + 1))
            opening = annual + carry
            remaining = max(0, opening - used)
            row = {
                "balance_id": f"LB{str(bal_id).zfill(5)}",
                "employee_id": emp["employee_id"],
                "leave_type": pol["leave_type"],
                "year": 2025,
                "opening_balance": opening,
                "used": used,
                "accrued": annual,
                "carry_forward": carry,
                "remaining": remaining,
            }
            balances[emp["employee_id"]][pol["leave_type"]] = row
            flat.append(row)

    return balances, flat


# ────────────────────────────────────────────────────────────────────
# 7. Leave Requests  (with anomaly injection)
# ────────────────────────────────────────────────────────────────────

def generate_leave_requests(
    employees: List[dict],
    balances: Dict[str, Dict[str, dict]],
    ground_truth: List[dict],
    status_events: List[dict],
) -> List[dict]:
    """
    Generate exactly NUM_LEAVE_REQUESTS leave requests.

    Anomalies are injected by reserving specific indices up-front and
    mutating those rows after initial generation.
    """
    n = cfg.NUM_LEAVE_REQUESTS

    # Decide which indices get which anomaly
    anomaly_map = _plan_leave_anomalies(n)

    # We track approved leaves per employee to detect overlaps
    approved_leaves_by_emp: Dict[str, List[dict]] = {}

    requests: List[dict] = []

    # Pre-compute a sorted employee list for deterministic cycling
    emp_ids = [e["employee_id"] for e in employees]
    emp_lookup = {e["employee_id"]: e for e in employees}
    policy_lookup = {p["leave_type"]: p for p in cfg.LEAVE_TYPES}
    active_emp_ids = [e["employee_id"] for e in employees if e["termination_date"] is None]

    for i in range(n):
        lr_id = f"LR{str(i + 1).zfill(4)}"
        anomaly = anomaly_map.get(i)

        # Pick employee – cycle through for coverage
        if anomaly == "overlapping_leave":
            # pick an employee that already has an approved leave
            candidates = sorted(approved_leaves_by_emp.keys())
            if candidates:
                emp_id = _rand_choice(candidates)
            else:
                emp_id = _rand_choice(active_emp_ids)
        else:
            emp_id = emp_ids[i % len(emp_ids)]
        emp = emp_lookup[emp_id]

        # Pick leave type
        common_types = ["Earned Leave", "Sick Leave", "Casual Leave", "Compensatory Off"]
        leave_type = _rand_choice(common_types)
        policy = policy_lookup[leave_type]

        # Generate dates
        start, end = _rand_date_range(FISCAL_START, FISCAL_END, 1, 5)
        days = (end - start).days + 1
        applied = start - timedelta(days=int(RNG.integers(1, 30)))
        if applied < FISCAL_START:
            applied = FISCAL_START

        # ── Apply anomaly mutations ─────────────────────────────
        if anomaly == "insufficient_balance":
            # Force days > remaining balance
            bal = balances[emp_id].get(leave_type)
            if bal and bal["remaining"] > 0:
                days = bal["remaining"] + int(RNG.integers(2, 8))
                end = start + timedelta(days=days - 1)
            else:
                days = policy["annual_quota"] + 5
                end = start + timedelta(days=days - 1)

        elif anomaly == "overlapping_leave":
            prev_list = approved_leaves_by_emp.get(emp_id, [])
            if prev_list:
                prev = prev_list[-1]
                # Overlap by starting 1 day before prev ends
                start = prev["end_date"] - timedelta(days=1)
                days = int(RNG.integers(2, 5))
                end = start + timedelta(days=days - 1)
                applied = start - timedelta(days=int(RNG.integers(1, 15)))
                if applied < FISCAL_START:
                    applied = FISCAL_START

        elif anomaly == "holiday_span":
            # Force the leave to span a holiday
            holiday_dates = sorted(engine._HOLIDAYS_SET)
            hol = _rand_choice(holiday_dates)
            start = hol - timedelta(days=int(RNG.integers(0, 3)))
            days = int(RNG.integers(3, 7))
            end = start + timedelta(days=days - 1)
            applied = start - timedelta(days=int(RNG.integers(1, 15)))
            if applied < FISCAL_START:
                applied = FISCAL_START

        elif anomaly == "self_approval":
            pass  # handled at approval step

        if end > FISCAL_END:
            end = FISCAL_END
            days = (end - start).days + 1

        req = {
            "leave_request_id": lr_id,
            "employee_id": emp_id,
            "leave_type": leave_type,
            "start_date": start,
            "end_date": end,
            "days_requested": days,
            "applied_date": applied,
        }

        # ── Decision engine ─────────────────────────────────────
        bal_row = balances[emp_id].get(leave_type)
        remaining = bal_row["remaining"] if bal_row else 0
        prev_approved = approved_leaves_by_emp.get(emp_id, [])

        status, reason_code, reason_text = engine.decide_leave(
            req, emp, remaining, prev_approved, policy,
        )

        req["status"] = status
        req["reason_code"] = reason_code

        # Track approved leaves
        if status == "Approved":
            approved_leaves_by_emp.setdefault(emp_id, []).append(req)
            # Deduct balance
            if bal_row:
                bal_row["remaining"] = max(0, bal_row["remaining"] - days)
                bal_row["used"] += days

        # ── Status events ───────────────────────────────────────
        _emit_leave_status_events(req, emp, status, reason_code, applied, status_events)

        # ── Ground truth for anomalies ──────────────────────────
        if anomaly:
            gt_reason = reason_text
            if anomaly == "self_approval":
                gt_reason = "Employee is the approver (self-approval)"
            elif anomaly == "holiday_span":
                gt_reason = f"Leave spans public holiday(s)"

            ground_truth.append({
                "entity_type": "leave_request",
                "entity_id": lr_id,
                "issue_type": anomaly,
                "description": gt_reason,
                "expected_decision": status,
                "expected_reason": reason_code,
            })

        requests.append(req)

    return requests


def _plan_leave_anomalies(n: int) -> Dict[int, str]:
    """
    Pre-allocate anomaly types to specific row indices.
    This ensures we don't exceed volumes and injection is deterministic.
    """
    anomaly_types = [
        ("overlapping_leave",      int(n * cfg.ANOMALY_RATES["overlapping_leave"])),
        ("insufficient_balance",   int(n * cfg.ANOMALY_RATES["insufficient_balance"])),
        ("self_approval",          int(n * cfg.ANOMALY_RATES["self_approval"])),
        ("holiday_span",           int(n * cfg.ANOMALY_RATES["holiday_span"])),
    ]
    mapping: Dict[int, str] = {}
    used_indices: set = set()

    for atype, count in anomaly_types:
        # Distribute across the index range (skip first 10% for clean baseline)
        start_idx = n // 10
        available = [i for i in range(start_idx, n) if i not in used_indices]
        step = max(1, len(available) // (count + 1))
        chosen = available[step::step][:count]
        for idx in chosen:
            mapping[idx] = atype
            used_indices.add(idx)

    return mapping


def _emit_leave_status_events(
    req: dict, emp: dict, final_status: str,
    reason_code: str, applied_date: date,
    events: List[dict],
) -> None:
    """Append status-history events for a leave request."""
    eid_counter = len(events)
    entity_id = req["leave_request_id"]

    ts_base = applied_date
    # Draft → Submitted
    eid_counter += 1
    events.append({
        "event_id": f"SE{str(eid_counter).zfill(6)}",
        "entity_type": "leave_request",
        "entity_id": entity_id,
        "from_status": "Draft",
        "to_status": "Submitted",
        "event_timestamp": _timestamp_from_date(ts_base, 9),
        "actor_id": emp["employee_id"],
        "reason_code": "",
    })
    # Submitted → Under Review
    ts_review = ts_base + timedelta(days=1)
    eid_counter += 1
    events.append({
        "event_id": f"SE{str(eid_counter).zfill(6)}",
        "entity_type": "leave_request",
        "entity_id": entity_id,
        "from_status": "Submitted",
        "to_status": "Under Review",
        "event_timestamp": _timestamp_from_date(ts_review, 10),
        "actor_id": emp.get("manager_id", emp["employee_id"]),
        "reason_code": "",
    })
    # Under Review → Approved/Rejected
    ts_decision = ts_review + timedelta(days=int(RNG.integers(1, 4)))
    eid_counter += 1
    events.append({
        "event_id": f"SE{str(eid_counter).zfill(6)}",
        "entity_type": "leave_request",
        "entity_id": entity_id,
        "from_status": "Under Review",
        "to_status": final_status,
        "event_timestamp": _timestamp_from_date(ts_decision, 11),
        "actor_id": emp.get("manager_id", emp["employee_id"]),
        "reason_code": reason_code,
    })


# ────────────────────────────────────────────────────────────────────
# 8. Expense Claims, Lines, Approval Steps
# ────────────────────────────────────────────────────────────────────

def generate_expense_claims(
    employees: List[dict],
    ground_truth: List[dict],
    status_events: List[dict],
) -> Tuple[List[dict], List[dict], List[dict], List[dict]]:
    """
    Generate exactly NUM_EXPENSE_CLAIMS claims with 1-10 lines each.

    Returns (claims, lines, approval_steps, reimbursements).
    """
    n = cfg.NUM_EXPENSE_CLAIMS
    anomaly_map = _plan_expense_anomalies(n)

    emp_lookup = {e["employee_id"]: e for e in employees}
    emp_ids = [e["employee_id"] for e in employees]
    active_emp_ids = [e["employee_id"] for e in employees if e["termination_date"] is None]

    claims: List[dict] = []
    all_lines: List[dict] = []
    all_steps: List[dict] = []
    reimbursements: List[dict] = []

    # For duplicate receipt tracking
    receipt_pool: List[str] = []
    # For duplicate reimbursement tracking
    reimbursed_claims: List[str] = []
    # For split-claim tracking
    split_source_map: Dict[int, int] = {}  # target_idx → source_idx

    # Pre-compute split claim pairs
    split_indices = sorted([i for i, a in anomaly_map.items() if a == "split_claim"])
    source_indices = []
    for si in split_indices:
        # source is the previous non-anomaly claim
        src = si - 1
        while src in anomaly_map and src > 0:
            src -= 1
        split_source_map[si] = src
        source_indices.append(src)

    line_counter = 0
    step_counter = 0
    reimb_counter = 0

    for i in range(n):
        ec_id = f"EC{str(i + 1).zfill(4)}"
        anomaly = anomaly_map.get(i)

        # Pick employee
        if anomaly == "expense_outside_dates":
            # pick an employee who has a termination date
            termed = [e for e in employees if e["termination_date"] is not None]
            if termed:
                emp = _rand_choice(termed)
            else:
                emp = emp_lookup[_rand_choice(active_emp_ids)]
        else:
            emp_id = emp_ids[i % len(emp_ids)]
            emp = emp_lookup[emp_id]

        # Claim date
        claim_date = _rand_date(FISCAL_START, FISCAL_END)
        if anomaly == "expense_outside_dates" and emp.get("termination_date"):
            # force claim after termination
            claim_date = emp["termination_date"] + timedelta(days=int(RNG.integers(5, 60)))

        # Cost center
        cc_id = emp["cost_center_id"]
        if anomaly == "missing_cost_center":
            cc_id = ""

        # Number of lines
        num_lines = int(RNG.integers(cfg.EXPENSE_LINES_MIN, cfg.EXPENSE_LINES_MAX + 1))

        # Handle split claims — copy lines from source claim
        if anomaly == "split_claim" and split_source_map.get(i) is not None:
            src_idx = split_source_map[i]
            if src_idx < len(claims):
                src_claim = claims[src_idx]
                # Get a subset of lines from source to duplicate
                src_lines = [l for l in all_lines if l["claim_id"] == src_claim["claim_id"]]
                num_lines = max(1, len(src_lines) // 2)

        # Generate lines
        claim_lines: List[dict] = []
        total_amount = 0.0
        for j in range(num_lines):
            line_counter += 1
            el_id = f"EL{str(line_counter).zfill(5)}"
            category = _rand_choice(cfg.EXPENSE_CATEGORIES)
            amount = round(float(RNG.uniform(50, 5000)), 2)

            # Policy-limit breach injection
            if anomaly == "policy_limit_breach" and j == 0:
                pol = cfg.EXPENSE_POLICY_MAP.get(category)
                if pol:
                    amount = round(pol["single_receipt_limit"] + float(RNG.uniform(500, 3000)), 2)

            has_receipt = True
            receipt_hash = _receipt_hash(ec_id, j, amount)

            # Missing receipt injection
            if anomaly == "missing_receipt" and j == 0:
                pol = cfg.EXPENSE_POLICY_MAP.get(category)
                if pol and amount > pol["receipt_required_above"]:
                    has_receipt = False
                else:
                    # force amount above threshold
                    amount = round(pol["receipt_required_above"] + float(RNG.uniform(100, 1000)), 2) if pol else amount
                    has_receipt = False

            # Duplicate receipt injection
            if anomaly == "duplicate_receipt" and j == 0 and receipt_pool:
                receipt_hash = _rand_choice(receipt_pool)

            if has_receipt:
                receipt_pool.append(receipt_hash)

            expense_date = claim_date - timedelta(days=int(RNG.integers(0, 30)))

            line = {
                "expense_line_id": el_id,
                "claim_id": ec_id,
                "line_number": j + 1,
                "category": category,
                "description": f"{category} expense",
                "amount": amount,
                "currency": "INR",
                "expense_date": expense_date,
                "has_receipt": has_receipt,
                "receipt_hash": receipt_hash if has_receipt else "",
            }
            claim_lines.append(line)
            total_amount += amount

        all_lines.extend(claim_lines)

        claim = {
            "claim_id": ec_id,
            "employee_id": emp["employee_id"],
            "claim_date": claim_date,
            "total_amount": round(total_amount, 2),
            "currency": "INR",
            "cost_center_id": cc_id,
            "department": emp["department"],
        }

        # ── Decision engine ─────────────────────────────────────
        status, reason_code, reason_text, line_issues = engine.decide_expense_claim(
            claim, claim_lines, emp, cfg.EXPENSE_POLICY_MAP,
        )

        # Self-approval: mark in ground truth but proceed with engine decision
        if anomaly == "self_approval":
            claim["approver_override"] = emp["employee_id"]

        claim["status"] = status
        claim["reason_code"] = reason_code

        # ── Approval steps ──────────────────────────────────────
        roles = engine.route_expense_approval(total_amount)
        for level, role in enumerate(roles, 1):
            step_counter += 1
            step_id = f"AS{str(step_counter).zfill(5)}"

            if anomaly == "self_approval" and level == 1:
                approver_id = emp["employee_id"]
            else:
                approver_id = emp.get("manager_id", emp["employee_id"])

            step_status = "Approved"
            step_reason = "RULES_PASSED"
            if status == "Rejected" and level == 1:
                step_status = "Rejected"
                step_reason = reason_code
            elif status == "Rejected" and level > 1:
                step_status = "Skipped"
                step_reason = "PRIOR_REJECTION"

            step_ts = claim_date + timedelta(days=level)

            all_steps.append({
                "approval_step_id": step_id,
                "entity_type": "expense_claim",
                "entity_id": ec_id,
                "step_order": level,
                "approver_id": approver_id,
                "approver_role": role,
                "status": step_status,
                "decision_date": step_ts,
                "reason_code": step_reason,
            })

        # ── Status events ───────────────────────────────────────
        _emit_expense_status_events(claim, emp, status, reason_code, claim_date, status_events)

        # ── Reimbursement ───────────────────────────────────────
        if engine.should_create_reimbursement(status):
            reimb_counter += 1
            reimb_id = f"RB{str(reimb_counter).zfill(4)}"
            reimb = {
                "reimbursement_id": reimb_id,
                "claim_id": ec_id,
                "employee_id": emp["employee_id"],
                "amount": claim["total_amount"],
                "currency": "INR",
                "status": "Processed",
                "processed_date": claim_date + timedelta(days=int(RNG.integers(5, 15))),
                "payment_method": _rand_choice(["Bank Transfer", "Direct Deposit"]),
            }
            reimbursements.append(reimb)
            reimbursed_claims.append(ec_id)

            # Duplicate reimbursement injection
            if anomaly == "duplicate_reimbursement":
                reimb_counter += 1
                dup_reimb_id = f"RB{str(reimb_counter).zfill(4)}"
                dup_reimb = dict(reimb)
                dup_reimb["reimbursement_id"] = dup_reimb_id
                dup_reimb["processed_date"] = reimb["processed_date"] + timedelta(days=int(RNG.integers(1, 5)))
                reimbursements.append(dup_reimb)
                ground_truth.append({
                    "entity_type": "reimbursement",
                    "entity_id": dup_reimb_id,
                    "issue_type": "duplicate_reimbursement",
                    "description": f"Duplicate reimbursement of {reimb_id} for claim {ec_id}",
                    "expected_decision": "Flag",
                    "expected_reason": "DUPLICATE_REIMBURSEMENT",
                })

        # ── Ground truth for anomalies ──────────────────────────
        if anomaly and anomaly != "duplicate_reimbursement":
            desc = reason_text
            if anomaly == "self_approval":
                desc = f"Employee {emp['employee_id']} approved own claim"
            elif anomaly == "duplicate_receipt":
                desc = f"Line {claim_lines[0]['expense_line_id']} uses duplicated receipt hash"
            elif anomaly == "split_claim":
                src_idx = split_source_map.get(i)
                if src_idx is not None and src_idx < len(claims):
                    desc = f"Split from claim {claims[src_idx]['claim_id']}"
                else:
                    desc = "Split claim (standalone)"

            ground_truth.append({
                "entity_type": "expense_claim",
                "entity_id": ec_id,
                "issue_type": anomaly,
                "description": desc,
                "expected_decision": status,
                "expected_reason": reason_code,
            })

        claims.append(claim)

    return claims, all_lines, all_steps, reimbursements


def _plan_expense_anomalies(n: int) -> Dict[int, str]:
    """Pre-allocate anomaly types to expense claim indices."""
    anomaly_types = [
        ("missing_receipt",         int(n * cfg.ANOMALY_RATES["missing_receipt"])),
        ("duplicate_receipt",       int(n * cfg.ANOMALY_RATES["duplicate_receipt"])),
        ("policy_limit_breach",     int(n * cfg.ANOMALY_RATES["policy_limit_breach"])),
        ("self_approval",           int(n * cfg.ANOMALY_RATES["self_approval"])),
        ("expense_outside_dates",   int(n * cfg.ANOMALY_RATES["expense_outside_dates"])),
        ("missing_cost_center",     int(n * cfg.ANOMALY_RATES["missing_cost_center"])),
        ("split_claim",             int(n * cfg.ANOMALY_RATES["split_claim"])),
        ("duplicate_reimbursement", int(n * cfg.ANOMALY_RATES["duplicate_reimbursement"])),
    ]
    mapping: Dict[int, str] = {}
    used_indices: set = set()

    for atype, count in anomaly_types:
        start_idx = n // 10
        available = [i for i in range(start_idx, n) if i not in used_indices]
        step = max(1, len(available) // (count + 1))
        chosen = available[step::step][:count]
        for idx in chosen:
            mapping[idx] = atype
            used_indices.add(idx)

    return mapping


def _emit_expense_status_events(
    claim: dict, emp: dict, final_status: str,
    reason_code: str, claim_date: date,
    events: List[dict],
) -> None:
    eid_counter = len(events)
    entity_id = claim["claim_id"]

    eid_counter += 1
    events.append({
        "event_id": f"SE{str(eid_counter).zfill(6)}",
        "entity_type": "expense_claim",
        "entity_id": entity_id,
        "from_status": "Draft",
        "to_status": "Submitted",
        "event_timestamp": _timestamp_from_date(claim_date, 9),
        "actor_id": emp["employee_id"],
        "reason_code": "",
    })
    ts_review = claim_date + timedelta(days=1)
    eid_counter += 1
    events.append({
        "event_id": f"SE{str(eid_counter).zfill(6)}",
        "entity_type": "expense_claim",
        "entity_id": entity_id,
        "from_status": "Submitted",
        "to_status": "Under Review",
        "event_timestamp": _timestamp_from_date(ts_review, 10),
        "actor_id": emp.get("manager_id", emp["employee_id"]),
        "reason_code": "",
    })
    ts_decision = ts_review + timedelta(days=int(RNG.integers(1, 4)))
    eid_counter += 1
    events.append({
        "event_id": f"SE{str(eid_counter).zfill(6)}",
        "entity_type": "expense_claim",
        "entity_id": entity_id,
        "from_status": "Under Review",
        "to_status": final_status,
        "event_timestamp": _timestamp_from_date(ts_decision, 11),
        "actor_id": emp.get("manager_id", emp["employee_id"]),
        "reason_code": reason_code,
    })


# ────────────────────────────────────────────────────────────────────
# 9. Leave Approval Steps (generated alongside leave requests)
# ────────────────────────────────────────────────────────────────────

def generate_leave_approval_steps(
    requests: List[dict],
    employees: List[dict],
) -> List[dict]:
    """Create approval-step records for each leave request."""
    emp_lookup = {e["employee_id"]: e for e in employees}
    steps: List[dict] = []
    step_counter = 0

    for req in requests:
        emp = emp_lookup[req["employee_id"]]
        days = req["days_requested"]
        roles = engine.route_leave_approval(days)
        status = req["status"]
        reason = req["reason_code"]

        for level, role in enumerate(roles, 1):
            step_counter += 1
            step_id = f"AS{str(step_counter).zfill(5)}"

            approver_id = emp.get("manager_id", emp["employee_id"])

            step_status = "Approved"
            step_reason = "RULES_PASSED"
            if status == "Rejected" and level == 1:
                step_status = "Rejected"
                step_reason = reason
            elif status == "Rejected" and level > 1:
                step_status = "Skipped"
                step_reason = "PRIOR_REJECTION"

            step_date = req["applied_date"] + timedelta(days=level + 1)

            steps.append({
                "approval_step_id": step_id,
                "entity_type": "leave_request",
                "entity_id": req["leave_request_id"],
                "step_order": level,
                "approver_id": approver_id,
                "approver_role": role,
                "status": step_status,
                "decision_date": step_date,
                "reason_code": step_reason,
            })

    return steps


# ────────────────────────────────────────────────────────────────────
# CSV Writing
# ────────────────────────────────────────────────────────────────────

def _write_csv(filename: str, rows: List[dict], fieldnames: Optional[List[str]] = None) -> None:
    """Write rows to a CSV in the data directory. Dates → ISO strings."""
    if not rows:
        # Write empty file with headers
        path = DATA_DIR / filename
        with open(path, "w", newline="", encoding="utf-8") as f:
            pass
        return

    if fieldnames is None:
        fieldnames = list(rows[0].keys())

    path = DATA_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            out = {}
            for k in fieldnames:
                v = row.get(k, "")
                if isinstance(v, (date, datetime)):
                    v = v.isoformat()
                elif isinstance(v, bool):
                    v = str(v)
                elif v is None:
                    v = ""
                out[k] = v
            writer.writerow(out)


# ────────────────────────────────────────────────────────────────────
# Main pipeline
# ────────────────────────────────────────────────────────────────────

def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    ground_truth: List[dict] = []
    status_events: List[dict] = []

    print("Generating employees …")
    employees = generate_employees()

    print("Generating cost centres …")
    cost_centers = generate_cost_centers()

    print("Generating leave policies …")
    leave_policies = generate_leave_policies()

    print("Generating expense policies …")
    expense_policies = generate_expense_policies()

    print("Generating approval rules …")
    approval_rules = generate_approval_rules()

    print("Generating leave balances …")
    balances, balances_flat = generate_leave_balances(employees)

    print("Generating leave requests (with anomaly injection) …")
    leave_requests = generate_leave_requests(employees, balances, ground_truth, status_events)

    print("Generating leave approval steps …")
    leave_steps = generate_leave_approval_steps(leave_requests, employees)

    print("Generating expense claims (with anomaly injection) …")
    claims, expense_lines, expense_steps, reimbursements = generate_expense_claims(
        employees, ground_truth, status_events,
    )

    # Merge approval steps (leave + expense)
    all_approval_steps = leave_steps + expense_steps
    # Re-number step IDs deterministically
    for idx, step in enumerate(all_approval_steps):
        step["approval_step_id"] = f"AS{str(idx + 1).zfill(5)}"

    # Re-number status events
    for idx, ev in enumerate(status_events):
        ev["event_id"] = f"SE{str(idx + 1).zfill(6)}"

    # ── Write all CSVs ──────────────────────────────────────────
    print("Writing CSV files …")

    _write_csv("employees.csv", employees, [
        "employee_id", "first_name", "last_name", "email", "department",
        "designation", "cost_center_id", "hire_date", "termination_date",
        "manager_id",
    ])

    _write_csv("cost_centers.csv", cost_centers, [
        "cost_center_id", "name", "budget",
    ])

    _write_csv("leave_policies.csv", leave_policies, [
        "policy_id", "leave_type", "annual_quota", "max_consecutive_days",
        "min_notice_days", "carry_forward", "encashable",
    ])

    _write_csv("expense_policies.csv", expense_policies, [
        "policy_id", "category", "single_receipt_limit", "monthly_limit",
        "receipt_required_above", "requires_pre_approval_above",
    ])

    _write_csv("approval_rules.csv", approval_rules, [
        "rule_id", "entity_type", "condition", "levels", "approver_role",
    ])

    _write_csv("leave_balances.csv", balances_flat, [
        "balance_id", "employee_id", "leave_type", "year",
        "opening_balance", "used", "accrued", "carry_forward", "remaining",
    ])

    _write_csv("leave_requests.csv", leave_requests, [
        "leave_request_id", "employee_id", "leave_type",
        "start_date", "end_date", "days_requested", "applied_date", "status",
    ])

    _write_csv("expense_claims.csv", claims, [
        "claim_id", "employee_id", "claim_date", "total_amount",
        "currency", "cost_center_id", "department", "status",
    ])

    _write_csv("expense_lines.csv", expense_lines, [
        "expense_line_id", "claim_id", "line_number", "category",
        "description", "amount", "currency", "expense_date",
        "has_receipt", "receipt_hash",
    ])

    _write_csv("approval_steps.csv", all_approval_steps, [
        "approval_step_id", "entity_type", "entity_id", "step_order",
        "approver_id", "approver_role", "status", "decision_date", "reason_code",
    ])

    _write_csv("reimbursements.csv", reimbursements, [
        "reimbursement_id", "claim_id", "employee_id", "amount",
        "currency", "status", "processed_date", "payment_method",
    ])

    _write_csv("ground_truth.csv", ground_truth, [
        "entity_type", "entity_id", "issue_type", "description",
        "expected_decision", "expected_reason",
    ])

    _write_csv("status_events.csv", status_events, [
        "event_id", "entity_type", "entity_id", "from_status",
        "to_status", "event_timestamp", "actor_id", "reason_code",
    ])

    # ── Summary ─────────────────────────────────────────────────
    print("\n✅  Generation complete!")
    print(f"   Employees:       {len(employees)}")
    print(f"   Leave policies:  {len(leave_policies)}")
    print(f"   Leave requests:  {len(leave_requests)}")
    print(f"   Expense claims:  {len(claims)}")
    print(f"   Expense lines:   {len(expense_lines)}")
    print(f"   Approval steps:  {len(all_approval_steps)}")
    print(f"   Reimbursements:  {len(reimbursements)}")
    print(f"   Status events:   {len(status_events)}")
    print(f"   Ground truth:    {len(ground_truth)}")


if __name__ == "__main__":
    main()
