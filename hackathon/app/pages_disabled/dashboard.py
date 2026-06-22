"""
CivicFlood AI - Simple Dashboard Fallback
"""

import streamlit as st
import requests
from datetime import datetime

API_URL = "https://nfcc-platform-production.up.railway.app"

DISTRICTS = {
    "Accra Central": {"region": "Greater Accra", "population": 187928},
    "Accra West": {"region": "Greater Accra", "population": 203461},
    "Accra East": {"region": "Greater Accra", "population": 142587},
    "Tema": {"region": "Greater Accra", "population": 198742},
    "Kumasi": {"region": "Ashanti", "population": 443981},
    "Tamale": {"region": "Northern", "population": 371578},
}


def call_api(endpoint, method="GET", data=None):
    """Call the NFCC API."""
    url = f"{API_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        else:
            response = requests.post(url, json=data, timeout=10)
        return response.json() if response.status_code == 200 else {}
    except:
        return {}


def main():
    """Main dashboard function - called by streamlit_app.py."""
    st.title("🌊 CivicFlood AI - Simple Dashboard")
    st.caption("National Flood Intelligence Platform • Ghana AI Innovation Challenge 2026")

    # Check API
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
        for src in ["CHIRPS Rainfall", "Open-Meteo Forecast", "NASA SMAP"]:
            st.markdown(f"✅ {src}")

    # Main content
    info = DISTRICTS[district]

    with st.spinner("Analyzing risk..."):
        score_data = call_api("/score", "POST", {
            "location": district,
            "precipitation": rainfall_mm
        })

    score = score_data.get("score", 50)
    risk_tier = score_data.get("risk_tier", "MODERATE")

    # Metrics
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

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"### Risk Category: **{risk_tier}**")
        st.progress(score/100, text=f"{score:.1f}%")
    with col2:
        st.markdown("### Recommendations")
        if score >= 80:
            st.error("🚨 IMMEDIATE EVACUATION")
        elif score >= 60:
            st.warning("⚠️ PREPARE TO EVACUATE")
        elif score >= 40:
            st.info("ℹ️ MONITOR CONDITIONS")
        else:
            st.success("✅ NORMAL - No immediate risk")

    st.divider()
    st.caption("Made with ❤️ for Ghana AI Innovation Challenge 2026")
    st.caption(f"🔗 Backend API: {API_URL}")


if __name__ == "__main__":
    main()
