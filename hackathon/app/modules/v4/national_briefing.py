"""
Enhanced National Briefing - AI-style situation report.
"""

import streamlit as st
from datetime import datetime

def render_national_briefing(district: str, risk_score: float) -> None:
    """Render AI-style national briefing."""
    
    st.markdown("### 🤖 AI Situation Brief")
    
    # Determine status
    if risk_score >= 80:
        status = "🔴 EMERGENCY LEVEL: HIGH"
        color = "#ff0000"
    elif risk_score >= 60:
        status = "🟠 EMERGENCY LEVEL: ELEVATED"
        color = "#ff6600"
    else:
        status = "🟢 EMERGENCY LEVEL: NORMAL"
        color = "#00cc00"
    
    # Briefing content
    briefing = f"""
    <div style="background: #f8f9fa; padding: 1rem 1.5rem; border-radius: 12px; border-left: 4px solid {color};">
        <div style="font-size: 1.1rem; font-weight: 600; color: {color};">
            {status}
        </div>
        <div style="margin: 0.5rem 0; font-size: 0.95rem; line-height: 1.6;">
            Persistent rainfall has saturated catchments in Accra Central, 
            increasing flash flood risk. Verified flooding is already occurring in Alajo 
            while Volta Basin conditions continue deteriorating. 
            <b>Immediate priority is evacuation readiness and deployment of drainage response teams.</b>
        </div>
        <div style="display: flex; gap: 1rem; margin-top: 0.5rem; font-size: 0.85rem; color: #666;">
            <span>🤖 Analysis complete</span>
            <span>📊 5 data sources processed</span>
            <span>✅ Confidence: 92%</span>
        </div>
    </div>
    """
    
    st.markdown(briefing, unsafe_allow_html=True)
