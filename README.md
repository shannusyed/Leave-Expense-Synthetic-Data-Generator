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
| Comprehensive validation (56 checks) | ✅ |
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

```bash
# Install dependencies
pip install -r requirements.txt

# Generate the dataset
python generate_data.py

# Run validation (56 checks)
python validate.py

# Run tests (36 tests)
python -m pytest tests/ -v

# Verify reproducibility
python scripts/repro_check.py
```

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
