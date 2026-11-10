# Validation Report

| Check | Status | Detail |
|-------|--------|--------|
| Employee count > 0 | ✅ PASS | 400 rows |
| Leave requests > 0 | ✅ PASS | 812 rows |
| Expense claims > 0 | ✅ PASS | 1020 rows |
| Expense lines > 0 | ✅ PASS | 5627 rows |
| Approval steps > 0 | ✅ PASS | 2110 rows |
| Reimbursements > 0 | ✅ PASS | 653 rows |
| Ground truth > 0 | ✅ PASS | 170 anomalies |
| Negative leave balances injected | ✅ PASS | 40 records |
| All reimbursements linked to approved claims | ✅ PASS | 0 orphan reimbursements |
| Approval steps reference valid IDs | ✅ PASS | 0 orphan step IDs |
| Expense lines reference valid claim IDs | ✅ PASS | 0 orphan line claim IDs |
| Duplicate reimbursements injected | ✅ PASS | 6 records |
| Self-approval anomalies injected | ✅ PASS | 21 records |
| Leave start_date >= submission_date | ✅ PASS | 0 violations |
| All 7 anomaly types present in ground truth | ✅ PASS | Missing: None |
