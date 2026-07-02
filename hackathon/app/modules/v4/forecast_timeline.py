"""
Forecast Timeline - Visual risk evolution.
"""

import streamlit as st
import plotly.graph_objects as go

def render_forecast_timeline() -> None:
    """Render forecast timeline with visual bars."""
    
    st.markdown("### ⏰ Risk Timeline")
    st.caption("24-hour flood risk evolution")
    
    # Timeline data
    time_points = ["00h", "+6h", "+12h", "+18h", "+24h"]
    risks = [88, 100, 95, 72, 45]
    
    # Color mapping
    colors = ["#ff0000" if r >= 80 else "#ff6600" if r >= 60 else "#ffaa00" if r >= 40 else "#00cc00" for r in risks]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=time_points,
        y=risks,
        marker_color=colors,
        text=[f"{r}%" for r in risks],
        textposition="outside",
        name="Risk Level"
    ))
    
    fig.update_layout(
        height=250,
        yaxis_title="Risk (%)",
        yaxis_range=[0, 105],
        xaxis_title="",
        showlegend=False,
        margin=dict(l=10, r=10, t=20, b=20)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Peak warning
    st.warning("⚠️ **Peak Risk:** 100% expected in 6 hours")
