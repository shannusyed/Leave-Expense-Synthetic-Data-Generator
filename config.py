"""
Configuration constants for the Leave & Expense Synthetic Data Generator.

All tuneable parameters live here so that generate_data.py and engine.py
stay free of magic numbers.  The SEED value and the numpy Generator
instance created from it are the single source of randomness for the
entire pipeline – nothing else may create its own RNG.
"""

# ── Reproducibility ─────────────────────────────────────────────────
SEED = 20261022

# ── Volume targets (non-negotiable) ────────────────────────────────
NUM_EMPLOYEES       = 400
NUM_LEAVE_POLICIES  = 6
NUM_LEAVE_REQUESTS  = 800
NUM_EXPENSE_CLAIMS  = 1000
EXPENSE_LINES_MIN   = 1
EXPENSE_LINES_MAX   = 10

# ── Date range ──────────────────────────────────────────────────────
FISCAL_YEAR_START = "2025-01-01"
FISCAL_YEAR_END   = "2025-12-31"
HIRE_DATE_RANGE   = ("2018-01-01", "2025-06-30")

# ── Org hierarchy ───────────────────────────────────────────────────
DEPARTMENTS = [
    "Engineering", "Sales", "Marketing", "Finance",
    "HR", "Operations", "Legal", "Product",
]
COST_CENTERS = [
    {"cost_center_id": f"CC{str(i+1).zfill(3)}", "name": dept, "budget": budget}
    for i, (dept, budget) in enumerate(zip(
        DEPARTMENTS,
        [500_000, 400_000, 350_000, 300_000, 250_000, 450_000, 200_000, 380_000],
    ))
]
DESIGNATIONS = [
    "Junior Engineer", "Senior Engineer", "Team Lead",
    "Manager", "Senior Manager", "Director", "VP",
]
# Mapping designation → hierarchy level (higher = more senior)
DESIGNATION_LEVEL = {d: i for i, d in enumerate(DESIGNATIONS)}

# ── Leave policies ──────────────────────────────────────────────────
LEAVE_TYPES = [
    {"policy_id": "LP001", "leave_type": "Earned Leave",       "annual_quota": 18, "max_consecutive_days": 10, "min_notice_days": 7,  "carry_forward": True,  "encashable": True},
    {"policy_id": "LP002", "leave_type": "Sick Leave",          "annual_quota": 12, "max_consecutive_days": 7,  "min_notice_days": 0,  "carry_forward": False, "encashable": False},
    {"policy_id": "LP003", "leave_type": "Casual Leave",        "annual_quota": 8,  "max_consecutive_days": 3,  "min_notice_days": 1,  "carry_forward": False, "encashable": False},
    {"policy_id": "LP004", "leave_type": "Maternity Leave",     "annual_quota": 180,"max_consecutive_days": 180,"min_notice_days": 30, "carry_forward": False, "encashable": False},
    {"policy_id": "LP005", "leave_type": "Paternity Leave",     "annual_quota": 15, "max_consecutive_days": 15, "min_notice_days": 15, "carry_forward": False, "encashable": False},
    {"policy_id": "LP006", "leave_type": "Compensatory Off",    "annual_quota": 4,  "max_consecutive_days": 2,  "min_notice_days": 1,  "carry_forward": False, "encashable": False},
]

# ── Expense policies ───────────────────────────────────────────────
EXPENSE_CATEGORIES = ["Travel", "Meals", "Accommodation", "Software", "Office Supplies", "Training", "Client Entertainment"]
EXPENSE_POLICIES = [
    {"policy_id": "EP001", "category": "Travel",              "single_receipt_limit": 5000,  "monthly_limit": 25000, "receipt_required_above": 500,  "requires_pre_approval_above": 10000},
    {"policy_id": "EP002", "category": "Meals",               "single_receipt_limit": 1500,  "monthly_limit": 8000,  "receipt_required_above": 200,  "requires_pre_approval_above": 5000},
    {"policy_id": "EP003", "category": "Accommodation",       "single_receipt_limit": 8000,  "monthly_limit": 30000, "receipt_required_above": 500,  "requires_pre_approval_above": 15000},
    {"policy_id": "EP004", "category": "Software",            "single_receipt_limit": 20000, "monthly_limit": 50000, "receipt_required_above": 1000, "requires_pre_approval_above": 20000},
    {"policy_id": "EP005", "category": "Office Supplies",     "single_receipt_limit": 3000,  "monthly_limit": 10000, "receipt_required_above": 300,  "requires_pre_approval_above": 8000},
    {"policy_id": "EP006", "category": "Training",            "single_receipt_limit": 15000, "monthly_limit": 40000, "receipt_required_above": 1000, "requires_pre_approval_above": 20000},
    {"policy_id": "EP007", "category": "Client Entertainment","single_receipt_limit": 10000, "monthly_limit": 30000, "receipt_required_above": 500,  "requires_pre_approval_above": 15000},
]
EXPENSE_POLICY_MAP = {p["category"]: p for p in EXPENSE_POLICIES}

