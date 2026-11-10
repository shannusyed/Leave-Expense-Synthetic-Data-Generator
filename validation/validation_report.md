# Validation Report

**Generated:** 2025-11-10  
**Generator seed:** 20261022  
**Tool:** `validate.py` (56 automated checks)

---

## Summary

| Category | Passed | Failed | Total |
|----------|--------|--------|-------|
| Volume checks | 4 | 0 | 4 |
| PK uniqueness | 9 | 0 | 9 |
| FK integrity | 12 | 0 | 12 |
| Ground-truth leakage | 8 | 0 | 8 |
| ID format | 4 | 0 | 4 |
| Date ordering | 2 | 0 | 2 |
| Lines per claim | 1 | 0 | 1 |
| Approval sequence | 1 | 0 | 1 |
| Reimbursement eligibility | 1 | 0 | 1 |
| Balance reconciliation | 2 | 0 | 2 |
| Status events | 1 | 0 | 1 |
| Ground-truth coverage | 11 | 0 | 11 |
| **Total** | **56** | **0** | **56** |

## Detailed Results

### Volume Checks
- ✅ 400 employees
- ✅ 6 leave policies
- ✅ 800 leave requests
- ✅ 1000 expense claims

### Primary Key Uniqueness
- ✅ employee_id unique
- ✅ cost_center_id unique
- ✅ leave_request_id unique
- ✅ claim_id unique
- ✅ expense_line_id unique
- ✅ approval_step_id unique
- ✅ reimbursement_id unique
- ✅ event_id unique
- ✅ balance_id unique

### Foreign Key Integrity
- ✅ employee.cost_center → cost_centers
- ✅ employee.manager_id → employees
- ✅ leave_request.employee_id → employees
- ✅ leave_balance.employee_id → employees
- ✅ expense_claim.employee_id → employees
- ✅ expense_claim.cost_center → cost_centers
- ✅ expense_line.claim_id → expense_claims
- ✅ approval_step leave → leave_requests
- ✅ approval_step expense → expense_claims
- ✅ reimbursement.claim_id → expense_claims
- ✅ status_event leave → leave_requests
- ✅ status_event expense → expense_claims

### Ground-Truth Leakage
- ✅ employees: no leakage
- ✅ leave_requests: no leakage
- ✅ expense_claims: no leakage
- ✅ expense_lines: no leakage
- ✅ leave_balances: no leakage
- ✅ approval_steps: no leakage
- ✅ reimbursements: no leakage
- ✅ status_events: no leakage

### Ground-Truth Anomaly Coverage
All 11 required anomaly types are present:

| Anomaly Type | Count |
|-------------|-------|
| missing_receipt | 50 |
| self_approval | 36 |
| insufficient_balance | 32 |
| policy_limit_breach | 30 |
| overlapping_leave | 24 |
| holiday_span | 24 |
| missing_cost_center | 20 |
| duplicate_receipt | 20 |
| expense_outside_dates | 20 |
| split_claim | 20 |
| duplicate_reimbursement | 3 |

### Reproducibility
Two consecutive runs produced identical SHA-256 checksums across all 13 CSV files.

---

## pytest Results

```
36 passed in 2.82s
```

All tests pass across 10 test classes:
TestVolumes, TestPrimaryKeys, TestForeignKeys, TestNoLeakage,
TestIDFormat, TestDates, TestApprovalSequence, TestBalances,
TestGroundTruth, TestReimbursements, TestStatusEvents,
TestReproducibility
