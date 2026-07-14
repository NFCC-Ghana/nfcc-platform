"""
CivicFlood AI - Canonical Dashboard
Complete implementation with all data dynamic.
"""

import streamlit as st
import requests
import json
from datetime import datetime
import sys
from pathlib import Path
import os
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import modules
from hackathon.app.modules.v4.state import DashboardState, create_state_from_api
from hackathon.app.modules.v4.header import render_header
from hackathon.app.modules.v4.control_panel import render_control_panel
from hackathon.app.modules.v4.risk_display import render_risk_display
from hackathon.app.modules.v4.situation_brief import render_situation_brief
from hackathon.app.modules.v4.evidence_panel import render_evidence_panel
from hackathon.app.modules.v4.situation_map import render_situation_map
from hackathon.app.modules.v4.operations import render_operations
from hackathon.app.modules.v4.impact_assessment import render_impact_assessment
from hackathon.app.modules.v4.community_intelligence import render_community_intelligence
from hackathon.app.modules.v4.decision_support import render_decision_support
from hackathon.app.modules.v4.forecast_timeline import render_forecast_timeline
from hackathon.app.modules.v4.ai_copilot import render_ai_copilot

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# API CONFIGURATION
# ============================================================

API_URL = os.getenv("NFCC_API_URL", "https://nfcc-platform-production.up.railway.app")


def call_api(endpoint: str, method: str = "GET", data: dict = None, timeout: int = 30) -> dict:
    """Call the NFCC API with robust error handling."""
    url = f"{API_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=timeout)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=timeout)
        else:
            return {"error": f"Unsupported method: {method}"}
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"API returned {response.status_code} for {endpoint}")
            return {"status_code": response.status_code, "error": response.text[:200]}
    except requests.exceptions.Timeout:
        logger.error(f"API timeout for {endpoint}")
        return {"error": "Timeout connecting to API"}
    except requests.exceptions.ConnectionError:
        logger.error(f"API connection error for {endpoint}")
        return {"error": "Cannot connect to API"}
    except Exception as e:
        logger.error(f"API call failed: {e}")
        return {"error": str(e)}


def get_district_data(district: str) -> dict:
    """Get district-specific data."""
    districts = {
        "Accra Central": {"region": "Greater Accra", "population": 187928, "area_km2": 45.5, "lat": 5.560, "lon": -0.210, "elevation": 12},
        "Accra West": {"region": "Greater Accra", "population": 203461, "area_km2": 52.3, "lat": 5.550, "lon": -0.230, "elevation": 10},
        "Accra East": {"region": "Greater Accra", "population": 142587, "area_km2": 38.2, "lat": 5.565, "lon": -0.190, "elevation": 15},
        "Tema": {"region": "Greater Accra", "population": 198742, "area_km2": 38.7, "lat": 5.650, "lon": -0.020, "elevation": 18},
        "Kumasi": {"region": "Ashanti", "population": 443981, "area_km2": 98.2, "lat": 6.670, "lon": -1.620, "elevation": 25},
        "Tamale": {"region": "Northern", "population": 371578, "area_km2": 67.4, "lat": 9.400, "lon": -0.840, "elevation": 125},
    }
    return districts.get(district, {})


# ============================================================
# MAIN APPLICATION
# ============================================================

def main():
    """Main dashboard orchestrator with complete state management."""
    
    # Get control panel inputs
    control_data = render_control_panel()
    district = control_data.get("district", "Accra Central")
    rainfall_mm = control_data.get("rainfall_mm", 75.0)
    
    # Get district data
    district_data = get_district_data(district)
    
    # Build API payload with all district data
    api_payload = {
        "location": district,
        "precipitation": rainfall_mm,
        "lat": district_data.get("lat", 5.560),
        "lon": district_data.get("lon", -0.210),
        "population": district_data.get("population", 100000),
        "elevation": district_data.get("elevation", 10),
        "region": district_data.get("region", "Greater Accra")
    }
    
    # Fetch risk data from API
    with st.spinner("🔄 Analyzing flood risk..."):
        api_data = call_api("/score", "POST", api_payload)
    
    # Create state from API data
    state = create_state_from_api(api_data)
    
    # Ensure district data is set (even if API doesn't return it)
    state.district = district
    state.rainfall_mm = rainfall_mm
    state.population = district_data.get("population", 187928)
    state.region = district_data.get("region", "Greater Accra")
    state.lat = district_data.get("lat", 5.560)
    state.lon = district_data.get("lon", -0.210)
    state.elevation_m = district_data.get("elevation", 10)
    state.area_km2 = district_data.get("area_km2", 45.5)
    
    # API connection status
    state.api_connected = "error" not in api_data
    
    # Render all sections
    render_header(state)
    render_risk_display(state)
    render_situation_brief(state)
    render_evidence_panel(state)
    
    # Map and Operations side by side
    col1, col2 = st.columns([2, 1])
    with col1:
        render_situation_map(state)
    with col2:
        render_operations(state)
    
    # Impact Assessment
    render_impact_assessment(state)
    
    # Community Intelligence and Decision Support
    col1, col2 = st.columns([2, 1])
    with col1:
        render_community_intelligence(state)
    with col2:
        render_decision_support(state)
    
    # Forecast Timeline
    render_forecast_timeline(state)
    
    # AI Copilot
    render_ai_copilot(state)
    
    # Footer
    st.divider()
    st.caption("🌊 CivicFlood AI • Decision Intelligence for National Flood Response")
    st.caption("NFCC Platform • Ghana AI Innovation Challenge 2026")
    st.caption(f"📊 {state.active_sources_count} Data Sources Active • 🔗 {API_URL}")
    st.caption(f"🔄 Last updated: {state.timestamp[:19]}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception("Dashboard error")
        st.error("🚨 Dashboard encountered an error. Please check the logs.")
        st.exception(e)