# ── Approval routing thresholds ─────────────────────────────────────
APPROVAL_RULES = [
    {"rule_id": "AR001", "entity_type": "leave",   "condition": "days <= 3",            "levels": 1, "approver_role": "Manager"},
    {"rule_id": "AR002", "entity_type": "leave",   "condition": "days > 3 and days <=7","levels": 2, "approver_role": "Manager,Senior Manager"},
    {"rule_id": "AR003", "entity_type": "leave",   "condition": "days > 7",             "levels": 3, "approver_role": "Manager,Senior Manager,Director"},
    {"rule_id": "AR004", "entity_type": "expense", "condition": "amount <= 5000",       "levels": 1, "approver_role": "Manager"},
    {"rule_id": "AR005", "entity_type": "expense", "condition": "amount > 5000 and amount <= 20000","levels": 2, "approver_role": "Manager,Senior Manager"},
    {"rule_id": "AR006", "entity_type": "expense", "condition": "amount > 20000",       "levels": 3, "approver_role": "Manager,Senior Manager,Director"},
]

# ── Anomaly injection targets (fractions of the relevant volume) ───
ANOMALY_RATES = {
    "missing_receipt":         0.05,   # ~50 expense lines
    "duplicate_receipt":       0.02,   # ~20 expense lines
    "policy_limit_breach":     0.03,   # ~30 expense lines
    "overlapping_leave":       0.03,   # ~24 leave requests
    "insufficient_balance":    0.04,   # ~32 leave requests
    "self_approval":           0.02,   # ~16 leave requests + ~20 expense claims
    "expense_outside_dates":   0.02,   # ~20 expense claims
    "missing_cost_center":     0.02,   # ~20 expense claims
    "duplicate_reimbursement": 0.015,  # ~15 reimbursements
    "holiday_span":            0.03,   # ~24 leave requests
    "split_claim":             0.02,   # ~20 expense claims
}

# ── Indian public holidays 2025 ────────────────────────────────────
HOLIDAYS = [
    "2025-01-01",  # New Year's Day
    "2025-01-14",  # Makar Sankranti
    "2025-01-26",  # Republic Day
    "2025-03-14",  # Holi
    "2025-03-31",  # Id-ul-Fitr (approx)
    "2025-04-06",  # Ram Navami
    "2025-04-10",  # Mahavir Jayanti
    "2025-04-14",  # Ambedkar Jayanti
    "2025-04-18",  # Good Friday
    "2025-05-01",  # May Day
    "2025-05-12",  # Buddha Purnima
    "2025-06-07",  # Id-ul-Adha (approx)
    "2025-07-06",  # Muharram (approx)
    "2025-08-15",  # Independence Day
    "2025-08-16",  # Janmashtami
    "2025-09-05",  # Milad-un-Nabi (approx)
    "2025-10-02",  # Gandhi Jayanti
    "2025-10-20",  # Dussehra
    "2025-11-01",  # Diwali (approx)
    "2025-11-05",  # Guru Nanak Jayanti
    "2025-12-25",  # Christmas
]

# ── Status workflows ───────────────────────────────────────────────
LEAVE_STATUSES  = ["Draft", "Submitted", "Under Review", "Approved", "Rejected", "Cancelled"]
EXPENSE_STATUSES = ["Draft", "Submitted", "Under Review", "Approved", "Rejected", "Cancelled"]
