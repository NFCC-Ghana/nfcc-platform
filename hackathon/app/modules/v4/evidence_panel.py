"""
Evidence Panel - Visual explainability with confidence bars
"""

import streamlit as st
import pandas as pd
import plotly.express as px

def render_evidence_panel(risk_score: float) -> None:
    """Render evidence and explainability panel."""
    
    st.markdown("### 📊 Evidence & Explainability")
    st.caption("Why this risk assessment was generated")
    
    # Risk drivers with visual bars
    drivers = [
        {"factor": "Rainfall", "contribution": 35, "status": "CRITICAL", "color": "#ff0000"},
        {"factor": "Soil Saturation", "contribution": 25, "status": "CRITICAL", "color": "#ff6600"},
        {"factor": "River Levels", "contribution": 20, "status": "MODERATE", "color": "#ffaa00"},
        {"factor": "Reservoir Risk", "contribution": 10, "status": "HIGH", "color": "#ff6600"},
        {"factor": "Community Reports", "contribution": 10, "status": "ELEVATED", "color": "#ffcc00"}
    ]
    
    # Create DataFrame for visualization
    df = pd.DataFrame(drivers)
    
    # Bar chart
    fig = px.bar(
        df,
        x="factor",
        y="contribution",
        title="Risk Factor Contributions",
        color="contribution",
        color_continuous_scale="RdYlGn_r",
        range_color=[0, 100],
        text=df["contribution"].apply(lambda x: f"{x}%")
    )
    
    fig.update_traces(textposition="outside")
    fig.update_layout(
        height=250,
        showlegend=False,
        xaxis_title="",
        yaxis_title="Contribution (%)",
        yaxis_range=[0, 105]
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Confidence metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Overall Confidence", "92%", delta="High")
    with col2:
        st.metric("Data Sources", "6", delta="Active")
    with col3:
        st.metric("Evidence Quality", "🟢 HIGH")
    
    # Data freshness
    st.markdown("#### 📡 Data Freshness")
    
    sources = [
        {"name": "CHIRPS Rainfall", "status": "🟢", "age": "2 min ago", "confidence": "High"},
        {"name": "NASA SMAP Soil", "status": "🟢", "age": "2 hours ago", "confidence": "High"},
        {"name": "River Gauges", "status": "🟢", "age": "30 min ago", "confidence": "Medium"},
        {"name": "Sentinel-1 SAR", "status": "🟢", "age": "6 hours ago", "confidence": "High"},
        {"name": "Community Reports", "status": "🟢", "age": "10 min ago", "confidence": "Medium"},
        {"name": "Reservoir Telemetry", "status": "🟢", "age": "1 hour ago", "confidence": "High"}
    ]
    
    for src in sources:
        st.markdown(f"""
        <div style="background: #f8f9fa; padding: 0.3rem 1rem; border-radius: 6px; margin-bottom: 0.2rem; display: flex; justify-content: space-between;">
            <span>{src['status']} {src['name']}</span>
            <span style="color: #666; font-size: 0.85rem;">{src['age']} • Confidence: {src['confidence']}</span>
        </div>
        """, unsafe_allow_html=True)
