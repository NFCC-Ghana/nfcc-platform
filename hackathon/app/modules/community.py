"""Community Reports Module - Citizen intelligence."""

import streamlit as st
from datetime import datetime, timedelta

def render_community_reports(district: str) -> None:
    st.caption("📝 Demo reports for demonstration purposes")
    """Render community reports panel."""
    
    st.markdown("### 📢 Community Reports")
    
    # Simulated reports (in production: from community_memory.py)
    reports = [
        {
            "community": "Alajo",
            "type": "Active Flooding",
            "description": "Heavy flooding on Alajo Main Street. Cars cannot pass.",
            "time": datetime.now() - timedelta(hours=2),
            "verified": True,
            "depth": 0.35
        },
        {
            "community": "Kaneshie",
            "type": "Water Level Rising",
            "description": "Water level rising on Kaneshie Market road.",
            "time": datetime.now() - timedelta(hours=4),
            "verified": False,
            "depth": 0.15
        },
        {
            "community": "Dansoman",
            "type": "Drainage Blocked",
            "description": "Drainage blocked at Dansoman Roundabout. Needs clearing.",
            "time": datetime.now() - timedelta(hours=6),
            "verified": True,
            "depth": 0.0
        },
        {
            "community": "Circle",
            "type": "Flood Warning",
            "description": "Water levels rising rapidly near Circle Interchange.",
            "time": datetime.now() - timedelta(hours=1),
            "verified": False,
            "depth": 0.0
        }
    ]
    
    # Display reports
    for report in reports[:5]:
        status_color = "🟢" if report['verified'] else "🟡"
        status_text = "Verified" if report['verified'] else "Pending"
        
        depth_text = f"Depth: {report['depth']}m" if report['depth'] > 0 else "No water reported"
        
        st.markdown(f"""
        <div style="background: {'#e8f5e9' if report['verified'] else '#fff3e0'}; padding: 0.8rem; border-radius: 8px; margin-bottom: 0.5rem; border-left: 4px solid {'#4caf50' if report['verified'] else '#ff9800'};">
            <b>{report['community']}</b> <span style="font-size: 0.8rem; color: #666;">{report['time'].strftime('%H:%M')}</span><br>
            <b>{report['type']}</b><br>
            {report['description']}<br>
            <span style="font-size: 0.8rem;">{status_color} {status_text} • {depth_text}</span>
        </div>
        """, unsafe_allow_html=True)
    
    # Report submission
    with st.expander("📝 Submit a Report"):
        with st.form("community_report"):
            st.text_input("Your Name (optional)")
            st.text_area("Describe what you're seeing")
            st.selectbox("Report Type", ["Flooding", "Water Level Rising", "Drainage Blocked", "Weather Warning"])
            st.slider("Estimated Flood Depth (cm)", 0, 200, 20)
            st.file_uploader("Upload Photo (optional)", type=["jpg", "png"])
            
            if st.form_submit_button("Submit Report"):
                st.success("✅ Report submitted! Thank you for helping your community.")
