"""
CivicFlood AI - National Emergency Operations Center
CANONICAL DASHBOARD - Single source of truth
"""

import streamlit as st
import requests
from datetime import datetime
import sys
from pathlib import Path
import os

# ============================================================
# PATH SETUP
# ============================================================
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# ============================================================
# PROFESSIONAL CSS - SINGLE DEFINITION
# ============================================================
st.markdown("""
<style>
    .main { background: #0a0e1a; padding: 0; }
    .eoc-header {
        background: linear-gradient(135deg, rgba(26, 26, 46, 0.95) 0%, rgba(22, 30, 62, 0.95) 50%, rgba(15, 52, 96, 0.95) 100%);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,0.08);
        padding: 1.2rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    }
    .eoc-header .title { color: #ffffff; font-size: 1.6rem; font-weight: 700; margin: 0; }
    .eoc-header .subtitle { color: #8ecae6; font-size: 0.85rem; letter-spacing: 1px; margin: 0; }
    .eoc-header .badge {
        background: rgba(0, 255, 135, 0.15);
        color: #00ff87;
        padding: 0.2rem 1rem;
        border-radius: 20px;
        font-size: 0.7rem;
        font-weight: 600;
        border: 1px solid rgba(0, 255, 135, 0.2);
    }
    .eoc-header .timestamp { color: #8ecae6; font-size: 0.7rem; opacity: 0.7; }
    .glass-card {
        background: rgba(255, 255, 255, 0.04);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        padding: 1.2rem;
        transition: all 0.3s ease;
    }
    .glass-card:hover { border-color: rgba(255, 255, 255, 0.12); box-shadow: 0 4px 24px rgba(0,0,0,0.3); }
    .glass-card .label { color: #8ecae6; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600; }
    .glass-card .value { color: #ffffff; font-size: 2rem; font-weight: 700; margin: 0.2rem 0; }
    .glass-card .delta { color: rgba(255,255,255,0.5); font-size: 0.8rem; }
    .metric-critical { border-left: 4px solid #ff0000; background: rgba(255, 0, 0, 0.08); }
    .metric-high { border-left: 4px solid #ff6600; background: rgba(255, 102, 0, 0.08); }
    .metric-moderate { border-left: 4px solid #ffaa00; background: rgba(255, 170, 0, 0.08); }
    .metric-low { border-left: 4px solid #00cc00; background: rgba(0, 204, 0, 0.08); }
    .status-active {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #00ff87;
        animation: pulse 2s infinite;
    }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }
    .divider { border: none; height: 1px; background: linear-gradient(to right, transparent, rgba(255,255,255,0.1), transparent); margin: 1.5rem 0; }
    .footer { text-align: center; padding: 2rem 0 0.5rem 0; border-top: 1px solid rgba(255,255,255,0.05); margin-top: 2rem; }
    .footer .brand { color: #ffffff; font-weight: 600; font-size: 0.9rem; }
    .footer .tagline { color: rgba(255,255,255,0.3); font-size: 0.7rem; letter-spacing: 1px; }
    .footer .copyright { color: rgba(255,255,255,0.15); font-size: 0.6rem; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# MODULE IMPORTS - ALL V4 MODULES
# ============================================================

from hackathon.app.modules.v4.mission_control_header import render_mission_control_header
from hackathon.app.modules.v4.national_briefing import render_national_briefing
from hackathon.app.modules.v4.situation_map import render_situation_map
from hackathon.app.modules.v4.evidence_panel import render_evidence_panel
from hackathon.app.modules.v4.operations_panel import render_operations_panel
from hackathon.app.modules.v4.impact_panel import render_impact_panel
from hackathon.app.modules.v4.community_intelligence import render_community_intelligence
from hackathon.app.modules.v4.decision_support import render_decision_support
from hackathon.app.modules.v4.forecast_timeline import render_forecast_timeline
from hackathon.app.modules.v4.ai_copilot import render_ai_copilot

# ============================================================
# CONFIG
# ============================================================
API_URL = os.getenv("NFCC_API_URL", "https://nfcc-platform-production.up.railway.app")

DISTRICTS = {
    "Accra Central": {"region": "Greater Accra", "population": 187928, "lat": 5.560, "lon": -0.210},
    "Accra West": {"region": "Greater Accra", "population": 203461, "lat": 5.550, "lon": -0.230},
    "Accra East": {"region": "Greater Accra", "population": 142587, "lat": 5.565, "lon": -0.190},
    "Tema": {"region": "Greater Accra", "population": 198742, "lat": 5.650, "lon": -0.020},
    "Kumasi": {"region": "Ashanti", "population": 443981, "lat": 6.670, "lon": -1.620},
    "Tamale": {"region": "Northern", "population": 371578, "lat": 9.400, "lon": -0.840},
}

def call_api(endpoint, method="GET", data=None):
    """Call the NFCC API - only external call with exception handling."""
    url = f"{API_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        else:
            response = requests.post(url, json=data, timeout=10)
        return response.json() if response.status_code == 200 else {}
    except requests.RequestException:
        return {}

# ============================================================
# MAIN DASHBOARD - PURE ORCHESTRATOR
# ============================================================
def main():
    # Sidebar
    with st.sidebar:
        st.markdown("### 🎯 Control Panel")
        district = st.selectbox("📍 Select District", list(DISTRICTS.keys()), index=0, key="district_select")
        rainfall_mm = st.slider("🌧️ Rainfall (mm)", 0, 200, 75, key="rainfall_slider")
        
        st.divider()
        st.markdown("### 📡 Data Sources")
        sources = [
            ("🛰️ CHIRPS Rainfall", "active"),
            ("🌤️ Open-Meteo Forecast", "active"),
            ("💧 NASA SMAP", "active"),
            ("📡 Sentinel-1 SAR", "active"),
            ("🌊 Ghana River Gauges", "active"),
            ("🏗️ Dam Database", "active")
        ]
        for name, status in sources:
            st.markdown(f"{'🟢' if status == 'active' else '🔴'} {name}")
        
        st.divider()
        health = call_api("/health")
        if health.get("status") == "healthy":
            st.success("✅ API Connected")
        else:
            st.warning("⚠️ API Unavailable")
        st.caption(API_URL)
    
    # Get data
    with st.spinner("🔄 Analyzing flood risk..."):
        score_data = call_api("/score", "POST", {"location": district, "precipitation": rainfall_mm})
    
    score = score_data.get("score", 50)
    risk_tier = score_data.get("risk_tier", "MODERATE")
    
    # ============================================================
    # HEADER
    # ============================================================
    render_mission_control_header()
    
    # ============================================================
    # KEY METRICS
    # ============================================================
    risk_color = "metric-critical" if score >= 80 else "metric-high" if score >= 60 else "metric-moderate" if score >= 40 else "metric-low"
    risk_emoji = "🔴" if score >= 80 else "🟠" if score >= 60 else "🟡" if score >= 40 else "🟢"
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="glass-card {risk_color}">
            <div class="label">Risk Score</div>
            <div class="value">{risk_emoji} {score:.1f}%</div>
            <div class="delta">Category: {risk_tier}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="glass-card">
            <div class="label">Population</div>
            <div class="value">{DISTRICTS[district]['population']:,}</div>
            <div class="delta">District total</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="glass-card">
            <div class="label">Rainfall</div>
            <div class="value">{rainfall_mm} mm</div>
            <div class="delta">24-hour accumulation</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="glass-card">
            <div class="label">River Status</div>
            <div class="value" style="font-size: 1.2rem;">🟢 Odaw</div>
            <div class="delta">Level: 0.45m • NORMAL</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    
    # ============================================================
    # AI SITUATION BRIEF
    # ============================================================
    render_national_briefing(district, score)
    
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    
    # ============================================================
    # MAP + EVIDENCE
    # ============================================================
    col1, col2 = st.columns([2, 1])
    with col1:
        render_situation_map(district, score)
    with col2:
        render_evidence_panel()
    
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    
    # ============================================================
    # OPERATIONS + IMPACT + COMMUNITY
    # ============================================================
    col1, col2, col3 = st.columns(3)
    with col1:
        render_operations_panel(district)
    with col2:
        render_impact_panel(district, score)
    with col3:
        render_community_intelligence()
    
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    
    # ============================================================
    # DECISION SUPPORT + FORECAST TIMELINE
    # ============================================================
    col1, col2 = st.columns(2)
    with col1:
        render_decision_support(district, score)
    with col2:
        render_forecast_timeline()
    
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    
    # ============================================================
    # AI COPILOT
    # ============================================================
    render_ai_copilot()
    
    # ============================================================
    # FOOTER
    # ============================================================
    st.markdown(f"""
    <div class="footer">
        <div class="brand">🌊 CivicFlood AI</div>
        <div class="tagline">Decision Intelligence for National Flood Response</div>
        <div style="display: flex; justify-content: center; gap: 2rem; margin: 0.5rem 0;">
            <span style="color: rgba(255,255,255,0.2); font-size: 0.6rem;">NFCC Platform</span>
            <span style="color: rgba(255,255,255,0.2); font-size: 0.6rem;">Ghana AI Innovation Challenge 2026</span>
        </div>
        <div class="copyright">© 2026 • Data Sources: CHIRPS, SMAP, Sentinel-1, Ghana Hydrological Services</div>
        <div style="margin-top: 0.3rem;">
            <span style="color: rgba(255,255,255,0.1); font-size: 0.5rem;">🔗 {API_URL}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
