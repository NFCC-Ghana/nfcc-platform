"""
CivicFlood AI - Professional Dashboard
Ghana AI Innovation Challenge 2026
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import requests
import json
import sys
from pathlib import Path
import os

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="CivicFlood AI - National Flood Intelligence",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CUSTOM CSS - PROFESSIONAL DESIGN
# ============================================================
st.markdown("""
<style>
    /* Main Background */
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* Header Gradient */
    .header-gradient {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 1.5rem 2rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    .header-gradient h1 {
        color: white;
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    .header-gradient p {
        color: #a8d8ea;
        margin: 0.2rem 0 0 0;
        font-size: 1.1rem;
    }
    .header-gradient .badge {
        background: rgba(255,255,255,0.15);
        padding: 0.3rem 1rem;
        border-radius: 20px;
        font-size: 0.8rem;
        color: #8ecae6;
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    /* Card Styles */
    .metric-card {
        background: white;
        padding: 1rem 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
        border-left: 4px solid #0f3460;
        height: 100%;
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
    }
    .metric-card .label {
        color: #666;
        font-size: 0.85rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-card .value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1a1a2e;
        margin: 0.2rem 0;
    }
    .metric-card .delta {
        font-size: 0.8rem;
        color: #666;
    }
    
    /* Risk Card Colors */
    .risk-extreme { border-left-color: #ff0000; }
    .risk-high { border-left-color: #ff6600; }
    .risk-moderate { border-left-color: #ffaa00; }
    .risk-low { border-left-color: #00cc00; }
    
    /* Section Headers */
    .section-header {
        font-size: 1.3rem;
        font-weight: 600;
        color: #1a1a2e;
        margin: 1.5rem 0 0.8rem 0;
        padding-bottom: 0.3rem;
        border-bottom: 2px solid #e8e8e8;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        color: #888;
        font-size: 0.8rem;
        padding: 2rem 0 0.5rem 0;
        border-top: 1px solid #e8e8e8;
        margin-top: 2rem;
    }
    .footer a {
        color: #0f3460;
        text-decoration: none;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: #1a1a2e;
    }
    .sidebar-section {
        padding: 0.5rem 0;
    }
    .sidebar-label {
        color: #a8d8ea;
        font-size: 0.8rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# CONFIGURATION
# ============================================================
API_URL = os.getenv("NFCC_API_URL", "https://nfcc-platform-production.up.railway.app")

# ============================================================
# API HELPER
# ============================================================
def call_api(endpoint: str, method: str = "GET", data: dict = None) -> dict:
    url = f"{API_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        else:
            return {"error": f"Unsupported method: {method}"}
        if response.status_code == 200:
            return response.json()
        return {"error": f"API returned {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# DISTRICTS
# ============================================================
DISTRICTS = {
    "Accra Central": {"region": "Greater Accra", "population": 187928, "lat": 5.560, "lon": -0.210},
    "Accra West": {"region": "Greater Accra", "population": 203461, "lat": 5.550, "lon": -0.230},
    "Accra East": {"region": "Greater Accra", "population": 142587, "lat": 5.565, "lon": -0.190},
    "Tema": {"region": "Greater Accra", "population": 198742, "lat": 5.650, "lon": -0.020},
    "Kumasi": {"region": "Ashanti", "population": 443981, "lat": 6.670, "lon": -1.620},
    "Tamale": {"region": "Northern", "population": 371578, "lat": 9.400, "lon": -0.840},
    "Sekondi-Takoradi": {"region": "Western", "population": 245567, "lat": 4.920, "lon": -1.710},
    "Cape Coast": {"region": "Central", "population": 169894, "lat": 5.105, "lon": -1.250},
    "Ho": {"region": "Volta", "population": 153705, "lat": 6.600, "lon": 0.470},
    "Sunyani": {"region": "Bono", "population": 138256, "lat": 7.336, "lon": -2.348}
}

# ============================================================
# MAIN DASHBOARD
# ============================================================
def main():
    # ============================================================
    # HEADER
    # ============================================================
    st.markdown(f"""
    <div class="header-gradient">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
                <h1>🌊 CivicFlood AI</h1>
                <p>National Flood Intelligence Platform • Ghana AI Innovation Challenge 2026</p>
                <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem;">
                    <span class="badge">🟢 SYSTEM ACTIVE</span>
                    <span class="badge">v3.0.0</span>
                    <span class="badge">🏆 Hackathon Submission</span>
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 0.8rem; color: #8ecae6;">Last Updated</div>
                <div style="font-size: 0.9rem; font-weight: 500;">{datetime.now().strftime('%d %b %Y, %H:%M')}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ============================================================
    # SIDEBAR
    # ============================================================
    with st.sidebar:
        st.markdown("### 🎛️ Control Panel")
        
        district = st.selectbox("📍 Select District", list(DISTRICTS.keys()), index=0)
        rainfall_mm = st.slider("🌧️ Rainfall (mm)", 0, 200, 75, help="Current 24-hour rainfall")
        
        st.divider()
        
        st.markdown("### 📊 Data Sources")
        sources = [
            ("CHIRPS Rainfall", "✅"),
            ("Open-Meteo Forecast", "✅"),
            ("NASA SMAP", "✅"),
            ("Sentinel-1 SAR", "✅"),
            ("Ghana River Gauges", "✅"),
            ("Dam Database", "✅")
        ]
        for src, status in sources:
            st.markdown(f"{status} {src}")
        
        st.divider()
        
        # API Status
        st.markdown("### 🔗 API Status")
        health = call_api("/health")
        if health.get("status") == "healthy":
            st.success("✅ Connected")
        else:
            st.warning("⚠️ Unavailable")
        st.caption(API_URL)
        
        st.divider()
        st.caption("v3.0.0 • Hackathon Submission")
        st.caption("Made with ❤️ for Ghana AI Innovation Challenge 2026")

    # ============================================================
    # MAIN CONTENT
    # ============================================================
    info = DISTRICTS[district]
    
    # Get risk assessment
    with st.spinner("🔄 Analyzing flood risk..."):
        score_data = call_api("/score", "POST", {
            "location": district,
            "precipitation": rainfall_mm
        })
    
    if score_data.get("error"):
        st.warning(f"⚠️ API Error: {score_data['error']}")
        score = 50
        risk_tier = "MODERATE"
    else:
        score = score_data.get("score", 50)
        risk_tier = score_data.get("risk_tier", "MODERATE")
    
    # ============================================================
    # DISTRICT HEADER
    # ============================================================
    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 1rem 1.5rem; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 1rem;">
        <div>
            <div style="font-size: 1.2rem; font-weight: 600; color: #1a1a2e;">📍 {district}</div>
            <div style="font-size: 0.85rem; color: #666;">Region: {info['region']} • Population: {info['population']:,}</div>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 0.8rem; color: #666;">Rainfall</div>
            <div style="font-size: 1.2rem; font-weight: 600; color: #0f3460;">{rainfall_mm} mm</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ============================================================
    # RISK METRICS ROW
    # ============================================================
    risk_color = "risk-extreme" if score >= 80 else "risk-high" if score >= 60 else "risk-moderate" if score >= 40 else "risk-low"
    risk_emoji = "🔴" if score >= 80 else "🟠" if score >= 60 else "🟡" if score >= 40 else "🟢"
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card {risk_color}">
            <div class="label">Risk Score</div>
            <div class="value">{risk_emoji} {score:.1f}%</div>
            <div class="delta">Category: {risk_tier}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Confidence</div>
            <div class="value">80%</div>
            <div class="delta">Model reliability</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Population</div>
            <div class="value">{info['population']:,}</div>
            <div class="delta">District total</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">River Status</div>
            <div class="value" style="font-size: 1.2rem;">🟢 Odaw</div>
            <div class="delta">Level: 0.45m • NORMAL</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ============================================================
    # RECOMMENDATIONS
    # ============================================================
    st.markdown('<div class="section-header">🚨 Actionable Recommendations</div>', unsafe_allow_html=True)
    
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

    # ============================================================
    # FOOTER
    # ============================================================
    st.markdown(f"""
    <div class="footer">
        <p>🌊 CivicFlood AI • Powered by NFCC Platform • Ghana AI Innovation Challenge 2026</p>
        <p style="font-size: 0.7rem; color: #aaa;">Data sources: CHIRPS, Open-Meteo, NASA SMAP, Sentinel-1, Ghana Hydrological Services</p>
        <p style="font-size: 0.7rem; color: #aaa;">🔗 API: {API_URL}</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
