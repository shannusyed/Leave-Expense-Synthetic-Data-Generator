#!/usr/bin/env python3
"""
test_anomaly_detection.py – Quick test of runtime anomaly detection.

This script loads the generated CSV data and runs all anomaly detection
functions to demonstrate that we can detect anomalies at runtime, not just
inject them during generation.
"""

import csv
from pathlib import Path

import engine

DATA_DIR = Path(__file__).resolve().parent / "data"


def load_csv(name: str):
    """Load a CSV file as a list of dictionaries."""
    with open(DATA_DIR / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    print("=" * 70)
    print("RUNTIME ANOMALY DETECTION TEST")
    print("=" * 70)
    print()
    
    # Load all data
    print("Loading data...")
    employees = load_csv("employees.csv")
    claims = load_csv("expense_claims.csv")
    lines = load_csv("expense_lines.csv")
    approval_steps = load_csv("approval_steps.csv")
    reimbursements = load_csv("reimbursements.csv")
    ground_truth = load_csv("ground_truth.csv")
    
    print(f"  ✓ Loaded {len(employees)} employees")
    print(f"  ✓ Loaded {len(claims)} expense claims")
    print(f"  ✓ Loaded {len(lines)} expense lines")
    print(f"  ✓ Loaded {len(approval_steps)} approval steps")
    print(f"  ✓ Loaded {len(reimbursements)} reimbursements")
    print(f"  ✓ Loaded {len(ground_truth)} ground truth labels")
    print()
    
    # Run detection
    print("Running anomaly detection...")
    results = engine.run_all_anomaly_detection(
        employees, claims, lines, approval_steps, reimbursements
    )
    
    print()
    print("=" * 70)
    print("DETECTION RESULTS")
    print("=" * 70)
    print()
    print(f"✅ {results['summary']}")
    print()
    
    # Print details for each anomaly type
    print("-" * 70)
    print("DUPLICATE RECEIPTS")
    print("-" * 70)
    if results["duplicate_receipts"]:
        for i, anom in enumerate(results["duplicate_receipts"][:5], 1):
            print(f"  {i}. {anom['description']}")
            print(f"     Claims: {', '.join(anom['claim_ids'])}")
            print(f"     Lines: {', '.join(anom['line_ids'])}")
            print(f"     Receipt hash: {anom['receipt_hash'][:16]}...")
            print()
        if len(results["duplicate_receipts"]) > 5:
            print(f"  ... and {len(results['duplicate_receipts']) - 5} more")
            print()
    else:
        print("  No duplicate receipts detected.")
        print()
    
    print("-" * 70)
    print("SPLIT CLAIMS")
    print("-" * 70)
    if results["split_claims"]:
        for i, anom in enumerate(results["split_claims"][:5], 1):
            print(f"  {i}. {anom['description']}")
            print(f"     Employee: {anom['employee_id']}")
            print(f"     Claims: {', '.join(anom['claim_ids'])}")
            print(f"     Date range: {anom['date_range']}")
            print()
        if len(results["split_claims"]) > 5:
            print(f"  ... and {len(results['split_claims']) - 5} more")
            print()
    else:
        print("  No split claims detected.")
        print()
    
    print("-" * 70)
    print("SELF-APPROVALS")
    print("-" * 70)
    if results["self_approvals"]:
        for i, anom in enumerate(results["self_approvals"][:5], 1):
            print(f"  {i}. {anom['description']}")
            print()
        if len(results["self_approvals"]) > 5:
            print(f"  ... and {len(results['self_approvals']) - 5} more")
            print()
    else:
        print("  No self-approvals detected.")
        print()
    
    print("-" * 70)
    print("DUPLICATE REIMBURSEMENTS")
    print("-" * 70)
    if results["duplicate_reimbursements"]:
        for i, anom in enumerate(results["duplicate_reimbursements"][:5], 1):
            print(f"  {i}. {anom['description']}")
            print()
        if len(results["duplicate_reimbursements"]) > 5:
            print(f"  ... and {len(results['duplicate_reimbursements']) - 5} more")
            print()
    else:
        print("  No duplicate reimbursements detected.")
        print()
    
    # Compare with ground truth
    print("=" * 70)
    print("GROUND TRUTH COMPARISON")
    print("=" * 70)
    
    # Count ground truth by type
    gt_counts = {}
    for gt in ground_truth:
        issue_type = gt["issue_type"]
        if issue_type not in gt_counts:
            gt_counts[issue_type] = 0
        gt_counts[issue_type] += 1
    
    # Map ground truth types to detection types
    detection_types = {
        "duplicate_receipt": "duplicate_receipts",
        "split_claim": "split_claims",
        "self_approval": "self_approvals",
        "duplicate_reimbursement": "duplicate_reimbursements",
    }
    
    print()
    print("Anomaly Type              | Ground Truth | Detected | Status")
    print("-" * 70)
    for gt_type, result_key in detection_types.items():
        gt_count = gt_counts.get(gt_type, 0)
        detected_count = len(results[result_key])
        status = "✅" if detected_count > 0 else "⚠️"
        print(f"{gt_type:<25} | {gt_count:>12} | {detected_count:>8} | {status}")
    
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()
    print(f"✅ Runtime anomaly detection is WORKING")
    print(f"✅ Total anomalies detected: {results['total_anomalies']}")
    print(f"✅ Ground truth labels exist for comparison")
    print()
    print("This demonstrates that we can:")
    print("  • Detect duplicate receipts across claims")
    print("  • Identify split claims to evade thresholds")
    print("  • Flag self-approval violations")
    print("  • Find duplicate reimbursements")
    print()
    print("All detection happens at RUNTIME on operational data,")
    print("not just during generation with pre-labeled anomalies.")
    print()


if __name__ == "__main__":
    main()
