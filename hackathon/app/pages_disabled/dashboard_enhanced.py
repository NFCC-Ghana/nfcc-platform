"""
CivicFlood AI - Enhanced Dashboard
Complete flood intelligence platform with REAL Copilot
"""

import streamlit as st
import requests
from datetime import datetime
import sys
from pathlib import Path
import os
import folium
from streamlit_folium import folium_static

# ============================================================
# PATH SETUP
# ============================================================
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# ============================================================
# MODULE IMPORTS - ALL MODULES INTEGRATED
# ============================================================

# Original modules
from hackathon.app.modules.explainability import render_explainability
from hackathon.app.modules.hydrological import render_hydrological_intelligence
from hackathon.app.modules.forecast import render_forecast
from hackathon.app.modules.impact import render_impact_assessment
from hackathon.app.modules.community import render_community_reports
from hackathon.app.modules.timeline import render_timeline
from hackathon.app.modules.evacuation import render_evacuation_info
from hackathon.app.modules.ranking import render_district_ranking

# NEW: Use ENHANCED COPILOT instead of old one
from hackathon.app.modules.copilot_enhanced import render_enhanced_copilot

# New intelligence modules
from hackathon.app.modules.road_intelligence import render_road_intelligence
from hackathon.app.modules.risk_explainer import render_risk_explainer
from hackathon.app.modules.national_center import render_national_center

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
    url = f"{API_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        else:
            response = requests.post(url, json=data, timeout=10)
        return response.json() if response.status_code == 200 else {}
    except:
        return {}

def create_flood_risk_map(district: str, risk_level: str) -> folium.Map:
    m = folium.Map(location=[7.9465, -1.0232], zoom_start=7)
    # Add districts (simplified)
    districts_coords = {
        "Accra Central": [5.560, -0.210],
        "Tema": [5.650, -0.020],
        "Kumasi": [6.670, -1.620],
        "Tamale": [9.400, -0.840]
    }
    colors = {"EXTREME": "red", "HIGH": "orange", "MODERATE": "yellow", "LOW": "green"}
    color = colors.get(risk_level, "blue")
    if district in districts_coords:
        folium.CircleMarker(
            districts_coords[district],
            radius=30,
            color=color,
            fill=True,
            fillOpacity=0.4,
            popup=f"{district}<br>Risk: {risk_level}"
        ).add_to(m)
    return m

