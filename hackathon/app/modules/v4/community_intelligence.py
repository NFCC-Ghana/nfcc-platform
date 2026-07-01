"""
Community Intelligence - AI-summarized reports with verification
"""

import streamlit as st
from datetime import datetime, timedelta

def render_community_intelligence() -> None:
    """Render AI-summarized community intelligence panel."""
    
    st.markdown("### 📢 Community Intelligence")
    st.caption("AI-summarized reports with verification status")
    
    # AI Summary
    st.markdown("""
    <div style="background: #f0f4f8; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; border-left: 4px solid #0f3460;">
        <b>🤖 AI Summary</b><br>
        <span style="color: #333;">
            42 reports received • 38 verified • Flood depth increasing in Alajo (0.35m)
            • Most urgent: Blocked drainage at Dansoman Roundabout
            • Confidence: 89%
        </span>
    </div>
    """, unsafe_allow_html=True)
    
    # Reports
    reports = [
        {
            "community": "Alajo",
            "type": "Active Flooding",
            "time": "12:30",
            "verified": True,
            "depth": "0.35m",
            "summary": "Heavy flooding on Main Street. Cars cannot pass."
        },
        {
            "community": "Kaneshie",
            "type": "Water Level Rising",
            "time": "10:30",
            "verified": False,
            "depth": "0.15m",
            "summary": "Water level rising on Market road."
        },
        {
            "community": "Dansoman",
            "type": "Drainage Blocked",
            "time": "08:30",
            "verified": True,
            "depth": "0m",
            "summary": "Drainage blocked at Roundabout. Needs clearing."
        },
        {
            "community": "Circle",
            "type": "Flood Warning",
            "time": "13:30",
            "verified": False,
            "depth": "0m",
            "summary": "Water levels rising rapidly near Interchange."
        }
    ]
    
    # Display reports
    for report in reports:
        status = "🟢 Verified" if report["verified"] else "🟡 Pending"
        depth_text = f"Depth: {report['depth']}" if report['depth'] != "0m" else "No water reported"
        
        st.markdown(f"""
        <div style="background: {'#e8f5e9' if report['verified'] else '#fff3e0'}; 
                    padding: 0.6rem 1rem; 
                    border-radius: 8px; 
                    margin-bottom: 0.4rem; 
                    border-left: 4px solid {'#4caf50' if report['verified'] else '#ff9800'};">
            <div style="display: flex; justify-content: space-between;">
                <b>{report['community']}</b>
                <span style="font-size: 0.8rem; color: #666;">{report['time']} • {status}</span>
            </div>
            <div style="font-size: 0.9rem;">{report['summary']}</div>
            <div style="font-size: 0.8rem; color: #666;">{depth_text}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Hotspots
    st.markdown("#### 🔥 Report Hotspots")
    
    hotspots = [
        {"area": "Alajo", "reports": "12", "trend": "🔴 Increasing"},
        {"area": "Kaneshie", "reports": "8", "trend": "🟠 Rising"},
        {"area": "Dansoman", "reports": "5", "trend": "🟢 Stable"}
    ]
    
    for hotspot in hotspots:
        st.markdown(f"""
        <div style="background: #f8f9fa; padding: 0.3rem 1rem; border-radius: 6px; margin-bottom: 0.2rem;">
            <b>{hotspot['area']}</b>
            <span style="float: right;">{hotspot['reports']} reports • {hotspot['trend']}</span>
        </div>
        """, unsafe_allow_html=True)
