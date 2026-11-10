# Data Dictionary

> Auto-generated schema reference for the Leave & Expense Synthetic Dataset.
> All dates are ISO-8601 (`YYYY-MM-DD`). Monetary amounts are in USD unless noted.

---

## employees.csv

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `employee_id` | string | No | Primary key. Format: `EMP-NNNNNN` |
| `full_name` | string | No | First + Last name |
| `email` | string | No | Corporate email address |
| `department` | string | No | Business department |
| `job_grade` | string | No | Grade level: L1–L6 (L1=junior, L6=executive) |
| `annual_salary` | float | No | Annual gross salary (USD) |
| `employment_type` | string | No | Full-Time / Part-Time / Contract |
| `hire_date` | date | No | Date employee joined the company |
| `termination_date` | date | Yes | Date of departure; NULL if still active |
| `manager_id` | string | Yes | FK → `employees.employee_id`. NULL for top-level executives |
| `location` | string | No | Work location city |
| `is_active` | boolean | No | True if `termination_date` is NULL |

---

## leave_policies.csv

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `policy_id` | string | No | PK. Format: `LP-NNN` |
| `policy_name` | string | No | Human-readable policy name |
| `leave_type` | string | No | Annual / Sick / Maternity / Paternity / Unpaid |
| `accrual_days_per_year` | int | No | Days accrued per calendar year |
| `max_carry_forward_days` | int | No | Maximum days that roll into the next year |
| `max_consecutive_days` | int | No | Maximum contiguous days per request |
| `notice_period_days` | int | No | Minimum days' notice before leave start |
| `applicable_grades` | string | No | Pipe-delimited list of eligible grades (e.g., `L1|L2|L3`) |
| `requires_approval` | boolean | No | Whether the request must go through approval workflow |

---

## leave_balances.csv

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `employee_id` | string | No | FK → `employees.employee_id` |
| `policy_id` | string | No | FK → `leave_policies.policy_id` |
| `leave_type` | string | No | Denormalised leave type for convenience |
| `accrued_days` | float | No | Days accrued pro-rata to `as_of_date` |
| `carry_forward_days` | float | No | Days carried over from prior year |
| `total_available` | float | No | `accrued_days + carry_forward_days` |
| `days_taken` | float | No | Days consumed as of `as_of_date` |
| `balance_days` | float | No | `total_available − days_taken` (can be negative — anomaly) |
| `as_of_date` | date | No | Snapshot date for balance calculation |
| `anomaly_flag` | boolean | No | True if this record was anomaly-injected |

---

## leave_requests.csv

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `request_id` | string | No | PK. Format: `LVE-YYYY-NNNNNN` |
| `employee_id` | string | No | FK → `employees.employee_id` |
| `policy_id` | string | No | FK → `leave_policies.policy_id` |
| `leave_type` | string | No | Denormalised leave type |
| `start_date` | date | No | First day of leave |
| `end_date` | date | No | Last day of leave |
| `days_requested` | int | No | Business (weekday) days requested |
| `submission_date` | date | No | Date request was submitted |
| `status` | string | No | Approved / Rejected / Pending / Cancelled |
| `policy_violation` | boolean | No | True if request exceeds available balance or policy limit |
| `remarks` | string | Yes | Free-text reason (e.g., "Insufficient balance") |
| `anomaly_flag` | boolean | No | True if anomaly-injected |
| `anomaly_type` | string | Yes | Anomaly label (e.g., `OverlappingLeave`) |

---

## expense_policies.csv

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `policy_id` | string | No | PK. Format: `EP-NNN` |
| `policy_name` | string | No | Human-readable policy name |
| `expense_category` | string | No | Travel / Meals / Office / Training |
| `per_diem_limit` | float | No | Maximum daily allowance (0 = not applicable) |
| `single_receipt_limit` | float | No | Maximum amount per individual receipt |
| `monthly_claim_limit` | float | No | Total cap per employee per month |
| `requires_receipt_above` | float | No | Receipt mandatory when line amount exceeds this |
| `approval_threshold_l1` | float | No | Manager approval required above this amount |
| `approval_threshold_l2` | float | No | Director approval required above this amount |
| `approval_threshold_l3` | float | No | CFO approval required above this amount |
| `reimbursable` | boolean | No | Whether the category is eligible for reimbursement |

---

## expense_claims.csv

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `claim_id` | string | No | PK. Format: `EXP-YYYY-NNNNNN` |
| `employee_id` | string | No | FK → `employees.employee_id` |
| `cost_center_id` | string | Yes | FK → `cost_centers.cost_center_id`. NULL = anomaly |
| `policy_id` | string | No | FK → `expense_policies.policy_id` (dominant category) |
| `submission_date` | date | No | Date the claim was submitted |
| `total_amount` | float | No | Sum of all expense line amounts |
| `currency` | string | No | Currency code (always `USD` in this dataset) |
| `num_lines` | int | No | Number of expense lines in the claim |
| `status` | string | No | Pending / Approved / Rejected |
| `purpose` | string | No | Business purpose description |
| `anomaly_flag` | boolean | No | True if anomaly-injected |
| `anomaly_type` | string | Yes | Pipe-delimited anomaly labels |

