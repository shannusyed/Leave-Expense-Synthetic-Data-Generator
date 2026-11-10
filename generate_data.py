#!/usr/bin/env python3
"""
generate_data.py
----------------
Production-ready synthetic data generator for HR Leave & Expense workflows.

Usage
-----
    python generate_data.py --scale full  --seed 20261022
    python generate_data.py --scale small --seed 20261022

All output is written to ./data/  relative to this script.
"""

from __future__ import annotations

import argparse
import os
import sys
import logging
from pathlib import Path
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ── project config ────────────────────────────────────────────────────────────
import config as cfg

# ── logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# Utility helpers
# ═════════════════════════════════════════════════════════════════════════════

def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def _date_range_days(start: str, end: str) -> int:
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    return (e - s).days


def _rand_date(rng: np.random.Generator, start: str, end: str) -> date:
    n = _date_range_days(start, end)
    offset = int(rng.integers(0, n + 1))
    return date.fromisoformat(start) + timedelta(days=offset)


def _fmt_date(d) -> str:
    if isinstance(d, (date,)):
        return d.isoformat()
    return str(d)


def _business_days(start: date, end: date) -> int:
    """Count weekday-only days between start and end (inclusive)."""
    if end < start:
        return 0
    days = 0
    cur = start
    while cur <= end:
        if cur.weekday() < 5:
            days += 1
        cur += timedelta(days=1)
    return days


# ═════════════════════════════════════════════════════════════════════════════
# ID factories
# ═════════════════════════════════════════════════════════════════════════════

def emp_id(n: int) -> str:
    return f"EMP-{n:06d}"

def cc_id(n: int) -> str:
    return f"CC-{n:04d}"

def lve_id(n: int, year: int = cfg.REFERENCE_YEAR) -> str:
    return f"LVE-{year}-{n:06d}"

def exp_id(n: int, year: int = cfg.REFERENCE_YEAR) -> str:
    return f"EXP-{year}-{n:06d}"

def expl_id(claim_id: str, line_num: int) -> str:
    return f"EXPL-{claim_id}-{line_num:02d}"

def apr_id(request_id: str, step_num: int) -> str:
    return f"APR-{request_id}-{step_num:02d}"

def rmb_id(n: int, year: int = cfg.REFERENCE_YEAR) -> str:
    return f"RMB-{year}-{n:06d}"


# ═════════════════════════════════════════════════════════════════════════════
# 1. EMPLOYEES
# ═════════════════════════════════════════════════════════════════════════════

def generate_employees(rng: np.random.Generator, n: int) -> pd.DataFrame:
    log.info("Generating %d employees …", n)

    first_names = [
        "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael",
        "Linda", "William", "Barbara", "David", "Elizabeth", "Richard",
        "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen",
        "Emma", "Noah", "Olivia", "Liam", "Ava", "Lucas", "Sophia", "Mason",
        "Isabella", "Ethan", "Mia", "Aiden", "Harper", "Jackson", "Evelyn",
        "Sebastian", "Abigail", "Mateo", "Emily", "Jack", "Ella", "Owen",
        "Elizabeth", "Theodore", "Camila", "Amir", "Priya", "Chen", "Yuki",
        "Fatima", "Carlos", "Ana", "Mohamed", "Leila", "Ravi", "Mei",
    ]
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
        "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
        "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
        "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
        "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
        "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
        "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
        "Carter", "Patel", "Kumar", "Singh", "Sharma", "Gupta", "Tanaka",
    ]

    ids      = [emp_id(i + 1) for i in range(n)]
    f_names  = [first_names[int(rng.integers(0, len(first_names)))] for _ in range(n)]
    l_names  = [last_names[int(rng.integers(0, len(last_names)))]   for _ in range(n)]
    names    = [f"{f} {l}" for f, l in zip(f_names, l_names)]
    emails   = [f"{fn.lower()}.{ln.lower()}{i+1}@company.com"
                for i, (fn, ln) in enumerate(zip(f_names, l_names))]

    depts   = rng.choice(cfg.DEPARTMENTS, size=n)
    grades  = []
    for _ in range(n):
        # weighted toward lower grades
        g = rng.choice(cfg.JOB_GRADES, p=[0.25, 0.25, 0.20, 0.15, 0.10, 0.05])
        grades.append(g)

    salaries = []
    for g in grades:
        lo, hi = cfg.GRADE_SALARY_RANGE[g]
        salaries.append(round(float(rng.uniform(lo, hi)), 2))

    emp_types  = rng.choice(
        cfg.EMPLOYMENT_TYPES, size=n, p=cfg.EMPLOYMENT_TYPE_WEIGHTS
    )

    hire_start = date.fromisoformat(cfg.EMPLOYMENT_START_MIN)
    hire_end   = date.fromisoformat(cfg.EMPLOYMENT_START_MAX)
    hire_range = (hire_end - hire_start).days

    hire_dates = [
        hire_start + timedelta(days=int(rng.integers(0, hire_range + 1)))
        for _ in range(n)
    ]

    # ~15 % of employees have a termination date
    term_dates: List[Optional[str]] = []
    for hd in hire_dates:
        if rng.random() < 0.15:
            max_offset = (date.fromisoformat(cfg.REQUEST_WINDOW_END) - hd).days
            if max_offset > 90:
                offset = int(rng.integers(90, max_offset))
                term_dates.append((_fmt_date(hd + timedelta(days=offset))))
            else:
                term_dates.append(None)
        else:
            term_dates.append(None)

    locations = rng.choice(cfg.LOCATIONS, size=n)

    # ── Manager hierarchy ────────────────────────────────────────────────────
    # First 10 employees are "top-level" (no manager).
    # Everyone else gets a manager from a higher grade or same dept.
    managers: List[Optional[str]] = [None] * min(10, n)
    for i in range(min(10, n), n):
        # pick from first i employees (guarantees no cycles)
        mgr_pool = list(range(max(0, i - 50), i))
        mgr_idx  = int(rng.choice(mgr_pool))
        managers.append(ids[mgr_idx])

    df = pd.DataFrame({
        "employee_id":       ids,
        "full_name":         names,
        "email":             emails,
        "department":        depts,
        "job_grade":         grades,
        "annual_salary":     salaries,
        "employment_type":   emp_types,
        "hire_date":         [_fmt_date(d) for d in hire_dates],
        "termination_date":  term_dates,
        "manager_id":        managers,
        "location":          locations,
        "is_active":         [t is None for t in term_dates],
    })

    log.info("  ✓ Employees: %d rows", len(df))
    return df


