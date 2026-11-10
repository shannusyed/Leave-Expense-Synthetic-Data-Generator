import pandas as pd

emp  = pd.read_csv('data/employees.csv')
lve  = pd.read_csv('data/leave_requests.csv')
exp  = pd.read_csv('data/expense_claims.csv')
expl = pd.read_csv('data/expense_lines.csv')
apr  = pd.read_csv('data/approval_steps.csv')
rmb  = pd.read_csv('data/reimbursements.csv')
cc   = pd.read_csv('data/cost_centers.csv')
gt   = pd.read_csv('data/ground_truth.csv')
lb   = pd.read_csv('data/leave_balances.csv')

print("=== ID Format Spot-Checks ===")
print("Employee IDs sample     :", emp['employee_id'].head(3).tolist())
print("Leave Request IDs sample:", lve['request_id'].head(3).tolist())
print("Expense Claim IDs sample:", exp['claim_id'].head(3).tolist())
print("Expense Line IDs sample :", expl['line_id'].head(3).tolist())
print("Approval Step IDs sample:", apr['step_id'].head(3).tolist())
print("Reimbursement IDs sample:", rmb['reimbursement_id'].head(3).tolist())
print("Cost Center IDs sample  :", cc['cost_center_id'].head(3).tolist())

print("\n=== Anomaly Types in Ground Truth ===")
print(gt['anomaly_type'].value_counts().to_string())

print("\n=== Expense Claim Status Distribution ===")
print(exp['status'].value_counts().to_string())

print("\n=== Reimbursements only for Approved claims ===")
clean_rmb = rmb[rmb['anomaly_flag'] == False]
rmb_cids  = set(clean_rmb['claim_id'])
approved  = set(exp[exp['status'] == 'Approved']['claim_id'])
bad       = rmb_cids - approved
print("Non-approved claim reimbursements (should be 0):", len(bad))

print("\n=== Negative Leave Balances ===")
neg = lb[lb['balance_days'] < 0]
print("Records with balance < 0:", len(neg))
print("Min balance             :", lb['balance_days'].min())

print("\n=== Leave Request date sanity ===")
lve['start_date']      = pd.to_datetime(lve['start_date'])
lve['submission_date'] = pd.to_datetime(lve['submission_date'])
bad_dates = (lve['start_date'] < lve['submission_date']).sum()
print("start_date < submission_date violations:", bad_dates)

print("\n=== Missing cost centers ===")
missing_cc = exp['cost_center_id'].isna().sum()
print("Claims with NULL cost_center_id:", missing_cc)

print("\nAll checks complete.")