---

## expense_lines.csv

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `line_id` | string | No | PK. Format: `EXPL-<claim_id>-NN` |
| `claim_id` | string | No | FK → `expense_claims.claim_id` |
| `expense_date` | date | No | Date the expense was incurred |
| `expense_category` | string | No | Category of spend |
| `policy_id` | string | No | FK → `expense_policies.policy_id` |
| `description` | string | No | Itemised description |
| `amount` | float | No | Line amount (USD) |
| `currency` | string | No | Currency code |
| `has_receipt` | boolean | No | True if receipt is attached (derived from policy threshold) |
| `is_billable` | boolean | No | True if cost can be billed to a client |
| `anomaly_flag` | boolean | No | True if anomaly-injected |
| `anomaly_type` | string | Yes | Anomaly label |

---

## cost_centers.csv

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `cost_center_id` | string | No | PK. Format: `CC-NNNN` |
| `cost_center_name` | string | No | Descriptive name |
| `department` | string | No | Owning department |
| `annual_budget` | float | No | Total annual budget (USD) |
| `budget_spent` | float | No | Amount spent to date |
| `budget_remaining` | float | No | `annual_budget − budget_spent` |
| `is_active` | boolean | No | Whether the cost center is currently active |

---

## approval_rules.csv

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `rule_id` | string | No | PK. Format: `AR-NNN` |
| `rule_name` | string | No | Human-readable rule name |
| `entity_type` | string | No | `Leave` or `Expense` |
| `condition` | string | No | `always` / `days_gt` / `amount_gt` |
| `threshold` | float | No | Trigger threshold (days or USD amount) |
| `approver_role` | string | No | Manager / Director / CFO / HR / Finance |
| `level` | int | No | Approval chain sequence (1 = first) |
| `sla_hours` | int | No | Expected turnaround time in hours |
| `is_active` | boolean | No | Whether the rule is currently enforced |

---

## approval_steps.csv

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `step_id` | string | No | PK. Format: `APR-<request_id>-NN` |
| `request_id` | string | No | FK → `leave_requests.request_id` or `expense_claims.claim_id` |
| `entity_type` | string | No | `Leave` or `Expense` |
| `rule_id` | string | No | FK → `approval_rules.rule_id` |
| `level` | int | No | Approval level (matches `approval_rules.level`) |
| `approver_id` | string | No | FK → `employees.employee_id` |
| `approver_role` | string | No | Role of the approver |
| `assigned_date` | date | No | Date step was assigned |
| `sla_due_date` | date | No | Deadline for decision |
| `decision_date` | date | Yes | Actual decision date; NULL if Pending |
| `status` | string | No | Approved / Rejected / Pending |
| `comments` | string | Yes | Approver notes |
| `anomaly_flag` | boolean | No | True if anomaly-injected |
| `anomaly_type` | string | Yes | Anomaly label (e.g., `SelfApproval`) |

---

## reimbursements.csv

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `reimbursement_id` | string | No | PK. Format: `RMB-YYYY-NNNNNN` |
| `claim_id` | string | No | FK → `expense_claims.claim_id` |
| `employee_id` | string | No | FK → `employees.employee_id` |
| `claim_amount` | float | No | Original claim total |
| `deduction_amount` | float | No | Amount deducted (non-reimbursable portion) |
| `net_reimbursed` | float | No | `claim_amount − deduction_amount` |
| `currency` | string | No | Currency code |
| `payment_date` | date | No | Date payment was processed |
| `payment_method` | string | No | Bank Transfer / Company Card Credit / Cheque |
| `bank_reference` | string | No | Unique payment reference |
| `status` | string | No | Paid / Cancelled |
| `anomaly_flag` | boolean | No | True if anomaly-injected |
| `anomaly_type` | string | Yes | Anomaly label (e.g., `DuplicateReimbursement`) |

---

## ground_truth.csv

> This file is for **audit and ML evaluation only**. It lists every injected anomaly with full lineage. Do not use as a training label source without splitting train/test first.

| Column | Type | Description |
|--------|------|-------------|
| `anomaly_id` | string | Unique anomaly record ID |
| `anomaly_type` | string | Canonical anomaly type name |
| `entity` | string | Table name the anomaly lives in |
| `entity_id` | string | Primary key of the affected record |
| `description` | string | Human-readable explanation of the injected anomaly |
| `injected_at` | string | CSV file name where anomaly was written |

### Anomaly Type Reference

| Anomaly Type | Description |
|--------------|-------------|
| `NegativeLeaveBalance` | Employee's days taken exceed total available |
| `OverlappingLeave` | Two approved leave requests for same employee overlap in dates |
| `ExpenseDateOutsideEmployment` | Expense line date is before the employee's hire date |
| `SplitClaimThresholdEvasion` | Claim split into smaller amounts to avoid a higher approval level |
| `MissingCostCenter` | Expense claim submitted without a valid cost center assignment |
| `SelfApproval` | The approver on a step is the same person as the requester |
| `DuplicateReimbursement` | Same approved claim reimbursed more than once |

