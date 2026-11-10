# Leave & Expense Synthetic Data Generator

## Overview
A production-ready, self-contained Python project that generates **fully linked, validated, and reproducible** synthetic data for end-to-end HR Leave and Finance Expense workflows. Seed-fixed generation ensures bit-exact reproducibility.

## Project Structure
```
leave_expense_synthetic/
├── generate_data.py        # Main generator (CLI entry point)
├── config.py               # All tuneable parameters
├── requirements.txt
├── schema/
│   └── data_dictionary.md  # Field-level schema documentation
├── data/                   # Generated CSV output
│   ├── employees.csv
│   ├── leave_policies.csv
│   ├── leave_balances.csv
│   ├── leave_requests.csv
│   ├── expense_policies.csv
│   ├── expense_claims.csv
│   ├── expense_lines.csv
│   ├── cost_centers.csv
│   ├── approval_rules.csv
│   ├── approval_steps.csv
│   ├── reimbursements.csv
│   └── ground_truth.csv    # Anomaly labels (audit use only)
└── validation/
    └── validation_report.md
```

## Quick Start

### Install dependencies
```bash
pip install -r requirements.txt
```

### Generate full dataset (400 employees, 1 000 expense claims)
```bash
python generate_data.py --scale full --seed 20261022
```

### Generate small dataset (50 employees, 150 expense claims)
```bash
python generate_data.py --scale small --seed 20261022
```

### Custom output directory
```bash
python generate_data.py --scale full --seed 20261022 --out-dir /path/to/output
```

## Scale Presets

| Parameter | `full` | `small` |
|-----------|--------|---------|
| Employees | 400 | 50 |
| Leave Policies | 6 | 6 |
| Expense Policies | 4 | 4 |
| Cost Centers | 20 | 10 |
| Leave Requests | 800 | 100 |
| Expense Claims | 1 000 | 150 |
| Lines per Claim | 1–10 | 1–5 |

## Entity Relationship

```
Employee ──┬── LeaveBalance (via LeavePolicy)
           │
           ├── LeaveRequest ──── ApprovalStep (Leave)
           │
           └── ExpenseClaim ──┬── ExpenseLine
                              │
                              ├── ApprovalStep (Expense)
                              │
                              └── Reimbursement (if Approved)
```

## ID Conventions

| Entity | Format | Example |
|--------|--------|---------|
| Employee | `EMP-NNNNNN` | `EMP-000001` |
| Leave Request | `LVE-YYYY-NNNNNN` | `LVE-2026-000001` |
| Expense Claim | `EXP-YYYY-NNNNNN` | `EXP-2026-000001` |
| Expense Line | `EXPL-<claim_id>-NN` | `EXPL-EXP-2026-000001-01` |
| Approval Step | `APR-<request_id>-NN` | `APR-LVE-2026-000001-01` |
| Reimbursement | `RMB-YYYY-NNNNNN` | `RMB-2026-000001` |
| Cost Center | `CC-NNNN` | `CC-0001` |
| Leave Policy | `LP-NNN` | `LP-001` |
| Expense Policy | `EP-NNN` | `EP-001` |
| Approval Rule | `AR-NNN` | `AR-001` |

## Business Rules Enforced

1. **Leave Balance**: accrued + carry_forward − days_taken (never random)
2. **Leave Request**: respects policy notice period, max consecutive days, and available balance
3. **Expense Routing**: multi-level approval triggered by amount vs. policy thresholds (L1/L2/L3/L4)
4. **Reimbursements**: only created for fully approved claims; payment date is after final approval date
5. **Date Consistency**: hire → submission → leave start/end; hire → expense date → claim submission

## Injected Anomalies (Ground Truth)

| # | Anomaly Type | Dataset Column | Description |
|---|--------------|----------------|-------------|
| 1 | `NegativeLeaveBalance` | `leave_balances.anomaly_flag` | days_taken > total_available |
| 2 | `OverlappingLeave` | `leave_requests.anomaly_flag` | Same employee, overlapping approved dates |
| 3 | `ExpenseDateOutsideEmployment` | `expense_lines.anomaly_flag` | Expense date before hire date |
| 4 | `SplitClaimThresholdEvasion` | `expense_claims.anomaly_flag` | Claim cloned to stay below L2 threshold |
| 5 | `MissingCostCenter` | `expense_claims.anomaly_flag` | cost_center_id set to NULL |
| 6 | `SelfApproval` | `approval_steps.anomaly_flag` | approver_id == requester's employee_id |
| 7 | `DuplicateReimbursement` | `reimbursements.anomaly_flag` | Same claim reimbursed twice |

> **Note**: `anomaly_flag = True` and `anomaly_type` are present in each table to support row-level filtering. The consolidated `ground_truth.csv` has full lineage for ML/audit use.

## Reproducibility

All random operations use `numpy.random.default_rng(seed)`. Given the same `--seed`, output is **bit-exact** across runs and platforms (Python 3.10+, numpy ≥ 1.26).

## Technical Stack

- **Python** 3.10+
- **pandas** ≥ 2.0
- **numpy** ≥ 1.26
- No external data sources; fully self-contained.

