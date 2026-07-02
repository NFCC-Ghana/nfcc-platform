"""Community Intelligence - Trend analysis and reports."""

import streamlit as st

def render_community_intelligence() -> None:
    """Render community intelligence panel."""
    
    st.markdown("### 📢 Community Intelligence")
    
    # Trend indicator
    st.markdown("""
    <div style="background: rgba(255, 255, 255, 0.04); padding: 0.8rem 1rem; border-radius: 8px; border-left: 4px solid #ff6600;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <div style="color: #8ecae6; font-size: 0.7rem;">Trend</div>
                <div style="color: #ffffff; font-weight: 600;">📈 Flood reports increasing</div>
            </div>
            <div style="text-align: right;">
                <div style="color: #8ecae6; font-size: 0.7rem;">Most affected</div>
                <div style="color: #ffffff; font-weight: 600;">Alajo</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Report stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Reports", "4", delta="+2")
    with col2:
        st.metric("Verified", "2", delta="100%")
    with col3:
        st.metric("Avg Depth", "0.3m", delta="+0.1m")
    
    # Report list
    reports = [
        {"community": "Alajo", "type": "Active Flooding", "time": "14:49", "status": "verified"},
        {"community": "Kaneshie", "type": "Water Level Rising", "time": "12:49", "status": "pending"},
        {"community": "Dansoman", "type": "Drainage Blocked", "time": "10:49", "status": "verified"},
        {"community": "Circle", "type": "Flood Warning", "time": "15:49", "status": "pending"}
    ]
    
    for report in reports[:2]:
        status_color = "#00cc00" if report["status"] == "verified" else "#ffaa00"
        status_text = "✅ Verified" if report["status"] == "verified" else "⏳ Pending"
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.03); padding: 0.5rem 0.8rem; border-radius: 6px; margin-bottom: 0.3rem; border-left: 3px solid {status_color};">
            <div style="display: flex; justify-content: space-between;">
                <span style="color: #ffffff; font-weight: 500;">{report['community']}</span>
                <span style="color: rgba(255,255,255,0.4); font-size: 0.7rem;">{report['time']}</span>
            </div>
            <div style="color: rgba(255,255,255,0.6); font-size: 0.8rem;">{report['type']}</div>
            <div style="color: {status_color}; font-size: 0.65rem;">{status_text}</div>
        </div>
        """, unsafe_allow_html=True)
    
    if st.button("📝 Submit Report", use_container_width=True):
        st.success("✅ Report submission form opened")
