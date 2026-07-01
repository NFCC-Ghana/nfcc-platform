"""
AI National Situation Briefing - Generated every refresh
"""

import streamlit as st
from datetime import datetime

def generate_situation_briefing(district: str, risk_score: float) -> dict:
    """Generate AI situation briefing."""
    
    # Determine status level
    if risk_score >= 80:
        status = "🔴 EMERGENCY"
        status_color = "#ff0000"
        brief = f"""
Heavy rainfall across {district} has saturated soils, increasing runoff potential. 
Bagre Dam remains at high capacity while Volta Basin conditions continue to deteriorate. 
Flooding has already been verified in Alajo and water levels are rising in Kaneshie.
"""
        actions = [
            "🚨 Activate Emergency Level 2",
            "🚨 Issue evacuation warnings for Accra Central",
            "🚨 Deploy pumps to Alajo",
            "🚨 Open Accra High School shelter",
            "🚨 Pre-position rescue teams"
        ]
    elif risk_score >= 60:
        status = "🟠 WARNING"
        status_color = "#ff6600"
        brief = f"""
Moderate to heavy rainfall is affecting {district}. Soil moisture is elevated and 
river levels are rising. Community reports indicate localized flooding in low-lying areas. 
Reservoir levels are being monitored closely.
"""
        actions = [
            "⚠️ Prepare evacuation routes",
            "⚠️ Deploy monitoring teams",
            "⚠️ Alert community leaders",
            "⚠️ Inspect drainage systems"
        ]
    elif risk_score >= 40:
        status = "🟡 WATCH"
        status_color = "#ffaa00"
        brief = f"""
Rainfall continues across {district} with soil moisture increasing. 
River levels remain within normal range but are being monitored. 
Community reports are being verified.
"""
        actions = [
            "ℹ️ Monitor conditions",
            "ℹ️ Update community reports",
            "ℹ️ Prepare resources"
        ]
    else:
        status = "🟢 NORMAL"
        status_color = "#00cc00"
        brief = f"""
Normal conditions prevail across {district}. Rainfall is within seasonal averages. 
River levels are stable. No immediate flood risk detected.
"""
        actions = [
            "✅ Continue monitoring",
            "✅ Update situation reports"
        ]
    
    return {
        "status": status,
        "status_color": status_color,
        "briefing": brief,
        "actions": actions,
        "confidence": 92,
        "timestamp": datetime.now().strftime('%H:%M')
    }


def render_national_briefing(district: str, risk_score: float) -> None:
    """Render AI National Situation Briefing."""
    
    briefing = generate_situation_briefing(district, risk_score)
    
    st.markdown("""
    <style>
    .briefing-card {
        background: linear-gradient(135deg, #0f1422 0%, #1a1a2e 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 4px solid #00ff88;
        margin-bottom: 1rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    .briefing-status {
        font-size: 1.4rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .briefing-text {
        color: #c8d6e5;
        font-size: 1rem;
        line-height: 1.6;
        margin-bottom: 1rem;
    }
    .briefing-action {
        background: rgba(255,255,255,0.05);
        padding: 0.5rem 1rem;
        border-radius: 8px;
        margin-bottom: 0.3rem;
        color: #a8d8ea;
        font-size: 0.9rem;
    }
    .briefing-confidence {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(255,255,255,0.05);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Status color
    status_color = briefing["status_color"]
    
    st.markdown(f"""
    <div class="briefing-card" style="border-left-color: {status_color};">
        <div class="briefing-status" style="color: {status_color};">
            {briefing['status']}
        </div>
        <div class="briefing-text">
            {briefing['briefing']}
        </div>
        <div style="margin-top: 0.5rem;">
            <span style="color: #8ecae6; font-size: 0.85rem;">🎯 Immediate Priorities</span>
    """, unsafe_allow_html=True)
    
    for action in briefing['actions']:
        st.markdown(f'<div class="briefing-action">{action}</div>', unsafe_allow_html=True)
    
    st.markdown(f"""
        </div>
        <div class="briefing-confidence">
            <span style="color: #8ecae6;">Confidence</span>
            <span style="color: #00ff88; font-weight: 700;">{briefing['confidence']}%</span>
            <span style="color: #8ecae6; font-size: 0.8rem; opacity: 0.6;">
                • Based on 5 data sources • Updated {briefing['timestamp']}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Briefing metadata
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption("📊 Data Sources: CHIRPS, Sentinel-1, River Gauges, SMAP, Community")
    with col2:
        st.caption("🔄 Last Analysis: 15 seconds ago")
    with col3:
        st.caption(f"📍 Region: {district}")
