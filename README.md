# Leave & Expense Synthetic Data Generator

A **deterministic**, **rule-driven** synthetic data generator that produces a
realistic Leave & Expense Management dataset suitable for building anomaly
detection models, testing approval workflows, and evaluating data-quality
pipelines.

## ✨ Key Features

| Feature | Status |
|---------|--------|
| 100% reproducible (seed `20261022`) | ✅ |
| Zero ground-truth leakage | ✅ |
| Rule-driven decision engine | ✅ |
| Exact volumes (400/6/800/1000) | ✅ |
| Status-event history (append-only) | ✅ |
| 11 anomaly scenarios injected in-place | ✅ |
| Holiday-aware business-day logic | ✅ |
| Comprehensive validation (61 checks) | ✅ |
| **Runtime anomaly detection** | ✅ |
| pytest suite (36 tests) | ✅ |

## 📁 Project Structure

```
leave_expense_synthetic/
├── generate_data.py          # Main generator (single RNG, sorted intermediates)
├── engine.py                 # Deterministic rule-driven decision engine
├── config.py                 # All constants, volumes, policies, seed
├── validate.py               # 56-check data-quality validator
├── scripts/
│   └── repro_check.py        # SHA-256 reproducibility verifier
├── schema/
│   └── data_dictionary.md    # Full schema documentation
├── data/                     # Generated CSV output (13 files)
├── validation/
│   └── validation_report.md  # Validation results
├── tests/
│   └── test_data.py          # 36 pytest tests
├── README.md
└── requirements.txt
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Generate the Dataset
```bash
# Generate the dataset with 400 employees, 800 leave requests, 1000 expense claims
python generate_data.py
```

Expected output:
```
✅ Generating 400 employees...
✅ Generating 800 leave requests...
✅ Generating 1000 expense claims...
✅ All data generated successfully!
Generated CSV files in data/ directory
```

### 3. Run Validation (61 checks)
```bash
python validate.py
```

This validates:
- Volume targets
- PK uniqueness & FK integrity
- Zero ground-truth leakage
- ID formats & date ordering
- Approval sequence correctness
- Balance reconciliation

### 4. Run Tests (36 tests)
```bash
python -m pytest tests/ -v
```

### 5. Verify Reproducibility
```bash
python scripts/repro_check.py
```

## 📊 Interactive Dashboard

Launch the **interactive Streamlit dashboard** to explore leave & expense data, approval chains, anomalies, and validation results:

### Install Streamlit
```bash
python -m pip install streamlit
```

### Run the Dashboard
```bash
python -m streamlit run streamlit_app.py
```

**Dashboard opens at:** http://localhost:8501

**Features:**
- **🏠 Home**: System overview with key metrics
- **✅ Approval Decisions**: Search leave/expense by ID; view complete approval chains and decisions
- **🔍 Anomaly Detection**: Browse all detected anomalies:
  - Duplicate receipts (fraud indicator)
  - Split claims (threshold evasion)
  - Self-approvals (conflict of interest)
  - Duplicate reimbursements (payment fraud)
- **📊 Data Quality**: Run and view 61 validation checks in real-time
- **📝 Audit Trail**: View complete status event history for any entity

All anomalies are detected at **runtime** from the generated data (not pre-labeled).

### Dashboard Output Examples

**Anomaly Detection Page:**
- Each anomaly shows clean, readable information (not JSON)
- Displays: Employee ID, Claim ID, Severity Level, Anomaly Type, Description
- Sortable by anomaly type: receipts, splits, self-approvals, reimbursements

**Approval Decisions Page:**
- Enter any Leave Request ID (LRxxxx) or Expense Claim ID (ECxxxx)
- View complete approval routing with all decision levels
- Shows approver role, decision, date, and reason code

**Data Quality Page:**
- Click "Run Validation" to execute 61 checks
- Displays pass/fail status for each validation category
- Shows volume targets vs. actual counts

## 📊 Generated Tables

| Table | File | Volume | Description |
|-------|------|--------|-------------|
| Employees | `employees.csv` | 400 | Employee master data with hierarchy |
| Cost Centers | `cost_centers.csv` | 8 | Department cost centres |
| Leave Policies | `leave_policies.csv` | 6 | Leave-type rules and quotas |
| Expense Policies | `expense_policies.csv` | 7 | Category-level spending limits |
| Approval Rules | `approval_rules.csv` | 6 | Multi-level routing thresholds |
| Leave Balances | `leave_balances.csv` | 2,400 | Per-employee per-type balances |
| Leave Requests | `leave_requests.csv` | 800 | Leave applications |
| Expense Claims | `expense_claims.csv` | 1,000 | Expense reimbursement claims |
| Expense Lines | `expense_lines.csv` | ~5,350 | Individual line items (1–10 per claim) |
| Approval Steps | `approval_steps.csv` | ~3,200 | Multi-level approval history |
| Reimbursements | `reimbursements.csv` | ~385 | Processed payments |
| Status Events | `status_events.csv` | 5,400 | Append-only state transitions |
| Ground Truth | `ground_truth.csv` | ~279 | Anomaly labels (for evaluation only) |

## 🔒 Reproducibility Proof

The generator uses a single `numpy.random.Generator` seeded with `20261022`.
All intermediate iterations over sets/dicts are explicitly sorted for
determinism.  Running `scripts/repro_check.py` confirms that two consecutive
runs produce identical SHA-256 checksums:

```
Run 1 …
Run 2 …
  ✅  approval_rules.csv
  ✅  approval_steps.csv
  ✅  cost_centers.csv
  ✅  employees.csv
  ✅  expense_claims.csv
  ✅  expense_lines.csv
  ✅  expense_policies.csv
  ✅  ground_truth.csv
  ✅  leave_balances.csv
  ✅  leave_policies.csv
  ✅  leave_requests.csv
  ✅  reimbursements.csv
  ✅  status_events.csv

