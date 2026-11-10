#!/usr/bin/env python3
"""
test_data.py – pytest test suite for the synthetic dataset.

Run with:  pytest tests/test_data.py -v
"""

import csv
import hashlib
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


# ── Fixtures ────────────────────────────────────────────────────────

def _load(name: str):
    with open(DATA_DIR / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="session", autouse=True)
def generate_data():
    """Run the generator once before all tests."""
    subprocess.run(
        [sys.executable, str(ROOT / "generate_data.py")],
        cwd=str(ROOT), check=True, capture_output=True,
    )


@pytest.fixture(scope="session")
def employees():       return _load("employees.csv")

@pytest.fixture(scope="session")
def leave_requests():  return _load("leave_requests.csv")

@pytest.fixture(scope="session")
def expense_claims():  return _load("expense_claims.csv")

@pytest.fixture(scope="session")
def expense_lines():   return _load("expense_lines.csv")

@pytest.fixture(scope="session")
def leave_balances():  return _load("leave_balances.csv")

@pytest.fixture(scope="session")
def approval_steps():  return _load("approval_steps.csv")

@pytest.fixture(scope="session")
def reimbursements():  return _load("reimbursements.csv")

@pytest.fixture(scope="session")
def ground_truth():    return _load("ground_truth.csv")

@pytest.fixture(scope="session")
def status_events():   return _load("status_events.csv")

@pytest.fixture(scope="session")
def leave_policies():  return _load("leave_policies.csv")

@pytest.fixture(scope="session")
def cost_centers():    return _load("cost_centers.csv")


# ── Volume tests ────────────────────────────────────────────────────

class TestVolumes:
    def test_employees(self, employees):
        assert len(employees) == 400

    def test_leave_policies(self, leave_policies):
        assert len(leave_policies) == 6

    def test_leave_requests(self, leave_requests):
        assert len(leave_requests) == 800

    def test_expense_claims(self, expense_claims):
        assert len(expense_claims) == 1000

    def test_expense_lines_range(self, expense_lines, expense_claims):
        per_claim = Counter(l["claim_id"] for l in expense_lines)
        assert len(per_claim) == len(expense_claims)
        assert all(1 <= v <= 10 for v in per_claim.values())


# ── PK uniqueness tests ────────────────────────────────────────────

class TestPrimaryKeys:
    def test_employee_id(self, employees):
        ids = [e["employee_id"] for e in employees]
        assert len(ids) == len(set(ids))

    def test_leave_request_id(self, leave_requests):
        ids = [r["leave_request_id"] for r in leave_requests]
        assert len(ids) == len(set(ids))

    def test_claim_id(self, expense_claims):
        ids = [c["claim_id"] for c in expense_claims]
        assert len(ids) == len(set(ids))

    def test_expense_line_id(self, expense_lines):
        ids = [l["expense_line_id"] for l in expense_lines]
        assert len(ids) == len(set(ids))

    def test_event_id(self, status_events):
        ids = [e["event_id"] for e in status_events]
        assert len(ids) == len(set(ids))


# ── FK integrity tests ─────────────────────────────────────────────

class TestForeignKeys:
    def test_lr_employee(self, leave_requests, employees):
        eids = {e["employee_id"] for e in employees}
        assert all(r["employee_id"] in eids for r in leave_requests)

    def test_ec_employee(self, expense_claims, employees):
        eids = {e["employee_id"] for e in employees}
        assert all(c["employee_id"] in eids for c in expense_claims)

    def test_el_claim(self, expense_lines, expense_claims):
        cids = {c["claim_id"] for c in expense_claims}
        assert all(l["claim_id"] in cids for l in expense_lines)

    def test_reimb_claim(self, reimbursements, expense_claims):
        cids = {c["claim_id"] for c in expense_claims}
        assert all(r["claim_id"] in cids for r in reimbursements)

    def test_manager_id(self, employees):
        eids = {e["employee_id"] for e in employees}
        assert all(e["manager_id"] in eids for e in employees)


# ── Ground-truth leakage ───────────────────────────────────────────

class TestNoLeakage:
    LEAK_COLS = {"anomaly_flag", "anomaly_type", "policy_violation",
                 "remarks", "is_anomaly", "issue_type", "expected_decision"}

    @pytest.mark.parametrize("filename", [
        "employees.csv", "leave_requests.csv", "expense_claims.csv",
        "expense_lines.csv", "leave_balances.csv", "approval_steps.csv",
        "reimbursements.csv", "status_events.csv",
    ])
    def test_no_leakage(self, filename):
        rows = _load(filename)
        if rows:
            cols = set(rows[0].keys())
            assert not (cols & self.LEAK_COLS), f"Leakage in {filename}"


