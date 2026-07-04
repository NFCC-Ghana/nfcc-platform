"""
Dashboard Header Module - Full Implementation
Displays system status, version, and key metrics.
"""

import streamlit as st
from datetime import datetime


def render_header(state):
    """Render the complete dashboard header."""
    
    # Main header row
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown("""
        # 🌊 CivicFlood AI
        *National Emergency Operations Center*
        """)
        st.caption("🇬🇭 Ghana AI Innovation Challenge 2026 • Public Services AI")
    
    with col2:
        status_color = "🟢" if state.api_connected else "🔴"
        status_text = "SYSTEM ACTIVE" if state.api_connected else "API DISCONNECTED"
        st.markdown(f"{status_color} **{status_text}**")
        st.caption(f"🕐 {datetime.now().strftime('%d %b %Y, %H:%M UTC')}")
    
    with col3:
        st.markdown(f"**v{state.version}**")
        st.caption(f"📊 {state.active_sources_count} Data Sources Active")
    
    # Quick metrics bar
    st.divider()
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Risk Score",
            f"{state.risk_score:.1f}%",
            delta=state.risk_category,
            delta_color="inverse" if state.risk_score > 60 else "normal"
        )
    
    with col2:
        st.metric("Districts Monitored", state.districts_count)
    
    with col3:
        st.metric("Active Alerts", state.active_alerts)
    
    with col4:
        st.metric("Community Reports", state.total_reports)
    
    with col5:
        st.metric("Data Confidence", f"{state.confidence*100:.0f}%")
    
    st.divider()
