"""
Visual Evidence Panel - Confidence gauges and data quality.
"""

import streamlit as st
import plotly.graph_objects as go

def render_evidence_panel() -> None:
    """Render visual evidence panel with gauges."""
    
    st.markdown("### 📊 Evidence Quality")
    st.caption("Real-time data confidence metrics")
    
    # Create gauge charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Confidence gauge
        fig1 = go.Figure(go.Indicator(
            mode="gauge+number",
            value=92,
            title={"text": "Confidence"},
            domain={"x": [0, 1], "y": [0, 1]},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#00cc00"},
                "steps": [
                    {"range": [0, 60], "color": "#ff0000"},
                    {"range": [60, 80], "color": "#ffaa00"},
                    {"range": [80, 100], "color": "#00cc00"}
                ]
            }
        ))
        fig1.update_layout(height=150, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # Freshness gauge
        fig2 = go.Figure(go.Indicator(
            mode="gauge+number",
            value=84,
            title={"text": "Freshness"},
            domain={"x": [0, 1], "y": [0, 1]},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#00cc00"},
                "steps": [
                    {"range": [0, 40], "color": "#ff0000"},
                    {"range": [40, 70], "color": "#ffaa00"},
                    {"range": [70, 100], "color": "#00cc00"}
                ]
            }
        ))
        fig2.update_layout(height=150, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig2, use_container_width=True)
    
    # Data sources status
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("🟢 **CHIRPS**\nUpdated: 2m ago")
    with col2:
        st.markdown("🟢 **SMAP**\nUpdated: 2h ago")
    with col3:
        st.markdown("🟢 **Sentinel-1**\nUpdated: 6h ago")
