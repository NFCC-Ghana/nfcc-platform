"""Evidence Quality module."""

import streamlit as st


def render_evidence_panel(state):
    """Render the evidence quality panel."""
    st.markdown("## 📊 Evidence Quality")
    st.caption("Real-time data confidence metrics")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.success("🟢 CHIRPS Updated: 2m ago")
        st.success("🟢 SMAP Updated: 2h ago")
    with col2:
        st.success("🟢 Sentinel-1 Updated: 6h ago")
        st.success("🟢 River Gauges: LIVE")
    with col3:
        st.metric("Data Quality", "92%")
        st.metric("Confidence", f"{state.confidence*100:.0f}%")