# ── ID format tests ────────────────────────────────────────────────

class TestIDFormat:
    def test_emp_format(self, employees):
        assert all(re.match(r"^EMP\d{4}$", e["employee_id"]) for e in employees)

    def test_lr_format(self, leave_requests):
        assert all(re.match(r"^LR\d{4}$", r["leave_request_id"]) for r in leave_requests)

    def test_ec_format(self, expense_claims):
        assert all(re.match(r"^EC\d{4}$", c["claim_id"]) for c in expense_claims)

    def test_el_format(self, expense_lines):
        assert all(re.match(r"^EL\d{5}$", l["expense_line_id"]) for l in expense_lines)


# ── Date ordering ──────────────────────────────────────────────────

class TestDates:
    def test_leave_start_before_end(self, leave_requests):
        assert all(r["start_date"] <= r["end_date"] for r in leave_requests)


# ── Approval sequence ──────────────────────────────────────────────

class TestApprovalSequence:
    def test_reject_then_skip(self, approval_steps):
        by_entity = defaultdict(list)
        for s in approval_steps:
            by_entity[s["entity_id"]].append(s)

        for eid, steps in by_entity.items():
            steps.sort(key=lambda x: int(x["step_order"]))
            seen_reject = False
            for s in steps:
                if seen_reject:
                    assert s["status"] == "Skipped", \
                        f"After rejection, step {s['approval_step_id']} should be Skipped"
                if s["status"] == "Rejected":
                    seen_reject = True


# ── Balance reconciliation ─────────────────────────────────────────

class TestBalances:
    def test_opening_formula(self, leave_balances):
        for b in leave_balances:
            assert int(b["opening_balance"]) == int(b["accrued"]) + int(b["carry_forward"])

    def test_remaining_formula(self, leave_balances):
        for b in leave_balances:
            expected = max(0, int(b["opening_balance"]) - int(b["used"]))
            assert int(b["remaining"]) == expected


# ── Ground-truth coverage ──────────────────────────────────────────

class TestGroundTruth:
    REQUIRED = [
        "missing_receipt", "duplicate_receipt", "policy_limit_breach",
        "overlapping_leave", "insufficient_balance", "self_approval",
        "expense_outside_dates", "missing_cost_center", "holiday_span",
        "split_claim", "duplicate_reimbursement",
    ]

    def test_all_types_present(self, ground_truth):
        types = {r["issue_type"] for r in ground_truth}
        for rt in self.REQUIRED:
            assert rt in types, f"Missing ground-truth type: {rt}"

    def test_columns(self, ground_truth):
        expected = {"entity_type", "entity_id", "issue_type",
                    "description", "expected_decision", "expected_reason"}
        actual = set(ground_truth[0].keys())
        assert expected == actual


# ── Reimbursement eligibility ──────────────────────────────────────

class TestReimbursements:
    def test_only_approved_claims(self, reimbursements, expense_claims, ground_truth):
        claim_status = {c["claim_id"]: c["status"] for c in expense_claims}
        dup_reimb_ids = {g["entity_id"] for g in ground_truth
                         if g["issue_type"] == "duplicate_reimbursement"}
        for r in reimbursements:
            if r["reimbursement_id"] not in dup_reimb_ids:
                assert claim_status.get(r["claim_id"]) == "Approved"


# ── Status events ──────────────────────────────────────────────────

class TestStatusEvents:
    def test_chain_starts_with_draft(self, status_events):
        by_entity = defaultdict(list)
        for e in status_events:
            by_entity[e["entity_id"]].append(e)
        for eid, evts in by_entity.items():
            evts.sort(key=lambda x: x["event_timestamp"])
            assert evts[0]["from_status"] == "Draft"
            assert evts[0]["to_status"] == "Submitted"


# ── Reproducibility ────────────────────────────────────────────────

class TestReproducibility:
    def test_deterministic(self):
        """Run generator twice and compare checksums."""
        def run_and_hash():
            subprocess.run(
                [sys.executable, str(ROOT / "generate_data.py")],
                cwd=str(ROOT), check=True, capture_output=True,
            )
            hashes = {}
            for f in sorted(DATA_DIR.glob("*.csv")):
                hashes[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
            return hashes

        h1 = run_and_hash()
        h2 = run_and_hash()
        assert h1 == h2, "Generation is not reproducible!"