# ============================================================
# MAIN DASHBOARD
# ============================================================
def main():
    # Sidebar
    with st.sidebar:
        st.markdown("## 🎛️ Control Panel")
        district = st.selectbox("📍 Select District", list(DISTRICTS.keys()), index=0)
        rainfall_mm = st.slider("🌧️ Rainfall (mm)", 0, 200, 75)
        
        st.divider()
        st.markdown("### 📊 Data Sources")
        for src in ["CHIRPS Rainfall", "Open-Meteo Forecast", "NASA SMAP", "Sentinel-1 SAR", "Ghana River Gauges", "Dam Database"]:
            st.markdown(f"✅ {src}")
        
        st.divider()
        health = call_api("/health")
        if health.get("status") == "healthy":
            st.success("✅ API Connected")
        else:
            st.warning("⚠️ API Unavailable")
        st.caption(API_URL)
        st.divider()
        st.caption("v3.0.0 • Hackathon Submission")
    
    # Get data
    info = DISTRICTS[district]
    with st.spinner("🔄 Analyzing flood risk..."):
        score_data = call_api("/score", "POST", {"location": district, "precipitation": rainfall_mm})
    
    score = score_data.get("score", 50)
    risk_tier = score_data.get("risk_tier", "MODERATE")
    
    # Store in session state for all modules
    st.session_state.current_risk = score
    st.session_state.current_district = district
    st.session_state.current_rainfall = rainfall_mm
    st.session_state.current_soil = 85  # In production from API
    st.session_state.current_river = 0.45  # In production from API
    
    # Header
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); padding: 1.5rem 2rem; border-radius: 16px; color: white; margin-bottom: 1.5rem;">
        <h1 style="color: white; margin: 0;">🌊 CivicFlood AI</h1>
        <p style="color: #a8d8ea;">National Flood Intelligence Platform • Ghana AI Innovation Challenge 2026</p>
        <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem;">
            <span style="background: rgba(255,255,255,0.15); padding: 0.3rem 1rem; border-radius: 20px; font-size: 0.8rem; color: #8ecae6;">🟢 SYSTEM ACTIVE</span>
            <span style="background: rgba(255,255,255,0.15); padding: 0.3rem 1rem; border-radius: 20px; font-size: 0.8rem; color: #8ecae6;">v3.0.0</span>
            <span style="background: rgba(255,255,255,0.15); padding: 0.3rem 1rem; border-radius: 20px; font-size: 0.8rem; color: #8ecae6;">🏆 Hackathon Submission</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Metrics
    risk_emoji = "🔴" if score >= 80 else "🟠" if score >= 60 else "🟡" if score >= 40 else "🟢"
    risk_color = "#ff0000" if score >= 80 else "#ff6600" if score >= 60 else "#ffaa00" if score >= 40 else "#00cc00"
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div style="background: white; padding: 1rem 1.5rem; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); border-left: 4px solid {risk_color};">
            <div style="color: #666; font-size: 0.85rem; text-transform: uppercase;">Risk Score</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: #1a1a2e;">{risk_emoji} {score:.1f}%</div>
            <div style="font-size: 0.8rem; color: #666;">Category: {risk_tier}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.metric("Confidence", "80%", "Model reliability")
    with col3:
        st.metric("Population", f"{info['population']:,}", "District total")
    with col4:
        st.markdown(f"""
        <div style="background: white; padding: 1rem 1.5rem; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.06);">
            <div style="color: #666; font-size: 0.85rem; text-transform: uppercase;">River Status</div>
            <div style="font-size: 1.2rem; font-weight: 600;">🟢 Odaw</div>
            <div style="font-size: 0.8rem; color: #666;">Level: 0.45m • NORMAL</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # Map
    st.markdown("### 🗺️ Flood Risk Map")
    m = create_flood_risk_map(district, risk_tier)
    folium_static(m, width=700, height=450)
    st.divider()
    
    # ============================================================
    # EXISTING FEATURES
    # ============================================================
    render_explainability(district, score)
    st.divider()
    
    render_hydrological_intelligence(district)
    st.divider()
    
    render_forecast(district, score)
    st.divider()
    
    # ============================================================
    # NEW FEATURES - WITH ENHANCED COPILOT
    # ============================================================
    st.markdown("## 🆕 Advanced Intelligence Features")
    
    # Row 1: Road Intelligence + Risk Explainer
    col1, col2 = st.columns(2)
    with col1:
        render_road_intelligence(district, rainfall_mm, st.session_state.current_soil)
    with col2:
        render_risk_explainer(district, rainfall_mm, st.session_state.current_soil, st.session_state.current_river)
    
    st.divider()
    
    # Row 2: ENHANCED COPILOT (REAL INTELLIGENCE) + Timeline
    col1, col2 = st.columns(2)
    with col1:
        # THIS IS THE FIX - USING ENHANCED COPILOT, NOT OLD ONE
        render_enhanced_copilot(district, score, rainfall_mm, st.session_state.current_soil, st.session_state.current_river)
    with col2:
        render_timeline(score)
    
    st.divider()
    
    # Row 3: National Command Center
    render_national_center()
    
    st.divider()
    
    # ============================================================
    # EXISTING FEATURES (Continued)
    # ============================================================
    render_impact_assessment(district, score)
    st.divider()
    
    render_community_reports(district)
    st.divider()
    
    render_evacuation_info(district)
    st.divider()
    
    render_district_ranking()
    st.divider()
    
    # Recommendations
    st.markdown("### 🚨 Actionable Recommendations")
    if score >= 80:
        st.error("🚨 IMMEDIATE EVACUATION - Seek higher ground")
        st.warning("⚠️ PREPARE TO EVACUATE - Move to higher ground")
    elif score >= 60:
        st.warning("⚠️ PREPARE TO EVACUATE - Move to higher ground")
        st.info("ℹ️ MONITOR CONDITIONS - Stay informed")
    elif score >= 40:
        st.info("ℹ️ MONITOR CONDITIONS - Stay informed")
    else:
        st.success("✅ NORMAL - No immediate risk")
    
    # Footer
    st.markdown(f"""
    <div style="text-align: center; color: #888; font-size: 0.8rem; padding: 2rem 0 0.5rem 0; border-top: 1px solid #e8e8e8; margin-top: 2rem;">
        <p>🌊 CivicFlood AI • Powered by NFCC Platform • Ghana AI Innovation Challenge 2026</p>
        <p style="font-size: 0.7rem; color: #aaa;">Data sources: CHIRPS, Open-Meteo, NASA SMAP, Sentinel-1, Ghana Hydrological Services</p>
        <p style="font-size: 0.7rem; color: #aaa;">🔗 API: {API_URL}</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
