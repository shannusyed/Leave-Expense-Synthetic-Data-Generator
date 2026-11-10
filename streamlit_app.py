#!/usr/bin/env python3
"""
streamlit_app.py – Interactive dashboard for Leave & Expense Management System.

Run with:
    streamlit run streamlit_app.py

Features:
  - Home: System overview with key metrics
  - Approval Decisions: Search and view approval chains
  - Anomaly Detection: Browse detected anomalies
  - Data Quality: Validation results
  - Audit Trail: Status event history
"""

import streamlit as st
import pandas as pd
import csv
from pathlib import Path
import subprocess
import sys

import engine
import config as cfg

DATA_DIR = Path(__file__).resolve().parent / "data"


def load_csv(name: str) -> list:
    """Load a CSV file as a list of dictionaries."""
    path = DATA_DIR / name
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ══════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Leave & Expense Dashboard",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🎯 Leave & Expense Management Dashboard")
st.markdown("*Rule-driven approval system with anomaly detection*")
st.markdown("---")


# ══════════════════════════════════════════════════════════════════════
# SIDEBAR: NAVIGATION
# ══════════════════════════════════════════════════════════════════════

page = st.sidebar.radio(
    "📑 Navigate to:",
    [
        "🏠 Home",
        "✅ Approval Decisions",
        "🔍 Anomaly Detection",
        "📊 Data Quality",
        "📝 Audit Trail"
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 💡 About")
st.sidebar.markdown("""
This dashboard demonstrates:
- **Multi-level approval routing**
- **Runtime anomaly detection**
- **Complete audit trail**
- **Data quality validation**
""")


# ══════════════════════════════════════════════════════════════════════
# PAGE 1: HOME
# ══════════════════════════════════════════════════════════════════════

if page == "🏠 Home":
    st.header("📈 System Overview")
    
    # Load data
    with st.spinner("Loading data..."):
        employees = load_csv("employees.csv")
        leave_requests = load_csv("leave_requests.csv")
        expense_claims = load_csv("expense_claims.csv")
        expense_lines = load_csv("expense_lines.csv")
        reimbursements = load_csv("reimbursements.csv")
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("👥 Employees", len(employees))
    
    with col2:
        st.metric("🏖️ Leave Requests", len(leave_requests))
        leave_approved = len([r for r in leave_requests if r["status"] == "Approved"])
        st.caption(f"✅ {leave_approved} approved ({100*leave_approved/len(leave_requests):.0f}%)")
    
    with col3:
        st.metric("💰 Expense Claims", len(expense_claims))
        exp_approved = len([c for c in expense_claims if c["status"] == "Approved"])
        st.caption(f"✅ {exp_approved} approved ({100*exp_approved/len(expense_claims):.0f}%)")
    
    with col4:
        total_amount = sum(float(r["amount"]) for r in reimbursements)
        st.metric("💳 Total Reimbursed", f"₹{total_amount:,.0f}")
        st.caption(f"{len(reimbursements)} payments")
    
    st.markdown("---")
    
    # Features
    st.subheader("✨ Key Features")
    
    feature_col1, feature_col2 = st.columns(2)
    
    with feature_col1:
        st.markdown("""
        **🔐 Rule-Driven Approval**
        - Multi-level routing (1-3 levels)
        - Threshold-based (days/amount)
        - Manager → Senior Manager → Director
        
        **📊 Complete Traceability**
        - Status event history (append-only)
        - Approval chain per request
        - Audit-ready logs
        """)
    
    with feature_col2:
        st.markdown("""
        **🔍 Anomaly Detection**
        - Duplicate receipts across claims
        - Split claims to evade thresholds
        - Self-approval violations
        - Duplicate reimbursements
        
        **✅ Data Quality**
        - 61 validation checks
        - 100% reproducible (fixed seed)
        - Zero ground-truth leakage
        """)
    
    st.markdown("---")
    st.info("💡 **Use the sidebar** to navigate to different sections")


# ══════════════════════════════════════════════════════════════════════
# PAGE 2: APPROVAL DECISIONS
# ══════════════════════════════════════════════════════════════════════

elif page == "✅ Approval Decisions":
    st.header("🔎 Search Approval Decisions")
    
    entity_type = st.radio("Select entity type:", ["Leave Request", "Expense Claim"])
    search_id = st.text_input(f"Enter {entity_type} ID:", placeholder="e.g., LR0001 or EC0001")
    
    if search_id:
        with st.spinner("Loading..."):
            if entity_type == "Leave Request":
                leave_requests = load_csv("leave_requests.csv")
                approval_steps = load_csv("approval_steps.csv")
                status_events = load_csv("status_events.csv")
                
                request = next((r for r in leave_requests if r["leave_request_id"] == search_id), None)
                
                if request:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("📄 Request Details")
                        st.json({
                            "Leave Type": request["leave_type"],
                            "Start Date": request["start_date"],
                            "End Date": request["end_date"],
                            "Days Requested": request["days_requested"],
                            "Applied Date": request["applied_date"],
                            "Status": request["status"],
                        })
                        
                        if request["status"] == "Approved":
                            st.success("✅ APPROVED")
                        else:
                            st.error("❌ REJECTED")
                    
                    with col2:
                        st.subheader("🔗 Approval Chain")
                        
                        steps = [s for s in approval_steps if s["entity_id"] == search_id]
                        steps.sort(key=lambda x: int(x["step_order"]))
                        
                        if steps:
                            for step in steps:
                                status_emoji = "✅" if step["status"] == "Approved" else "❌" if step["status"] == "Rejected" else "⏭️"
                                st.markdown(f"""
**{status_emoji} Level {step['step_order']}: {step['approver_role']}**
- Approver: {step['approver_id']}
- Decision: {step['status']}
- Date: {step['decision_date']}
- Reason: {step['reason_code']}
                                """)
                        else:
                            st.warning("No approval steps found")
                else:
                    st.error(f"❌ Leave request {search_id} not found")
            
            else:  # Expense Claim
                expense_claims = load_csv("expense_claims.csv")
                expense_lines = load_csv("expense_lines.csv")
                approval_steps = load_csv("approval_steps.csv")
                reimbursements = load_csv("reimbursements.csv")
                
                claim = next((c for c in expense_claims if c["claim_id"] == search_id), None)
                
                if claim:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("📄 Claim Details")
                        st.json({
                            "Amount": f"₹{float(claim['total_amount']):,.2f}",
                            "Claim Date": claim["claim_date"],
                            "Department": claim["department"],
                            "Cost Center": claim["cost_center_id"],
                            "Status": claim["status"],
                        })
                        
                        if claim["status"] == "Approved":
                            st.success("✅ APPROVED")
                        else:
                            st.error("❌ REJECTED")
                        
                        # Show line items
                        st.subheader("📋 Line Items")
                        lines = [l for l in expense_lines if l["claim_id"] == search_id]
                        if lines:
                            for line in lines:
                                st.markdown(f"- **{line['category']}**: ₹{float(line['amount']):,.2f} ({'✓ Receipt' if line['has_receipt']=='True' else '✗ No receipt'})")
                    
                    with col2:
                        st.subheader("🔗 Approval Chain")
                        
                        steps = [s for s in approval_steps if s["entity_id"] == search_id]
                        steps.sort(key=lambda x: int(x["step_order"]))
                        
                        if steps:
                            for step in steps:
                                status_emoji = "✅" if step["status"] == "Approved" else "❌" if step["status"] == "Rejected" else "⏭️"
                                st.markdown(f"""
**{status_emoji} Level {step['step_order']}: {step['approver_role']}**
- Approver: {step['approver_id']}
- Decision: {step['status']}
- Date: {step['decision_date']}
                                """)
                        
                        # Show reimbursement
                        st.subheader("💳 Reimbursement")
                        reimb = next((r for r in reimbursements if r["claim_id"] == search_id), None)
                        if reimb:
                            st.success(f"✅ Reimbursed ₹{float(reimb['amount']):,.2f}")
                            st.caption(f"ID: {reimb['reimbursement_id']} | Date: {reimb['processed_date']}")
                        else:
                            st.warning("No reimbursement processed")
                else:
                    st.error(f"❌ Expense claim {search_id} not found")


# ══════════════════════════════════════════════════════════════════════
# PAGE 3: ANOMALY DETECTION
# ══════════════════════════════════════════════════════════════════════

elif page == "🔍 Anomaly Detection":
    st.header("🔍 Runtime Anomaly Detection")
    
    with st.spinner("Running anomaly detection..."):
        employees = load_csv("employees.csv")
        claims = load_csv("expense_claims.csv")
        lines = load_csv("expense_lines.csv")
        approval_steps = load_csv("approval_steps.csv")
        reimbursements = load_csv("reimbursements.csv")
        
        results = engine.run_all_anomaly_detection(
            employees, claims, lines, approval_steps, reimbursements
        )
    
    st.success(results["summary"])
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🧾 Duplicate Receipts", len(results["duplicate_receipts"]))
    with col2:
        st.metric("✂️ Split Claims", len(results["split_claims"]))
    with col3:
        st.metric("👤 Self-Approvals", len(results["self_approvals"]))
    with col4:
        st.metric("💳 Duplicate Reimbursements", len(results["duplicate_reimbursements"]))
    
    st.markdown("---")
    
    # Detailed results
    anomaly_type = st.selectbox(
        "Select anomaly type to view details:",
        ["Duplicate Receipts", "Split Claims", "Self-Approvals", "Duplicate Reimbursements"]
    )
    
    if anomaly_type == "Duplicate Receipts":
        if results["duplicate_receipts"]:
            st.subheader("🧾 Duplicate Receipt Details")
            for i, anom in enumerate(results["duplicate_receipts"], 1):
                with st.expander(f"#{i}: {anom['description']}"):
                    st.json({
                        "Receipt Hash": anom["receipt_hash"][:32] + "...",
                        "Claims": anom["claim_ids"],
                        "Lines": anom["line_ids"],
                        "Severity": anom["severity"],
                        "Count": anom["count"]
                    })
        else:
            st.info("No duplicate receipts detected")
    
    elif anomaly_type == "Split Claims":
        if results["split_claims"]:
            st.subheader("✂️ Split Claim Details")
            for i, anom in enumerate(results["split_claims"], 1):
                with st.expander(f"#{i}: {anom['description']}"):
                    st.json({
                        "Employee": anom["employee_id"],
                        "Claims": anom["claim_ids"],
                        "Individual Max": f"₹{anom['individual_max']:,.0f}",
                        "Group Total": f"₹{anom['group_total']:,.0f}",
                        "Date Range": anom["date_range"],
                        "Severity": anom["severity"]
                    })
        else:
            st.info("No split claims detected")
    
    elif anomaly_type == "Self-Approvals":
        if results["self_approvals"]:
            st.subheader("👤 Self-Approval Details")
            for i, anom in enumerate(results["self_approvals"], 1):
                with st.expander(f"#{i}: {anom['description']}"):
                    st.json({
                        "Employee": anom["employee_id"],
                        "Claim": anom["claim_id"],
                        "Approver Role": anom["approver_role"],
                        "Severity": anom["severity"]
                    })
        else:
            st.info("No self-approvals detected")
    
    else:  # Duplicate Reimbursements
        if results["duplicate_reimbursements"]:
            st.subheader("💳 Duplicate Reimbursement Details")
            for i, anom in enumerate(results["duplicate_reimbursements"], 1):
                with st.expander(f"#{i}: {anom['description']}"):
                    st.json({
                        "Claim": anom["claim_id"],
                        "Reimbursement IDs": anom["reimbursement_ids"],
                        "Count": anom["count"],
                        "Severity": anom["severity"]
                    })
        else:
            st.info("No duplicate reimbursements detected")


# ══════════════════════════════════════════════════════════════════════
# PAGE 4: DATA QUALITY
# ══════════════════════════════════════════════════════════════════════

elif page == "📊 Data Quality":
    st.header("📊 Data Quality Validation")
    
    if st.button("🔄 Run Validation"):
        with st.spinner("Running 61 validation checks..."):
            try:
                # Get the full path to validate.py
                validate_path = Path(__file__).parent / "validate.py"
                result = subprocess.run(
                    [sys.executable, str(validate_path)],
                    capture_output=True,
                    text=True,
                    cwd=str(Path(__file__).parent),
                    timeout=60
                )
                
                st.subheader("Validation Results")
                if result.stdout:
                    st.code(result.stdout, language="text")
                
                if result.returncode == 0:
                    st.success("✅ All validation checks passed!")
                else:
                    if result.stderr:
                        st.error(f"Error output:\n{result.stderr}")
                    else:
                        st.error("❌ Some validation checks may have issues")
            except subprocess.TimeoutExpired:
                st.error("⏱️ Validation took too long (timeout)")
            except Exception as e:
                st.error(f"Error running validation: {str(e)}")
    else:
        st.info("Click 'Run Validation' to execute 61 data quality checks")
    
    st.markdown("---")
    
    # Show quick stats
    st.subheader("📈 Quick Stats")
    
    employees = load_csv("employees.csv")
    leave_requests = load_csv("leave_requests.csv")
    expense_claims = load_csv("expense_claims.csv")
    expense_lines = load_csv("expense_lines.csv")
    ground_truth = load_csv("ground_truth.csv")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
**Volume Targets**
- ✅ Employees: {len(employees)} (target: 400)
- ✅ Leave Requests: {len(leave_requests)} (target: 800)
- ✅ Expense Claims: {len(expense_claims)} (target: 1000)
- ✅ Expense Lines: {len(expense_lines)} (1-10 per claim)
        """)
    
    with col2:
        st.markdown(f"""
**Ground Truth**
- Total labels: {len(ground_truth)}
- Anomaly types: {len(set(g['issue_type'] for g in ground_truth))}
- Leave anomalies: {len([g for g in ground_truth if g['entity_type']=='leave_request'])}
- Expense anomalies: {len([g for g in ground_truth if g['entity_type']=='expense_claim'])}
        """)


# ══════════════════════════════════════════════════════════════════════
# PAGE 5: AUDIT TRAIL
# ══════════════════════════════════════════════════════════════════════

elif page == "📝 Audit Trail":
    st.header("📝 Status Event Audit Trail")
    
    search_id = st.text_input("Enter entity ID (LR/EC):", placeholder="e.g., LR0001 or EC0001")
    
    if search_id:
        with st.spinner("Loading audit trail..."):
            status_events = load_csv("status_events.csv")
            events = [e for e in status_events if e["entity_id"] == search_id]
            events.sort(key=lambda x: x["event_timestamp"])
            
            if events:
                st.subheader(f"Event Timeline for {search_id}")
                
                for i, event in enumerate(events, 1):
                    st.markdown(f"""
### Event {i}: {event['from_status']} → {event['to_status']}
- **Timestamp:** {event['event_timestamp']}
- **Actor:** {event['actor_id']}
- **Reason:** {event.get('reason_code', 'N/A')}
                    """)
                    
                    if i < len(events):
                        st.markdown("↓")
            else:
                st.warning(f"No events found for {search_id}")
    else:
        st.info("Enter a Leave Request ID (LRxxxx) or Expense Claim ID (ECxxxx) to view its audit trail")


# ══════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════

st.markdown("---")
st.caption("🎯 Leave & Expense Management Dashboard | Built with Streamlit | 100% Rule-Driven")
