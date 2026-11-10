"""
config.py
---------
Central configuration for the Leave & Expense Synthetic Data Generator.
All tuneable parameters live here; generate_data.py imports from this module.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Scale presets
# ---------------------------------------------------------------------------
SCALE_PRESETS: Dict[str, Dict] = {
    "full": {
        "num_employees":      400,
        "num_leave_policies": 6,
        "num_expense_policies": 4,
        "num_cost_centers":   20,
        "num_leave_requests": 800,
        "num_expense_claims": 1000,
        "expense_lines_range": (1, 10),   # min/max lines per claim
    },
    "small": {
        "num_employees":      50,
        "num_leave_policies": 6,
        "num_expense_policies": 4,
        "num_cost_centers":   10,
        "num_leave_requests": 100,
        "num_expense_claims": 150,
        "expense_lines_range": (1, 5),
    },
}

DEFAULT_SEED  = 20261022
DEFAULT_SCALE = "full"

# ---------------------------------------------------------------------------
# Simulation reference year / date window
# ---------------------------------------------------------------------------
REFERENCE_YEAR       = 2026
EMPLOYMENT_START_MIN = "2018-01-01"   # earliest hire date
EMPLOYMENT_START_MAX = "2025-12-31"   # latest hire date
REQUEST_WINDOW_START = "2026-01-01"   # leave/expense requests begin
REQUEST_WINDOW_END   = "2026-10-31"   # leave/expense requests end

# ---------------------------------------------------------------------------
# Employee demographics / org
# ---------------------------------------------------------------------------
DEPARTMENTS: List[str] = [
    "Engineering", "Finance", "HR", "Marketing",
    "Operations", "Legal", "Sales", "Product",
]

JOB_GRADES: List[str] = ["L1", "L2", "L3", "L4", "L5", "L6"]

GRADE_SALARY_RANGE: Dict[str, Tuple[float, float]] = {
    "L1": (30_000,  50_000),
    "L2": (50_001,  80_000),
    "L3": (80_001, 120_000),
    "L4": (120_001, 180_000),
    "L5": (180_001, 250_000),
    "L6": (250_001, 400_000),
}

EMPLOYMENT_TYPES: List[str] = ["Full-Time", "Part-Time", "Contract"]
EMPLOYMENT_TYPE_WEIGHTS: List[float] = [0.75, 0.15, 0.10]

LOCATIONS: List[str] = [
    "New York", "London", "Singapore", "Bangalore",
    "Dubai", "Sydney", "Toronto", "Berlin",
]

# ---------------------------------------------------------------------------
# Leave policy definitions
# ---------------------------------------------------------------------------
LEAVE_POLICY_TEMPLATES: List[Dict] = [
    {
        "policy_id":          "LP-001",
        "policy_name":        "Annual Leave – Standard",
        "leave_type":         "Annual",
        "accrual_days_per_year": 20,
        "max_carry_forward":  5,
        "max_consecutive_days": 15,
        "notice_period_days": 7,
        "applicable_grades":  ["L1", "L2", "L3"],
        "requires_approval":  True,
    },
    {
        "policy_id":          "LP-002",
        "policy_name":        "Annual Leave – Senior",
        "leave_type":         "Annual",
        "accrual_days_per_year": 25,
        "max_carry_forward":  10,
        "max_consecutive_days": 20,
        "notice_period_days": 7,
        "applicable_grades":  ["L4", "L5", "L6"],
        "requires_approval":  True,
    },
    {
        "policy_id":          "LP-003",
        "policy_name":        "Sick Leave",
        "leave_type":         "Sick",
        "accrual_days_per_year": 12,
        "max_carry_forward":  0,
        "max_consecutive_days": 5,
        "notice_period_days": 0,
        "applicable_grades":  ["L1", "L2", "L3", "L4", "L5", "L6"],
        "requires_approval":  True,
    },
    {
        "policy_id":          "LP-004",
        "policy_name":        "Maternity Leave",
        "leave_type":         "Maternity",
        "accrual_days_per_year": 90,
        "max_carry_forward":  0,
        "max_consecutive_days": 90,
        "notice_period_days": 30,
        "applicable_grades":  ["L1", "L2", "L3", "L4", "L5", "L6"],
        "requires_approval":  True,
    },
    {
        "policy_id":          "LP-005",
        "policy_name":        "Paternity Leave",
        "leave_type":         "Paternity",
        "accrual_days_per_year": 10,
        "max_carry_forward":  0,
        "max_consecutive_days": 10,
        "notice_period_days": 14,
        "applicable_grades":  ["L1", "L2", "L3", "L4", "L5", "L6"],
        "requires_approval":  True,
    },
    {
        "policy_id":          "LP-006",
        "policy_name":        "Unpaid Leave",
        "leave_type":         "Unpaid",
        "accrual_days_per_year": 30,
        "max_carry_forward":  0,
        "max_consecutive_days": 30,
        "notice_period_days": 14,
        "applicable_grades":  ["L1", "L2", "L3", "L4", "L5", "L6"],
        "requires_approval":  True,
    },
]

# ---------------------------------------------------------------------------
# Expense policy definitions
# ---------------------------------------------------------------------------
EXPENSE_POLICY_TEMPLATES: List[Dict] = [
    {
        "policy_id":              "EP-001",
        "policy_name":            "Travel & Subsistence",
        "category":               "Travel",
        "per_diem_limit":         150.0,
        "single_receipt_limit":   500.0,
        "monthly_claim_limit":    3000.0,
        "requires_receipt_above": 25.0,
        "approval_threshold_l1":  500.0,    # manager approval
        "approval_threshold_l2":  2000.0,   # director approval
        "approval_threshold_l3":  5000.0,   # CFO approval
        "reimbursable":           True,
    },
    {
        "policy_id":              "EP-002",
        "policy_name":            "Meals & Entertainment",
        "category":               "Meals",
        "per_diem_limit":         75.0,
        "single_receipt_limit":   200.0,
        "monthly_claim_limit":    1000.0,
        "requires_receipt_above": 25.0,
        "approval_threshold_l1":  200.0,
        "approval_threshold_l2":  800.0,
        "approval_threshold_l3":  2000.0,
        "reimbursable":           True,
    },
    {
        "policy_id":              "EP-003",
        "policy_name":            "Office Supplies",
        "category":               "Office",
        "per_diem_limit":         0.0,
        "single_receipt_limit":   300.0,
        "monthly_claim_limit":    500.0,
        "requires_receipt_above": 10.0,
        "approval_threshold_l1":  300.0,
        "approval_threshold_l2":  1000.0,
        "approval_threshold_l3":  3000.0,
        "reimbursable":           True,
    },
    {
        "policy_id":              "EP-004",
        "policy_name":            "Training & Conferences",
        "category":               "Training",
        "per_diem_limit":         0.0,
        "single_receipt_limit":   5000.0,
        "monthly_claim_limit":    10000.0,
        "requires_receipt_above": 50.0,
        "approval_threshold_l1":  500.0,
        "approval_threshold_l2":  2000.0,
        "approval_threshold_l3":  8000.0,
        "reimbursable":           True,
    },
]

# ---------------------------------------------------------------------------
# Approval rule definitions
# ---------------------------------------------------------------------------
APPROVAL_RULE_TEMPLATES: List[Dict] = [
    # Leave approval
    {
        "rule_id":        "AR-001",
        "rule_name":      "Leave – Manager Approval",
        "entity_type":    "Leave",
        "condition":      "always",
        "threshold":      0.0,
        "approver_role":  "Manager",
        "level":          1,
        "sla_hours":      48,
    },
    {
        "rule_id":        "AR-002",
        "rule_name":      "Leave – HR Review (>10 days)",
        "entity_type":    "Leave",
        "condition":      "days_gt",
        "threshold":      10.0,
        "approver_role":  "HR",
        "level":          2,
        "sla_hours":      72,
    },
    # Expense approval – tier 1
    {
        "rule_id":        "AR-003",
        "rule_name":      "Expense – Manager (>$0)",
        "entity_type":    "Expense",
        "condition":      "amount_gt",
        "threshold":      0.0,
        "approver_role":  "Manager",
        "level":          1,
        "sla_hours":      48,
    },
    # Expense approval – tier 2
    {
        "rule_id":        "AR-004",
        "rule_name":      "Expense – Director (>$2 000)",
        "entity_type":    "Expense",
        "condition":      "amount_gt",
        "threshold":      2000.0,
        "approver_role":  "Director",
        "level":          2,
        "sla_hours":      72,
    },
    # Expense approval – tier 3
    {
        "rule_id":        "AR-005",
        "rule_name":      "Expense – CFO (>$5 000)",
        "entity_type":    "Expense",
        "condition":      "amount_gt",
        "threshold":      5000.0,
        "approver_role":  "CFO",
        "level":          3,
        "sla_hours":      96,
    },
    # Finance check
    {
        "rule_id":        "AR-006",
        "rule_name":      "Expense – Finance Audit (>$10 000)",
        "entity_type":    "Expense",
        "condition":      "amount_gt",
        "threshold":      10000.0,
        "approver_role":  "Finance",
        "level":          4,
        "sla_hours":      120,
    },
]

# ---------------------------------------------------------------------------
# Anomaly injection rates  (fraction of records affected)
# ---------------------------------------------------------------------------
ANOMALY_RATES: Dict[str, float] = {
    "negative_leave_balance":        0.02,   # ~2 % of leave balances
    "overlapping_leave":             0.015,  # ~1.5 % of leave requests
    "expense_outside_employment":    0.01,   # ~1 % of expense lines
    "split_claim_evasion":           0.02,   # ~2 % of expense claims
    "missing_cost_center":           0.015,  # ~1.5 % of expense claims
    "self_approval":                 0.01,   # ~1 % of approval steps
    "duplicate_reimbursement":       0.01,   # ~1 % of reimbursements
}

# ---------------------------------------------------------------------------
# Output paths (relative to project root)
# ---------------------------------------------------------------------------
DATA_DIR       = "data"
SCHEMA_DIR     = "schema"
VALIDATION_DIR = "validation"