# ═════════════════════════════════════════════════════════════════════════════
# 2a. LEAVE POLICIES
# ═════════════════════════════════════════════════════════════════════════════

def generate_leave_policies() -> pd.DataFrame:
    log.info("Generating leave policies …")
    rows = []
    for t in cfg.LEAVE_POLICY_TEMPLATES:
        rows.append({
            "policy_id":               t["policy_id"],
            "policy_name":             t["policy_name"],
            "leave_type":              t["leave_type"],
            "accrual_days_per_year":   t["accrual_days_per_year"],
            "max_carry_forward_days":  t["max_carry_forward"],
            "max_consecutive_days":    t["max_consecutive_days"],
            "notice_period_days":      t["notice_period_days"],
            "applicable_grades":       "|".join(t["applicable_grades"]),
            "requires_approval":       t["requires_approval"],
        })
    df = pd.DataFrame(rows)
    log.info("  ✓ Leave policies: %d rows", len(df))
    return df


# ═════════════════════════════════════════════════════════════════════════════
# 2b. EXPENSE POLICIES
# ═════════════════════════════════════════════════════════════════════════════

def generate_expense_policies() -> pd.DataFrame:
    log.info("Generating expense policies …")
    rows = []
    for t in cfg.EXPENSE_POLICY_TEMPLATES:
        rows.append({
            "policy_id":               t["policy_id"],
            "policy_name":             t["policy_name"],
            "expense_category":        t["category"],
            "per_diem_limit":          t["per_diem_limit"],
            "single_receipt_limit":    t["single_receipt_limit"],
            "monthly_claim_limit":     t["monthly_claim_limit"],
            "requires_receipt_above":  t["requires_receipt_above"],
            "approval_threshold_l1":   t["approval_threshold_l1"],
            "approval_threshold_l2":   t["approval_threshold_l2"],
            "approval_threshold_l3":   t["approval_threshold_l3"],
            "reimbursable":            t["reimbursable"],
        })
    df = pd.DataFrame(rows)
    log.info("  ✓ Expense policies: %d rows", len(df))
    return df


# ═════════════════════════════════════════════════════════════════════════════
# 2c. COST CENTERS
# ═════════════════════════════════════════════════════════════════════════════

def generate_cost_centers(rng: np.random.Generator, n: int) -> pd.DataFrame:
    log.info("Generating %d cost centers …", n)
    rows = []
    dept_cycle = [cfg.DEPARTMENTS[i % len(cfg.DEPARTMENTS)] for i in range(n)]
    for i in range(n):
        budget = round(float(rng.uniform(50_000, 500_000)), 2)
        spent  = round(float(rng.uniform(0, budget * 0.9)), 2)
        rows.append({
            "cost_center_id":   cc_id(i + 1),
            "cost_center_name": f"{dept_cycle[i]} – CC{i+1:04d}",
            "department":       dept_cycle[i],
            "annual_budget":    budget,
            "budget_spent":     spent,
            "budget_remaining": round(budget - spent, 2),
            "is_active":        True,
        })
    df = pd.DataFrame(rows)
    log.info("  ✓ Cost centers: %d rows", len(df))
    return df


# ═════════════════════════════════════════════════════════════════════════════
# 2d. APPROVAL RULES
# ═════════════════════════════════════════════════════════════════════════════

def generate_approval_rules() -> pd.DataFrame:
    log.info("Generating approval rules …")
    rows = []
    for t in cfg.APPROVAL_RULE_TEMPLATES:
        rows.append({
            "rule_id":        t["rule_id"],
            "rule_name":      t["rule_name"],
            "entity_type":    t["entity_type"],
            "condition":      t["condition"],
            "threshold":      t["threshold"],
            "approver_role":  t["approver_role"],
            "level":          t["level"],
            "sla_hours":      t["sla_hours"],
            "is_active":      True,
        })
    df = pd.DataFrame(rows)
    log.info("  ✓ Approval rules: %d rows", len(df))
    return df


# ═════════════════════════════════════════════════════════════════════════════
# 3. LEAVE BALANCES
# ═════════════════════════════════════════════════════════════════════════════

