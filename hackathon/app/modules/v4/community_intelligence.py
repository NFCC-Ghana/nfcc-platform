"""Community Intelligence module."""

import streamlit as st


def render_community_intelligence(state):
    """Render the community intelligence section."""
    st.markdown("## 📢 Community Intelligence")
    st.caption("Real-time citizen reports and AI-verified insights")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Report Trend", "📈 Increasing Reports")
        st.metric("Most Affected", "Alajo")
    with col2:
        st.metric("Total Reports", f"{state.total_reports}", "+2 in last hour")
        st.metric("Verified", f"{state.verified_reports}", "50%")
    with col3:
        st.metric("Avg Depth", f"{state.avg_flood_depth:.2f}m", "Real-time")
        st.metric("Communities", f"{state.communities_reporting}")
    
    st.markdown("### 📋 Recent Reports")
    
    reports = [
        {"community": "Circle", "time": "30m ago", "status": "⏳ Pending", 
         "description": "Water levels rising rapidly near Circle Interchange.",
         "depth": "0.00m", "confidence": "72%"},
        {"community": "Alajo", "time": "45m ago", "status": "✅ Verified",
         "description": "Heavy flooding on Alajo Main Street. Cars cannot pass.",
         "depth": "0.35m", "confidence": "92%"},
        {"community": "Nima", "time": "1h ago", "status": "✅ Verified",
         "description": "Nima Main Street flooded after heavy rain.",
         "depth": "0.25m", "confidence": "88%"},
        {"community": "Kaneshie", "time": "2h ago", "status": "⏳ Pending",
         "description": "Water level rising on Kaneshie Market road.",
         "depth": "0.15m", "confidence": "78%"},
    ]
    
    for report in reports:
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{report['community']}** • {report['time']}")
                st.markdown(f"{report['status']} {report['description']}")
            with col2:
                st.caption(f"💧 {report['depth']}")
                st.caption(f"🎯 {report['confidence']} confidence")
            st.divider()