✅  All files match — generation is fully reproducible!
```

## ⚙️ Decision Engine (`engine.py`)

All approval decisions are **computed from business rules**, not random:

### Leave Decision Rules (evaluated in order)
1. **Employment dates** — reject if leave starts before hire or ends after termination
2. **Insufficient balance** — reject if requested days > remaining balance
3. **Max consecutive days** — reject if exceeds policy limit
4. **Notice period** — reject if applied too late (for non-sick leave)
5. **Overlapping leave** — reject if dates overlap with existing approved leave
6. Otherwise → **Approved**

### Expense Decision Rules
1. **Employment dates** — reject if claim date outside employment period
2. **Missing cost centre** — reject if no cost centre assigned
3. **Line-level policy violations** — reject if any line breaches single-receipt limit or is missing a required receipt
4. Otherwise → **Approved**

### Approval Routing
| Entity | Condition | Levels | Approver Roles |
|--------|-----------|--------|----------------|
| Leave | ≤ 3 days | 1 | Manager |
| Leave | 4–7 days | 2 | Manager → Senior Manager |
| Leave | > 7 days | 3 | Manager → Senior Manager → Director |
| Expense | ≤ ₹5,000 | 1 | Manager |
| Expense | ₹5,001–20,000 | 2 | Manager → Senior Manager |
| Expense | > ₹20,000 | 3 | Manager → Senior Manager → Director |

Rejection at any level terminates the chain — subsequent steps are **Skipped**.

## 🔍 Runtime Anomaly Detection (`engine.py`)

The engine includes **four runtime anomaly detection functions** that analyze operational data to discover issues:

### `detect_duplicate_receipts(claims, lines)`
Finds expense lines with identical receipt hashes across different claims (fraud indicator).

**Example:**
```python
anomalies = engine.detect_duplicate_receipts(claims, lines)
# Returns: [
#   {
#     "anomaly_type": "duplicate_receipt",
#     "severity": "HIGH",
#     "claim_ids": ["EC0040", "EC0035"],
#     "line_ids": ["EL00268", "EL04894"],
#     "receipt_hash": "ba77a2d339533012...",
#     "description": "Receipt ba77a2d3... used on 2 lines across 2 claims"
#   }
# ]
```

### `detect_split_claims(claims, lines)`
Identifies claims artificially split to evade approval thresholds.

**Logic:** Groups claims by (employee, cost_center) within 7 days. Flags if group total > ₹20k but individual claims ≤ ₹20k.

**Example:**
```python
anomalies = engine.detect_split_claims(claims, lines)
# Returns: [
#   {
#     "anomaly_type": "split_claim",
#     "severity": "MEDIUM",
#     "employee_id": "EMP0362",
#     "claim_ids": ["EC0362", "EC0762"],
#     "group_total": 25445,
#     "description": "2 claims totaling ₹25,445 (threshold ₹20,000)"
#   }
# ]
```

### `detect_self_approval(approval_steps, claims, employees)`
Flags cases where an employee is their own first-level approver (conflict of interest).

**Example:**
```python
anomalies = engine.detect_self_approval(approval_steps, claims, employees)
# Returns: [
#   {
#     "anomaly_type": "self_approval",
#     "severity": "HIGH",
#     "employee_id": "EMP0016",
#     "claim_id": "EC0016",
#     "description": "Employee EMP0016 is first-level approver for their own claim"
#   }
# ]
```

### `detect_duplicate_reimbursements(reimbursements)`
Finds claims that have been reimbursed multiple times (payment fraud).

**Example:**
```python
anomalies = engine.detect_duplicate_reimbursements(reimbursements)
# Returns: [
#   {
#     "anomaly_type": "duplicate_reimbursement",
#     "severity": "CRITICAL",
#     "claim_id": "EC0155",
#     "reimbursement_ids": ["RB0065", "RB0066"],
#     "count": 2,
#     "description": "Claim EC0155 reimbursed 2 times"
#   }
# ]
```

### `run_all_anomaly_detection(employees, claims, lines, approval_steps, reimbursements)`
Master function that runs all detection checks and returns comprehensive results.

**Usage:**
```python
import csv
import engine