def generate_leave_balances(
    employees: pd.DataFrame,
    leave_policies: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    log.info("Computing leave balances …")
    rows = []
    ref_date = date(cfg.REFERENCE_YEAR, 10, 31)   # balance as-of date

    for _, emp in employees.iterrows():
        hire = date.fromisoformat(emp["hire_date"])
        # fraction of reference year completed by employee
        year_start = date(cfg.REFERENCE_YEAR, 1, 1)
        months_in_year = max(
            0,
            min(
                (ref_date - max(hire, year_start)).days / 30.44,
                12.0,
            ),
        )
        grade = emp["job_grade"]

        for _, pol in leave_policies.iterrows():
            applicable = pol["applicable_grades"].split("|")
            if grade not in applicable:
                continue
            accrual_per_year = pol["accrual_days_per_year"]
            # pro-rata accrual
            accrued = round(accrual_per_year * (months_in_year / 12.0), 2)

            # carry-forward (prior-year remnant, capped by policy)
            carry = round(
                float(rng.uniform(0, pol["max_carry_forward_days"] + 1)), 2
            ) if pol["max_carry_forward_days"] > 0 else 0.0

            total_available = accrued + carry

            # days taken so far (capped at total to avoid overdraft – anomalies injected later)
            taken = round(float(rng.uniform(0, total_available * 0.8)), 2)

            balance = round(total_available - taken, 2)

            rows.append({
                "employee_id":       emp["employee_id"],
                "policy_id":         pol["policy_id"],
                "leave_type":        pol["leave_type"],
                "accrued_days":      accrued,
                "carry_forward_days": carry,
                "total_available":   total_available,
                "days_taken":        taken,
                "balance_days":      balance,
                "as_of_date":        ref_date.isoformat(),
                "anomaly_flag":      False,
            })

    df = pd.DataFrame(rows)
    log.info("  ✓ Leave balances: %d rows", len(df))
    return df


# ═════════════════════════════════════════════════════════════════════════════
# 4. LEAVE REQUESTS
# ═════════════════════════════════════════════════════════════════════════════

def generate_leave_requests(
    employees: pd.DataFrame,
    leave_policies: pd.DataFrame,
    leave_balances: pd.DataFrame,
    rng: np.random.Generator,
    n: int,
) -> pd.DataFrame:
    log.info("Generating %d leave requests …", n)

    req_start = date.fromisoformat(cfg.REQUEST_WINDOW_START)
    req_end   = date.fromisoformat(cfg.REQUEST_WINDOW_END)
    span_days = (req_end - req_start).days

    # build balance lookup: (emp_id, policy_id) → balance_days
    bal_lookup = {
        (r["employee_id"], r["policy_id"]): r["balance_days"]
        for _, r in leave_balances.iterrows()
    }

    statuses = ["Approved", "Rejected", "Pending", "Cancelled"]
    status_w = [0.60, 0.15, 0.20, 0.05]

    rows  = []
    idx   = 1

    while idx <= n:
        emp = employees.sample(1, random_state=int(rng.integers(0, 2**31))).iloc[0]
        hire    = date.fromisoformat(emp["hire_date"])
        # pick a policy that is applicable to this employee's grade
        applicable_pols = leave_policies[
            leave_policies["applicable_grades"].str.contains(emp["job_grade"])
        ]
        if len(applicable_pols) == 0:
            continue
        pol = applicable_pols.sample(1, random_state=int(rng.integers(0, 2**31))).iloc[0]

        # start date: must be after hire and within window
        earliest = max(req_start, hire + timedelta(days=int(pol["notice_period_days"])))
        if earliest > req_end:
            continue
        offset  = int(rng.integers(0, (req_end - earliest).days + 1))
        lv_start = earliest + timedelta(days=offset)

        # duration: 1 … max_consecutive_days (business days)
        max_days = int(pol["max_consecutive_days"])
        dur_bd   = int(rng.integers(1, min(max_days, 15) + 1))
        lv_end   = lv_start + timedelta(days=dur_bd + int(dur_bd * 2 / 5))  # calendar days
        if lv_end > req_end:
            lv_end = req_end
        days_requested = max(1, _business_days(lv_start, lv_end))

        # submission must precede leave start by notice period
        earliest_submit = hire
        latest_submit   = lv_start - timedelta(days=int(pol["notice_period_days"]))
        if latest_submit < req_start:
            latest_submit = req_start
        if latest_submit < earliest_submit:
            continue
        sub_offset  = int(rng.integers(0, max(1, (latest_submit - req_start).days + 1)))
        sub_date    = req_start + timedelta(days=sub_offset)

        # balance check
        avail = bal_lookup.get((emp["employee_id"], pol["policy_id"]), 0.0)
        policy_violation = days_requested > avail

        status = str(rng.choice(statuses, p=status_w))
        if policy_violation and status == "Approved":
            status = "Rejected"   # enforce: can't approve if balance insufficient

        remarks = ""
        if policy_violation:
            remarks = "Insufficient balance"

        req_id = lve_id(idx)
        rows.append({
            "request_id":        req_id,
            "employee_id":       emp["employee_id"],
            "policy_id":         pol["policy_id"],
            "leave_type":        pol["leave_type"],
            "start_date":        lv_start.isoformat(),
            "end_date":          lv_end.isoformat(),
            "days_requested":    days_requested,
            "submission_date":   sub_date.isoformat(),
            "status":            status,
            "policy_violation":  policy_violation,
            "remarks":           remarks,
            "anomaly_flag":      False,
            "anomaly_type":      "",
        })
        idx += 1

    df = pd.DataFrame(rows)
    log.info("  ✓ Leave requests: %d rows", len(df))
    return df


# ═════════════════════════════════════════════════════════════════════════════
# 5. EXPENSE CLAIMS + LINES
# ═════════════════════════════════════════════════════════════════════════════

EXPENSE_CATEGORIES = ["Travel", "Meals", "Office", "Training", "Accommodation", "Communication"]
EXPENSE_DESCS = {
    "Travel":        ["Flight – {dest}", "Train ticket", "Taxi/Uber", "Fuel reimbursement", "Parking fees"],
    "Meals":         ["Team lunch", "Client dinner", "Coffee meeting", "Working lunch", "Dinner – {dest}"],
    "Office":        ["Printer cartridges", "Stationery", "Mouse & keyboard", "Monitor stand", "Desk organizer"],
    "Training":      ["Online course subscription", "Conference registration", "Workshop fee", "Book / materials"],
    "Accommodation": ["Hotel – {dest}", "Serviced apartment", "Airbnb – {dest}", "Corporate housing"],
    "Communication": ["Mobile data plan", "International SIM", "Video-call subscription", "Hotspot device"],
}
CITIES = ["New York", "London", "Singapore", "Paris", "Tokyo", "Berlin", "Dubai", "Sydney"]

CATEGORY_TO_POLICY = {
    "Travel":        "EP-001",
    "Accommodation": "EP-001",
    "Meals":         "EP-002",
    "Office":        "EP-003",
    "Training":      "EP-004",
    "Communication": "EP-003",
}


def _pick_desc(rng: np.random.Generator, cat: str) -> str:
    desc = str(rng.choice(EXPENSE_DESCS[cat]))
    city = str(rng.choice(CITIES))
    return desc.replace("{dest}", city)


def generate_expense_claims_and_lines(
    employees:        pd.DataFrame,
    expense_policies: pd.DataFrame,
    cost_centers:     pd.DataFrame,
    rng:              np.random.Generator,
    n_claims:         int,
    lines_range:      Tuple[int, int],
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    log.info("Generating %d expense claims + lines …", n_claims)

    req_start = date.fromisoformat(cfg.REQUEST_WINDOW_START)
    req_end   = date.fromisoformat(cfg.REQUEST_WINDOW_END)
    span_days = (req_end - req_start).days

    pol_lookup = {r["policy_id"]: r for _, r in expense_policies.iterrows()}
    cc_ids     = cost_centers["cost_center_id"].tolist()

    claim_rows = []
    line_rows  = []
    claim_idx  = 1

    while claim_idx <= n_claims:
        emp = employees.sample(1, random_state=int(rng.integers(0, 2**31))).iloc[0]
        hire     = date.fromisoformat(emp["hire_date"])
        term_raw = emp["termination_date"]
        term_dt  = date.fromisoformat(term_raw) if pd.notna(term_raw) and term_raw else None

        # claim submission date
        earliest = max(req_start, hire)
        latest   = min(req_end, term_dt) if term_dt else req_end
        if latest <= earliest:
            continue
        offset      = int(rng.integers(0, (latest - earliest).days + 1))
        submit_date = earliest + timedelta(days=offset)

        # cost center
        cc = str(rng.choice(cc_ids))

        claim_id = exp_id(claim_idx)
        n_lines  = int(rng.integers(lines_range[0], lines_range[1] + 1))

        lines_total = 0.0
        claim_lines = []
        for ln in range(1, n_lines + 1):
            cat   = str(rng.choice(EXPENSE_CATEGORIES))
            pol_id = CATEGORY_TO_POLICY.get(cat, "EP-001")
            pol    = pol_lookup[pol_id]

            # expense date must be within employment window and before submission
            exp_earliest = max(req_start, hire)
            exp_latest   = min(submit_date, term_dt) if term_dt else submit_date
            if exp_latest <= exp_earliest:
                exp_date = submit_date
            else:
                ed_offset = int(rng.integers(0, (exp_latest - exp_earliest).days + 1))
                exp_date  = exp_earliest + timedelta(days=ed_offset)

            amount = round(float(rng.uniform(10.0, min(pol["single_receipt_limit"], 800.0))), 2)
            has_receipt = amount >= pol["requires_receipt_above"]

            claim_lines.append({
                "line_id":          expl_id(claim_id, ln),
                "claim_id":         claim_id,
                "expense_date":     exp_date.isoformat(),
                "expense_category": cat,
                "policy_id":        pol_id,
                "description":      _pick_desc(rng, cat),
                "amount":           amount,
                "currency":         "USD",
                "has_receipt":      has_receipt,
                "is_billable":      bool(rng.random() < 0.3),
                "anomaly_flag":     False,
                "anomaly_type":     "",
            })
            lines_total += amount

        total = round(lines_total, 2)
        # determine dominant category
        cats_in_claim = [cl["expense_category"] for cl in claim_lines]
        dominant_cat  = max(set(cats_in_claim), key=cats_in_claim.count)
        primary_pol   = CATEGORY_TO_POLICY.get(dominant_cat, "EP-001")

        claim_rows.append({
            "claim_id":        claim_id,
            "employee_id":     emp["employee_id"],
            "cost_center_id":  cc,
            "policy_id":       primary_pol,
            "submission_date": submit_date.isoformat(),
            "total_amount":    total,
            "currency":        "USD",
            "num_lines":       n_lines,
            "status":          "Pending",   # will be updated after approval steps
            "purpose":         f"{dominant_cat} expenses – {submit_date.strftime('%b %Y')}",
            "anomaly_flag":    False,
            "anomaly_type":    "",
        })
        line_rows.extend(claim_lines)
        claim_idx += 1

    claims_df = pd.DataFrame(claim_rows)
    lines_df  = pd.DataFrame(line_rows)
    log.info("  ✓ Expense claims: %d rows, expense lines: %d rows",
             len(claims_df), len(lines_df))
    return claims_df, lines_df


# ═════════════════════════════════════════════════════════════════════════════
# 6. APPROVAL STEPS
# ═════════════════════════════════════════════════════════════════════════════

def _pick_approver(
    emp_id_req: str,
    approver_role: str,
    employees: pd.DataFrame,
    emp_lookup: Dict[str, dict],
    rng: np.random.Generator,
) -> str:
    """Pick an approver employee_id based on role logic."""
    requester = emp_lookup.get(emp_id_req, {})

    if approver_role == "Manager":
        mgr = requester.get("manager_id")
        if mgr and pd.notna(mgr):
            return str(mgr)

    # For Director / CFO / HR / Finance, pick from higher grade
    target_grades = {
        "Director": ["L5", "L6"],
        "CFO":      ["L6"],
        "HR":       ["L3", "L4", "L5", "L6"],
        "Finance":  ["L4", "L5", "L6"],
        "Manager":  ["L3", "L4", "L5", "L6"],
    }.get(approver_role, ["L4", "L5", "L6"])

    pool = employees[employees["job_grade"].isin(target_grades)]
    if len(pool) == 0:
        pool = employees

    # exclude the requester (normal case)
    filtered = pool[pool["employee_id"] != emp_id_req]
    if len(filtered) == 0:
        filtered = pool

    return str(filtered.sample(1, random_state=int(rng.integers(0, 2**31))).iloc[0]["employee_id"])


def generate_approval_steps(
    leave_requests:   pd.DataFrame,
    expense_claims:   pd.DataFrame,
    approval_rules:   pd.DataFrame,
    employees:        pd.DataFrame,
    rng:              np.random.Generator,
) -> pd.DataFrame:
    log.info("Generating approval steps …")

    emp_lookup = {r["employee_id"]: r.to_dict() for _, r in employees.iterrows()}

    leave_rules   = approval_rules[approval_rules["entity_type"] == "Leave"].sort_values("level")
    expense_rules = approval_rules[approval_rules["entity_type"] == "Expense"].sort_values("level")

    rows = []

    # ── Leave requests ───────────────────────────────────────────────────────
    for _, req in leave_requests.iterrows():
        if req["status"] not in ("Approved", "Rejected", "Pending"):
            continue

        step_num   = 1
        req_date   = date.fromisoformat(req["submission_date"])
        running_dt = req_date

        for _, rule in leave_rules.iterrows():
            # check condition
            if rule["condition"] == "always":
                pass
            elif rule["condition"] == "days_gt":
                if req["days_requested"] <= rule["threshold"]:
                    continue
            else:
                continue

            approver_id = _pick_approver(
                req["employee_id"], rule["approver_role"],
                employees, emp_lookup, rng
            )

            sla_dt = running_dt + timedelta(hours=int(rule["sla_hours"]))
            # actual decision within SLA (or slightly over for realism)
            decision_offset = int(rng.integers(1, int(rule["sla_hours"]) + 24))
            decision_dt = running_dt + timedelta(hours=decision_offset)

            if req["status"] == "Approved":
                step_status = "Approved"
            elif req["status"] == "Rejected" and step_num == 1:
                step_status = "Rejected"
            else:
                step_status = str(rng.choice(["Approved", "Pending"], p=[0.7, 0.3]))

            apt_id = apr_id(req["request_id"], step_num)
            rows.append({
                "step_id":         apt_id,
                "request_id":      req["request_id"],
                "entity_type":     "Leave",
                "rule_id":         rule["rule_id"],
                "level":           rule["level"],
                "approver_id":     approver_id,
                "approver_role":   rule["approver_role"],
                "assigned_date":   running_dt.isoformat(),
                "sla_due_date":    (running_dt + timedelta(hours=int(rule["sla_hours"]))).isoformat(),
                "decision_date":   decision_dt.isoformat() if step_status != "Pending" else None,
                "status":          step_status,
                "comments":        "Approved as per policy" if step_status == "Approved"
                                   else ("Insufficient balance" if step_status == "Rejected" else ""),
                "anomaly_flag":    False,
                "anomaly_type":    "",
            })
            running_dt = decision_dt
            step_num  += 1

    # ── Expense claims ───────────────────────────────────────────────────────
    for _, claim in expense_claims.iterrows():
        total  = claim["total_amount"]
        step_num   = 1
        sub_date   = date.fromisoformat(claim["submission_date"])
        running_dt = sub_date

        applicable_rules = expense_rules[
            (expense_rules["condition"] == "amount_gt") &
            (expense_rules["threshold"] < total)
        ]

        for _, rule in applicable_rules.iterrows():
            approver_id = _pick_approver(
                claim["employee_id"], rule["approver_role"],
                employees, emp_lookup, rng
            )

            decision_offset = int(rng.integers(1, int(rule["sla_hours"]) + 24))
            decision_dt     = running_dt + timedelta(hours=decision_offset)

            step_status = str(rng.choice(
                ["Approved", "Rejected", "Pending"], p=[0.70, 0.10, 0.20]
            ))

            apt_id = apr_id(claim["claim_id"], step_num)
            rows.append({
                "step_id":       apt_id,
                "request_id":    claim["claim_id"],
                "entity_type":   "Expense",
                "rule_id":       rule["rule_id"],
                "level":         rule["level"],
                "approver_id":   approver_id,
                "approver_role": rule["approver_role"],
                "assigned_date": running_dt.isoformat(),
                "sla_due_date":  (running_dt + timedelta(hours=int(rule["sla_hours"]))).isoformat(),
                "decision_date": decision_dt.isoformat() if step_status != "Pending" else None,
                "status":        step_status,
                "comments":      "Approved" if step_status == "Approved"
                                 else ("Policy violation" if step_status == "Rejected" else ""),
                "anomaly_flag":  False,
                "anomaly_type":  "",
            })
            running_dt = decision_dt
            step_num  += 1

    df = pd.DataFrame(rows)
    log.info("  ✓ Approval steps: %d rows", len(df))
    return df


def _resolve_claim_statuses(
    expense_claims:  pd.DataFrame,
    approval_steps:  pd.DataFrame,
) -> pd.DataFrame:
    """
    Update expense claim status based on their approval steps:
      - If all steps Approved → Approved
      - If any step Rejected  → Rejected
      - Otherwise             → Pending
    """
    exp_steps = approval_steps[approval_steps["entity_type"] == "Expense"].copy()
    grouped   = exp_steps.groupby("request_id")["status"].apply(list).to_dict()

    def resolve(row):
        statuses = grouped.get(row["claim_id"], [])
        if not statuses:
            return "Pending"
        if any(s == "Rejected" for s in statuses):
            return "Rejected"
        if all(s == "Approved" for s in statuses):
            return "Approved"
        return "Pending"

    expense_claims = expense_claims.copy()
    expense_claims["status"] = expense_claims.apply(resolve, axis=1)
    return expense_claims


# ═════════════════════════════════════════════════════════════════════════════
# 7. REIMBURSEMENTS
# ═════════════════════════════════════════════════════════════════════════════

def generate_reimbursements(
    expense_claims: pd.DataFrame,
    approval_steps: pd.DataFrame,
    employees:      pd.DataFrame,
    rng:            np.random.Generator,
) -> pd.DataFrame:
    log.info("Generating reimbursements …")

    approved_claims = expense_claims[expense_claims["status"] == "Approved"].copy()

    # latest approval date per claim
    exp_steps = approval_steps[
        (approval_steps["entity_type"] == "Expense") &
        (approval_steps["status"] == "Approved") &
        (approval_steps["decision_date"].notna())
    ].copy()

    latest_approval = (
        exp_steps.groupby("request_id")["decision_date"]
        .max()
        .reset_index()
        .rename(columns={"request_id": "claim_id", "decision_date": "last_approval_date"})
    )

    merged = approved_claims.merge(latest_approval, on="claim_id", how="left")

    rows = []
    rmb_idx = 1

    for _, row in merged.iterrows():
        last_appr_raw = row.get("last_approval_date")
        if pd.isna(last_appr_raw) or not last_appr_raw:
            # No dated approval – skip
            continue

        last_appr = date.fromisoformat(str(last_appr_raw)[:10])
        # payment 3-14 days after final approval
        pay_offset = int(rng.integers(3, 15))
        pay_date   = last_appr + timedelta(days=pay_offset)

        # deductions (tax, partial non-reimbursable)
        deduction_pct = round(float(rng.uniform(0.0, 0.05)), 4)
        deduction_amt = round(row["total_amount"] * deduction_pct, 2)
        net_amount    = round(row["total_amount"] - deduction_amt, 2)

        payment_methods = ["Bank Transfer", "Company Card Credit", "Cheque"]
        pay_method = str(rng.choice(payment_methods, p=[0.70, 0.20, 0.10]))

        rows.append({
            "reimbursement_id":    rmb_id(rmb_idx),
            "claim_id":            row["claim_id"],
            "employee_id":         row["employee_id"],
            "claim_amount":        row["total_amount"],
            "deduction_amount":    deduction_amt,
            "net_reimbursed":      net_amount,
            "currency":            "USD",
            "payment_date":        pay_date.isoformat(),
            "payment_method":      pay_method,
            "bank_reference":      f"REF-{rmb_idx:08d}",
            "status":              "Paid",
            "anomaly_flag":        False,
            "anomaly_type":        "",
        })
        rmb_idx += 1

    df = pd.DataFrame(rows)
    log.info("  ✓ Reimbursements: %d rows", len(df))
    return df


# ═════════════════════════════════════════════════════════════════════════════
# ANOMALY INJECTION
# ═════════════════════════════════════════════════════════════════════════════

def inject_anomalies(
    leave_balances:  pd.DataFrame,
    leave_requests:  pd.DataFrame,
    expense_claims:  pd.DataFrame,
    expense_lines:   pd.DataFrame,
    approval_steps:  pd.DataFrame,
    reimbursements:  pd.DataFrame,
    employees:       pd.DataFrame,
    rng:             np.random.Generator,
) -> Tuple[
    pd.DataFrame, pd.DataFrame, pd.DataFrame,
    pd.DataFrame, pd.DataFrame, pd.DataFrame,
    pd.DataFrame
]:
    """
    Inject labelled anomalies into the datasets.
    Returns updated DataFrames + ground_truth DataFrame.
    """
    log.info("Injecting anomalies …")
    gt_rows: List[Dict] = []
    rates = cfg.ANOMALY_RATES

    # ── 1. Negative leave balance ────────────────────────────────────────────
    n_neg = max(1, int(len(leave_balances) * rates["negative_leave_balance"]))
    neg_idx = rng.choice(leave_balances.index.tolist(), size=n_neg, replace=False)
    for i in neg_idx:
        original = leave_balances.at[i, "balance_days"]
        overdraft = round(float(rng.uniform(0.5, 5.0)), 2)
        leave_balances.at[i, "days_taken"]    = round(leave_balances.at[i, "total_available"] + overdraft, 2)
        leave_balances.at[i, "balance_days"]  = round(-overdraft, 2)
        leave_balances.at[i, "anomaly_flag"]  = True
        gt_rows.append({
            "anomaly_id":    f"ANO-NLB-{i:04d}",
            "anomaly_type":  "NegativeLeaveBalance",
            "entity":        "LeaveBalance",
            "entity_id":     f"{leave_balances.at[i,'employee_id']}|{leave_balances.at[i,'policy_id']}",
            "description":   f"Balance forced to {leave_balances.at[i,'balance_days']:.2f} days (overdraft)",
            "injected_at":   "leave_balances",
        })
    log.info("    ↳ Negative leave balance: %d", n_neg)

    # ── 2. Overlapping leave requests ────────────────────────────────────────
    n_ovl = max(1, int(len(leave_requests) * rates["overlapping_leave"]))
    # find approved requests and clone them with same employee & overlapping dates
    approved_lve = leave_requests[leave_requests["status"] == "Approved"].copy()
    if len(approved_lve) >= n_ovl:
        base_rows = approved_lve.sample(n_ovl, random_state=int(rng.integers(0, 2**31)))
        for _, base in base_rows.iterrows():
            new_start = date.fromisoformat(base["start_date"])
            new_end   = date.fromisoformat(base["end_date"])
            new_idx   = len(leave_requests)
            new_req_id = lve_id(900000 + new_idx)
            new_row = base.to_dict()
            new_row["request_id"]   = new_req_id
            new_row["start_date"]   = (new_start + timedelta(days=1)).isoformat()
            new_row["end_date"]     = (new_end + timedelta(days=1)).isoformat()
            new_row["status"]       = "Approved"
            new_row["anomaly_flag"] = True
            new_row["anomaly_type"] = "OverlappingLeave"
            leave_requests = pd.concat(
                [leave_requests, pd.DataFrame([new_row])], ignore_index=True
            )
            gt_rows.append({
                "anomaly_id":   f"ANO-OVL-{new_idx:04d}",
                "anomaly_type": "OverlappingLeave",
                "entity":       "LeaveRequest",
                "entity_id":    new_req_id,
                "description":  f"Overlaps with {base['request_id']} for employee {base['employee_id']}",
                "injected_at":  "leave_requests",
            })
    log.info("    ↳ Overlapping leave: %d", n_ovl)

    # ── 3. Expense date outside employment period ────────────────────────────
    n_emp_dt = max(1, int(len(expense_lines) * rates["expense_outside_employment"]))
    sampled_lines = expense_lines.sample(
        min(n_emp_dt, len(expense_lines)),
        random_state=int(rng.integers(0, 2**31))
    )
    for i in sampled_lines.index:
        # pick an expense date before employee's hire date
        claim_id  = expense_lines.at[i, "claim_id"]
        emp_id_cl = expense_claims.loc[
            expense_claims["claim_id"] == claim_id, "employee_id"
        ].values
        if len(emp_id_cl) == 0:
            continue
        emp_row = employees[employees["employee_id"] == emp_id_cl[0]]
        if len(emp_row) == 0:
            continue
        hire_dt = date.fromisoformat(emp_row.iloc[0]["hire_date"])
        # set expense_date 10-60 days BEFORE hire
        back_days = int(rng.integers(10, 61))
        bad_date  = hire_dt - timedelta(days=back_days)
        expense_lines.at[i, "expense_date"]   = bad_date.isoformat()
        expense_lines.at[i, "anomaly_flag"]   = True
        expense_lines.at[i, "anomaly_type"]   = "ExpenseOutsideEmployment"
        gt_rows.append({
            "anomaly_id":   f"ANO-EMP-{i:04d}",
            "anomaly_type": "ExpenseDateOutsideEmployment",
            "entity":       "ExpenseLine",
            "entity_id":    expense_lines.at[i, "line_id"],
            "description":  f"Expense date {bad_date} is before hire date {hire_dt} for employee {emp_id_cl[0]}",
            "injected_at":  "expense_lines",
        })
    log.info("    ↳ Expense outside employment: %d", n_emp_dt)

    # ── 4. Split claims to evade threshold ───────────────────────────────────
    n_split = max(1, int(len(expense_claims) * rates["split_claim_evasion"]))
    # pick claims just below L2 threshold (2000); inject a companion claim
    pol_l2 = 2000.0
    candidate_claims = expense_claims[
        (expense_claims["total_amount"] > pol_l2 * 0.4) &
        (expense_claims["total_amount"] < pol_l2 * 0.9)
    ]
    split_base = candidate_claims.sample(
        min(n_split, len(candidate_claims)),
        random_state=int(rng.integers(0, 2**31))
    )
    for _, base_cl in split_base.iterrows():
        new_cl_idx = len(expense_claims)
        new_cid    = exp_id(900000 + new_cl_idx)
        new_cl = base_cl.to_dict()
        new_cl["claim_id"]     = new_cid
        new_cl["total_amount"] = round(base_cl["total_amount"] * 0.9, 2)
        new_cl["anomaly_flag"] = True
        new_cl["anomaly_type"] = "SplitClaimEvasion"
        new_cl["num_lines"]    = 1
        expense_claims = pd.concat(
            [expense_claims, pd.DataFrame([new_cl])], ignore_index=True
        )
        gt_rows.append({
            "anomaly_id":   f"ANO-SPL-{new_cl_idx:04d}",
            "anomaly_type": "SplitClaimThresholdEvasion",
            "entity":       "ExpenseClaim",
            "entity_id":    new_cid,
            "description":  f"Clone of {base_cl['claim_id']} (amount {base_cl['total_amount']}) split to evade L2 threshold",
            "injected_at":  "expense_claims",
        })
    log.info("    ↳ Split claim evasion: %d", n_split)

    # ── 5. Missing cost center ───────────────────────────────────────────────
    n_mcc = max(1, int(len(expense_claims) * rates["missing_cost_center"]))
    mcc_idx = rng.choice(expense_claims.index.tolist(), size=n_mcc, replace=False)
    for i in mcc_idx:
        orig_cc = expense_claims.at[i, "cost_center_id"]
        expense_claims.at[i, "cost_center_id"] = None
        expense_claims.at[i, "anomaly_flag"]   = True
        expense_claims.at[i, "anomaly_type"]   = (
            expense_claims.at[i, "anomaly_type"] + "|MissingCostCenter"
            if expense_claims.at[i, "anomaly_type"] else "MissingCostCenter"
        )
        gt_rows.append({
            "anomaly_id":   f"ANO-MCC-{i:04d}",
            "anomaly_type": "MissingCostCenter",
            "entity":       "ExpenseClaim",
            "entity_id":    expense_claims.at[i, "claim_id"],
            "description":  f"Cost center removed (was {orig_cc})",
            "injected_at":  "expense_claims",
        })
    log.info("    ↳ Missing cost center: %d", n_mcc)

    # ── 6. Self-approval ─────────────────────────────────────────────────────
    n_self = max(1, int(len(approval_steps) * rates["self_approval"]))
    self_idx = rng.choice(approval_steps.index.tolist(), size=n_self, replace=False)
    for i in self_idx:
        req_id = approval_steps.at[i, "request_id"]
        # find requester
        requester_id = None
        if approval_steps.at[i, "entity_type"] == "Leave":
            m = leave_requests[leave_requests["request_id"] == req_id]
            if len(m):
                requester_id = m.iloc[0]["employee_id"]
        else:
            m = expense_claims[expense_claims["claim_id"] == req_id]
            if len(m):
                requester_id = m.iloc[0]["employee_id"]

        if requester_id:
            approval_steps.at[i, "approver_id"]   = requester_id
            approval_steps.at[i, "anomaly_flag"]  = True
            approval_steps.at[i, "anomaly_type"]  = "SelfApproval"
            gt_rows.append({
                "anomaly_id":   f"ANO-SA-{i:04d}",
                "anomaly_type": "SelfApproval",
                "entity":       "ApprovalStep",
                "entity_id":    approval_steps.at[i, "step_id"],
                "description":  f"Approver {requester_id} is same as requester on {req_id}",
                "injected_at":  "approval_steps",
            })
    log.info("    ↳ Self approval: %d", n_self)

    # ── 7. Duplicate reimbursement ───────────────────────────────────────────
    if len(reimbursements) > 0:
        n_dup = max(1, int(len(reimbursements) * rates["duplicate_reimbursement"]))
        dup_base = reimbursements.sample(
            min(n_dup, len(reimbursements)),
            random_state=int(rng.integers(0, 2**31))
        )
        new_rmb_rows = []
        for _, base_r in dup_base.iterrows():
            new_rmb_idx = len(reimbursements) + len(new_rmb_rows) + 1
            new_r = base_r.to_dict()
            new_r["reimbursement_id"] = rmb_id(900000 + new_rmb_idx)
            pay_dt = date.fromisoformat(base_r["payment_date"])
            new_r["payment_date"]  = (pay_dt + timedelta(days=int(rng.integers(1, 8)))).isoformat()
            new_r["bank_reference"] = f"REF-DUP-{new_rmb_idx:08d}"
            new_r["anomaly_flag"]  = True
            new_r["anomaly_type"]  = "DuplicateReimbursement"
            new_rmb_rows.append(new_r)
            gt_rows.append({
                "anomaly_id":   f"ANO-DUP-{new_rmb_idx:04d}",
                "anomaly_type": "DuplicateReimbursement",
                "entity":       "Reimbursement",
                "entity_id":    new_r["reimbursement_id"],
                "description":  f"Duplicate of {base_r['reimbursement_id']} for claim {base_r['claim_id']}",
                "injected_at":  "reimbursements",
            })
        if new_rmb_rows:
            reimbursements = pd.concat(
                [reimbursements, pd.DataFrame(new_rmb_rows)], ignore_index=True
            )
        log.info("    ↳ Duplicate reimbursement: %d", len(new_rmb_rows))

    ground_truth = pd.DataFrame(gt_rows)
    log.info("  ✓ Total anomalies injected: %d", len(ground_truth))

    return (
        leave_balances, leave_requests, expense_claims,
        expense_lines, approval_steps, reimbursements,
        ground_truth,
    )


# ═════════════════════════════════════════════════════════════════════════════
# VALIDATION REPORT (inline, written after generation)
# ═════════════════════════════════════════════════════════════════════════════

def _validate_and_report(
    employees:        pd.DataFrame,
    leave_balances:   pd.DataFrame,
    leave_requests:   pd.DataFrame,
    expense_claims:   pd.DataFrame,
    expense_lines:    pd.DataFrame,
    approval_steps:   pd.DataFrame,
    reimbursements:   pd.DataFrame,
    ground_truth:     pd.DataFrame,
) -> str:
    checks = []

    def chk(name: str, passed: bool, detail: str = ""):
        status = "✅ PASS" if passed else "❌ FAIL"
        checks.append(f"| {name} | {status} | {detail} |")

    # row counts
    chk("Employee count > 0",    len(employees) > 0,       f"{len(employees)} rows")
    chk("Leave requests > 0",    len(leave_requests) > 0,  f"{len(leave_requests)} rows")
    chk("Expense claims > 0",    len(expense_claims) > 0,  f"{len(expense_claims)} rows")
    chk("Expense lines > 0",     len(expense_lines) > 0,   f"{len(expense_lines)} rows")
    chk("Approval steps > 0",    len(approval_steps) > 0,  f"{len(approval_steps)} rows")
    chk("Reimbursements > 0",    len(reimbursements) > 0,  f"{len(reimbursements)} rows")
    chk("Ground truth > 0",      len(ground_truth) > 0,    f"{len(ground_truth)} anomalies")

    # Leave balances: should have negatives (injected)
    neg_bal = (leave_balances["balance_days"] < 0).sum()
    chk("Negative leave balances injected", neg_bal > 0, f"{neg_bal} records")

    # Reimbursements only for approved claims
    if len(reimbursements) > 0:
        rmb_claims = set(reimbursements["claim_id"].tolist())
        all_approved = expense_claims[expense_claims["status"] == "Approved"]["claim_id"].tolist()
        # (duplicates are allowed – they are anomalies)
        non_approved_rmb = rmb_claims - set(all_approved)
        chk("All reimbursements linked to approved claims",
            len(non_approved_rmb) == 0, f"{len(non_approved_rmb)} orphan reimbursements")

    # Approval steps reference valid request IDs
    all_req_ids  = set(leave_requests["request_id"].tolist()) | set(expense_claims["claim_id"].tolist())
    apr_req_ids  = set(approval_steps["request_id"].tolist())
    orphan_steps = apr_req_ids - all_req_ids
    chk("Approval steps reference valid IDs", len(orphan_steps) == 0,
        f"{len(orphan_steps)} orphan step IDs")

    # Expense lines reference valid claim IDs
    claim_ids   = set(expense_claims["claim_id"].tolist())
    line_cids   = set(expense_lines["claim_id"].tolist())
    orphan_lines = line_cids - claim_ids
    chk("Expense lines reference valid claim IDs", len(orphan_lines) == 0,
        f"{len(orphan_lines)} orphan line claim IDs")

    # Duplicate reimbursement anomalies present
    dup_rmb = (ground_truth["anomaly_type"] == "DuplicateReimbursement").sum()
    chk("Duplicate reimbursements injected", dup_rmb > 0, f"{dup_rmb} records")

    # Self-approval anomalies present
    self_apr = (ground_truth["anomaly_type"] == "SelfApproval").sum()
    chk("Self-approval anomalies injected", self_apr > 0, f"{self_apr} records")

    # Date chronology: leave start >= submission
    lve = leave_requests.copy()
    lve["start_date"]      = pd.to_datetime(lve["start_date"])
    lve["submission_date"] = pd.to_datetime(lve["submission_date"])
    bad_dates = (lve["start_date"] < lve["submission_date"]).sum()
    chk("Leave start_date >= submission_date", bad_dates == 0, f"{bad_dates} violations")

    # Ground truth covers all 7 anomaly types
    all_types = set(ground_truth["anomaly_type"].tolist())
    expected_types = {
        "NegativeLeaveBalance", "OverlappingLeave",
        "ExpenseDateOutsideEmployment", "SplitClaimThresholdEvasion",
        "MissingCostCenter", "SelfApproval", "DuplicateReimbursement",
    }
    missing_types = expected_types - all_types
    chk("All 7 anomaly types present in ground truth", len(missing_types) == 0,
        f"Missing: {missing_types if missing_types else 'None'}")

    header = (
        "# Validation Report\n\n"
        "| Check | Status | Detail |\n"
        "|-------|--------|--------|\n"
    )
    return header + "\n".join(checks) + "\n"


# ═════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ═════════════════════════════════════════════════════════════════════════════

def run(scale: str, seed: int, out_dir: str = ".") -> None:
    log.info("=" * 60)
    log.info("Leave & Expense Synthetic Data Generator")
    log.info("Scale: %s | Seed: %d", scale, seed)
    log.info("=" * 60)

    preset = cfg.SCALE_PRESETS[scale]
    rng    = _rng(seed)

    # ── 1. Employees ─────────────────────────────────────────────────────────
    employees = generate_employees(rng, preset["num_employees"])

    # ── 2a-d. Static reference data ──────────────────────────────────────────
    leave_policies    = generate_leave_policies()
    expense_policies  = generate_expense_policies()
    cost_centers      = generate_cost_centers(rng, preset["num_cost_centers"])
    approval_rules    = generate_approval_rules()

    # ── 3. Leave balances ────────────────────────────────────────────────────
    leave_balances = generate_leave_balances(employees, leave_policies, rng)

    # ── 4. Leave requests ────────────────────────────────────────────────────
    leave_requests = generate_leave_requests(
        employees, leave_policies, leave_balances, rng,
        preset["num_leave_requests"],
    )

    # ── 5. Expense claims + lines ─────────────────────────────────────────────
    expense_claims, expense_lines = generate_expense_claims_and_lines(
        employees, expense_policies, cost_centers, rng,
        preset["num_expense_claims"],
        preset["expense_lines_range"],
    )

    # ── 6. Approval steps ────────────────────────────────────────────────────
    approval_steps = generate_approval_steps(
        leave_requests, expense_claims, approval_rules, employees, rng
    )

    # Resolve claim statuses based on approval steps
    expense_claims = _resolve_claim_statuses(expense_claims, approval_steps)

    # ── 7. Reimbursements ────────────────────────────────────────────────────
    reimbursements = generate_reimbursements(
        expense_claims, approval_steps, employees, rng
    )

    # ── Anomaly injection ────────────────────────────────────────────────────
    (
        leave_balances, leave_requests, expense_claims,
        expense_lines, approval_steps, reimbursements,
        ground_truth,
    ) = inject_anomalies(
        leave_balances, leave_requests, expense_claims,
        expense_lines, approval_steps, reimbursements,
        employees, rng,
    )

    # ── Write CSVs ───────────────────────────────────────────────────────────
    data_path = Path(out_dir) / cfg.DATA_DIR
    data_path.mkdir(parents=True, exist_ok=True)

    outputs: Dict[str, pd.DataFrame] = {
        "employees.csv":       employees,
        "leave_policies.csv":  leave_policies,
        "leave_balances.csv":  leave_balances,
        "leave_requests.csv":  leave_requests,
        "expense_policies.csv": expense_policies,
        "expense_claims.csv":  expense_claims,
        "expense_lines.csv":   expense_lines,
        "cost_centers.csv":    cost_centers,
        "approval_rules.csv":  approval_rules,
        "approval_steps.csv":  approval_steps,
        "reimbursements.csv":  reimbursements,
        "ground_truth.csv":    ground_truth,
    }

    for fname, df in outputs.items():
        fpath = data_path / fname
        df.to_csv(fpath, index=False)
        log.info("  Wrote %s (%d rows)", fname, len(df))

    # ── Validation report ────────────────────────────────────────────────────
    report = _validate_and_report(
        employees, leave_balances, leave_requests,
        expense_claims, expense_lines, approval_steps,
        reimbursements, ground_truth,
    )
    val_path = Path(out_dir) / cfg.VALIDATION_DIR
    val_path.mkdir(parents=True, exist_ok=True)
    (val_path / "validation_report.md").write_text(report, encoding="utf-8")
    log.info("  Wrote validation/validation_report.md")

    log.info("=" * 60)
    log.info("Generation complete. Output → %s", data_path.resolve())
    log.info("=" * 60)


# ═════════════════════════════════════════════════════════════════════════════
# CLI
# ═════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Synthetic Leave & Expense data generator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--scale",
        choices=list(cfg.SCALE_PRESETS.keys()),
        default=cfg.DEFAULT_SCALE,
        help="Dataset scale preset",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=cfg.DEFAULT_SEED,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--out-dir",
        default=".",
        help="Root output directory (data/ and validation/ are created inside it)",
    )
    args = parser.parse_args()
    run(scale=args.scale, seed=args.seed, out_dir=args.out_dir)


if __name__ == "__main__":
    main()
