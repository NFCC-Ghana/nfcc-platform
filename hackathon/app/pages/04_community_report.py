"""Community Flood Report Submission."""

import streamlit as st
import requests
from datetime import datetime
import json
import pandas as pd

st.set_page_config(
    page_title="Report Flood - CivicFlood AI", page_icon="📢", layout="wide"
)

# Custom CSS for professional look
st.markdown(
    """
<style>
    .report-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .report-header h1 {
        color: white;
        margin: 0;
    }
    .report-header p {
        color: #a8d8ea;
        margin: 0.5rem 0 0 0;
    }
    .submission-success {
        background: #00ff87;
        background: linear-gradient(135deg, #00ff87 0%, #60efff 100%);
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border: 2px solid #00d4ff;
    }
    .submission-success h3 {
        color: #1a1a2e;
        margin: 0;
    }
    .submission-success p {
        color: #1a1a2e;
        margin: 0.5rem 0 0 0;
    }
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }
    .stat-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        text-align: center;
    }
    .stat-card .number {
        font-size: 2rem;
        font-weight: bold;
        color: #0f3460;
    }
    .stat-card .label {
        color: #666;
        font-size: 0.9rem;
    }
    .report-list {
        max-height: 400px;
        overflow-y: auto;
    }
    .report-item {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        border-left: 4px solid #0f3460;
    }
    .report-item .community {
        font-weight: bold;
        color: #0f3460;
    }
    .report-item .timestamp {
        color: #888;
        font-size: 0.8rem;
    }
    .report-item .status {
        display: inline-block;
        padding: 0.2rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
    }
    .status-verified {
        background: #00ff87;
        color: #1a1a2e;
    }
    .status-pending {
        background: #ffd93d;
        color: #1a1a2e;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Sample community reports data
SAMPLE_REPORTS = [
    {
        "community": "Alajo",
        "district": "Accra Central",
        "report_type": "Active Flooding",
        "flood_depth": 35,
        "description": "Heavy flooding on Alajo Main Street. Cars cannot pass.",
        "timestamp": "2026-06-17 08:30",
        "status": "Verified",
    },
    {
        "community": "Kaneshie",
        "district": "Accra Central",
        "report_type": "Water Level Rising",
        "flood_depth": 15,
        "description": "Water level rising on Kaneshie Market road.",
        "timestamp": "2026-06-17 07:15",
        "status": "Pending",
    },
    {
        "community": "Dansoman",
        "district": "Accra West",
        "report_type": "Drainage Blocked",
        "flood_depth": 0,
        "description": "Drainage blocked at Dansoman Roundabout. Needs clearing.",
        "timestamp": "2026-06-16 22:00",
        "status": "Verified",
    },
]


def main():
    # Header
    st.markdown(
        """
    <div class="report-header">
        <h1>📢 Community Flood Reporting</h1>
        <p>Your reports help protect your community and improve flood predictions</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Reports", "47")
    with col2:
        st.metric("Verified", "32")
    with col3:
        st.metric("Pending", "15")
    with col4:
        st.metric("Communities", "12")

    st.divider()

    # Two-column layout
    col_submit, col_reports = st.columns([1, 1])

    with col_submit:
        st.markdown("### 📝 Submit a Report")

        with st.form("flood_report", clear_on_submit=True):
            col_form1, col_form2 = st.columns(2)

            with col_form1:
                district = st.selectbox(
                    "📍 District",
                    [
                        "Accra Central",
                        "Accra West",
                        "Accra East",
                        "Tema",
                        "Kumasi",
                        "Tamale",
                    ],
                    index=0,
                )
                community = st.text_input(
                    "🏘️ Community Name", placeholder="e.g., Alajo"
                )

            with col_form2:
                report_type = st.selectbox(
                    "📋 Report Type",
                    [
                        "Active Flooding",
                        "Water Level Rising",
                        "Recent Flood",
                        "Drainage Blocked",
                        "Weather Warning",
                    ],
                    index=0,
                )
                flood_depth = st.slider(
                    "🌊 Estimated Flood Depth (cm)",
                    min_value=0,
                    max_value=200,
                    value=20,
                )

            description = st.text_area(
                "📝 Description",
                placeholder="Describe what you're seeing...",
                height=100,
            )

            col_contact, col_photo = st.columns(2)
            with col_contact:
                contact = st.text_input(
                    "📱 Phone Number (optional)",
                    placeholder="For verification if needed",
                )
            with col_photo:
                photo = st.file_uploader(
                    "📸 Upload Photo (optional)",
                    type=["jpg", "jpeg", "png"],
                    accept_multiple_files=False,
                )

            submitted = st.form_submit_button(
                "🚨 Submit Report", use_container_width=True
            )

            if submitted:
                if not community:
                    st.error("⚠️ Please enter a community name")
                else:
                    st.markdown(
                        """
                    <div class="submission-success">
                        <h3>✅ Report Submitted!</h3>
                        <p>Thank you for helping protect your community. Your report will be verified and shared with NADMO.</p>
                        <p><strong>Report ID:</strong> FLD-"""
                        + datetime.now().strftime("%Y%m%d-%H%M%S")
                        + """</p>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

    with col_reports:
        st.markdown("### 📋 Recent Community Reports")

        for report in SAMPLE_REPORTS:
            status_class = (
                "status-verified"
                if report["status"] == "Verified"
                else "status-pending"
            )
            depth_text = (
                f"Depth: {report['flood_depth']}cm"
                if report["flood_depth"] > 0
                else "No flooding"
            )

            st.markdown(
                f"""
            <div class="report-item">
                <div class="community">📍 {report['community']}</div>
                <div>{report['report_type']} • {depth_text}</div>
                <div style="font-size:0.9rem;color:#555;">{report['description'][:80]}...</div>
                <div style="display:flex;justify-content:space-between;margin-top:0.5rem;">
                    <span class="timestamp">🕐 {report['timestamp']}</span>
                    <span class="status {status_class}">{report['status']}</span>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

    st.divider()

    st.markdown(
        """
    <div style="text-align:center;padding:1rem;color:#888;font-size:0.9rem;">
        🛡️ Reports are verified by CivicFlood AI and shared with NADMO for emergency response
    </div>
    """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
