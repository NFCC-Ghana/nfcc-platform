"""
CivicFlood AI - Main Dashboard Page
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import json

# Set page config

# API URL
API_URL = "https://nfcc-platform-production.up.railway.app"

def call_api(endpoint: str, method: str = "GET", data: dict = None) -> dict:
    """Call the NFCC API"""
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
        else:
            return {"error": f"API returned {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

# Districts
DISTRICTS = {
    "Accra Central": {"region": "Greater Accra", "population": 187928, "lat": 5.560, "lon": -0.210},
    "Accra West": {"region": "Greater Accra", "population": 203461, "lat": 5.550, "lon": -0.230},
    "Accra East": {"region": "Greater Accra", "population": 142587, "lat": 5.565, "lon": -0.190},
    "Tema": {"region": "Greater Accra", "population": 198742, "lat": 5.650, "lon": -0.020},
    "Kumasi": {"region": "Ashanti", "population": 443981, "lat": 6.670, "lon": -1.620},
    "Tamale": {"region": "Northern", "population": 371578, "lat": 9.400, "lon": -0.840},
}

def main():
    # Header
    st.title("🌊 CivicFlood AI")
    st.caption("National Flood Intelligence Platform • Ghana AI Innovation Challenge 2026")
    
    # Check API health
    health = call_api("/health")
    if health.get("status") == "healthy":
        st.success("✅ Backend API Connected")
    else:
        st.warning("⚠️ Backend API Unavailable - Using Fallback")
    
    st.divider()
    
    # Sidebar
    with st.sidebar:
        st.markdown("## 🎛️ Controls")
        district = st.selectbox("📍 Select District", list(DISTRICTS.keys()), index=0)
        rainfall_mm = st.slider("🌧️ Rainfall (mm)", 0, 200, 75)
        st.divider()
        st.markdown("### 📊 Data Sources")
        for src in ["CHIRPS Rainfall", "Open-Meteo Forecast", "NASA SMAP", "Sentinel-1 SAR", "Ghana River Gauges"]:
            st.markdown(f"✅ {src}")
    
    # Main content
    info = DISTRICTS[district]
    
    # Get score
    with st.spinner("Analyzing risk..."):
        score_data = call_api("/score", "POST", {
            "location": district,
            "precipitation": rainfall_mm
        })
    
    score = score_data.get("score", 50)
    risk_tier = score_data.get("risk_tier", "MODERATE")
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("District", district)
    with col2:
        st.metric("Population", f"{info['population']:,}")
    with col3:
        st.metric("Rainfall", f"{rainfall_mm} mm")
    with col4:
        color = "🔴" if score >= 80 else "🟠" if score >= 60 else "🟡" if score >= 40 else "🟢"
        st.metric("Risk Score", f"{color} {score:.1f}%")
    
    st.divider()
    
    # Risk details
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"### Risk Category: **{risk_tier}**")
        st.progress(score/100, text=f"{score:.1f}%")
    with col2:
        st.markdown("### Recommendations")
        if score >= 80:
            st.error("🚨 IMMEDIATE EVACUATION - Seek higher ground")
        elif score >= 60:
            st.warning("⚠️ PREPARE TO EVACUATE - Move to higher ground")
        elif score >= 40:
            st.info("ℹ️ MONITOR CONDITIONS - Stay informed")
        else:
            st.success("✅ NORMAL - No immediate risk")
    
    st.divider()
    st.caption("Made with ❤️ for Ghana AI Innovation Challenge 2026")

if __name__ == "__main__":
    main()