# Load data
def load_csv(name):
    with open(f"data/{name}", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

employees = load_csv("employees.csv")
claims = load_csv("expense_claims.csv")
lines = load_csv("expense_lines.csv")
approval_steps = load_csv("approval_steps.csv")
reimbursements = load_csv("reimbursements.csv")

# Run detection
results = engine.run_all_anomaly_detection(
    employees, claims, lines, approval_steps, reimbursements
)

print(results["summary"])
# Output: "Detected 66 runtime anomalies: 20 duplicate receipts, 
#          3 split claims, 40 self-approvals, 3 duplicate reimbursements"

# Inspect details
for dup in results["duplicate_receipts"]:
    print(f"  {dup['description']}")
    print(f"  Claims: {dup['claim_ids']}")
```

**Test it:**
```bash
python test_anomaly_detection.py
```

This demonstrates **runtime anomaly detection** on operational data, not just pre-labeled ground truth.

## 🐛 Injected Anomaly Scenarios

All anomalies are injected by **mutating existing rows** (never appending), so
volumes stay exact.  Each anomaly is recorded in `ground_truth.csv`.

| Scenario | Target | Count | Description |
|----------|--------|-------|-------------|
| `insufficient_balance` | Leave | ~32 | Days requested exceeds remaining balance |
| `overlapping_leave` | Leave | ~24 | Dates overlap with previously approved leave |
| `holiday_span` | Leave | ~24 | Leave spans a public holiday |
| `self_approval` | Leave + Expense | ~36 | Employee is their own approver |
| `missing_receipt` | Expense lines | ~50 | Amount exceeds threshold but has_receipt=False |
| `duplicate_receipt` | Expense lines | ~20 | Same receipt hash on different claims |
| `policy_limit_breach` | Expense lines | ~30 | Amount exceeds single-receipt limit |
| `expense_outside_dates` | Expense | ~20 | Claim date after employee termination |
| `missing_cost_center` | Expense | ~20 | Empty cost_center_id |
| `split_claim` | Expense | ~20 | Duplicate claim splitting amounts |
| `duplicate_reimbursement` | Reimbursement | ~3 | Same claim reimbursed twice |

## 🔑 Zero Ground-Truth Leakage

Operational tables (`employees`, `leave_requests`, `expense_claims`, etc.)
contain **only** business-domain columns.  No `anomaly_flag`, `anomaly_type`,
`policy_violation`, or `remarks` columns exist in any input table.

All anomaly metadata lives exclusively in `ground_truth.csv`:
```
entity_type, entity_id, issue_type, description, expected_decision, expected_reason
```

## 📈 Status Events (Append-Only)

`status_events.csv` records every state transition without overwriting:

```
event_id, entity_type, entity_id, from_status, to_status, event_timestamp, actor_id, reason_code
```

Typical chain: `Draft → Submitted → Under Review → Approved/Rejected`

## 🧪 Validation

**`validate.py`** runs 56 automated checks covering:
- Volume targets • PK uniqueness • FK integrity
- Zero leakage • ID formats • Date ordering
- Lines-per-claim range • Approval sequence correctness
- Reimbursement eligibility • Balance reconciliation
- Status-event chain integrity • Ground-truth coverage

**`tests/test_data.py`** provides 36 pytest tests in 10 test classes.

## Requirements

- Python ≥ 3.9
- NumPy ≥ 1.21
- pytest (for tests only)
- Streamlit (for dashboard)


