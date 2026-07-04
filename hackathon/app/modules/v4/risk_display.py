"""
Risk Display Module - Full Implementation
Displays risk score with gauge, category, and breakdown.
"""

import streamlit as st
import plotly.graph_objects as go


def render_risk_display(state):
    """Render the complete risk display section."""
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        # Risk Gauge
        st.markdown(f"## {state.risk_emoji} Risk Score")
        
        # Create gauge chart
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=state.risk_score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Flood Risk"},
            delta={'reference': 50, 'increasing': {'color': "#ff0000"}},
            gauge={
                'axis': {'range': [0, 100], 'tickwidth': 1},
                'bar': {'color': state.risk_color},
                'steps': [
                    {'range': [0, 40], 'color': "#00cc00"},
                    {'range': [40, 60], 'color': "#ffaa00"},
                    {'range': [60, 80], 'color': "#ff6600"},
                    {'range': [80, 100], 'color': "#ff0000"}
                ],
                'threshold': {
                    'line': {'color': "black", 'width': 4},
                    'thickness': 0.75,
                    'value': state.risk_score
                }
            }
        ))
        
        fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown(f"**Category:** {state.risk_category}")
        st.caption(f"Confidence: {state.confidence*100:.0f}%")
    
    with col2:
        # Risk Breakdown
        st.markdown("### 📊 Risk Breakdown")
        
        factors = {
            "Rainfall": min(100, state.rainfall_mm * 1.2),
            "River Level": min(100, (state.river_level_m / 5) * 100),
            "Soil Saturation": state.soil_saturation,
            "Historical Risk": 20 if state.past_events > 0 else 10,
            "Dam Risk": 30 if state.dam_risk == "HIGH" else 15 if state.dam_risk == "MEDIUM" else 5
        }
        
        for name, value in factors.items():
            color = "🔴" if value > 70 else "🟠" if value > 50 else "🟡" if value > 30 else "🟢"
            st.progress(value/100, text=f"{color} {name}: {value:.0f}%")
    
    with col3:
        # Quick Stats
        st.markdown("### 📈 Quick Stats")
        
        st.metric(
            "Population at Risk",
            f"{state.population_exposed:,}",
            delta=f"{state.exposure_percentage:.1f}%"
        )
        
        st.metric(
            "Affected Communities",
            state.communities_affected,
            delta="at risk"
        )
        
        st.metric(
            "Lead Time",
            f"{state.lead_time_hours}h",
            delta=state.lead_time_action
        )
        
        st.caption("🔄 Updates every 15 minutes")

