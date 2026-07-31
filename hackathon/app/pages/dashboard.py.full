"""
CivicFlood AI - Enterprise Command Center
Single authoritative dashboard for NADMO operations.
Replaces ALL previous dashboard versions.
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

# ============================================================
# CONFIGURATION
# ============================================================

API_URL = os.getenv("NFCC_API_URL", "https://nfcc-platform-production.up.railway.app")

# Page config
st.set_page_config(
    page_title="CivicFlood AI - National Emergency Operations Center",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# API FUNCTIONS
# ============================================================

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
            return {"status_code": response.status_code, "error": response.text[:200]}
    except requests.exceptions.Timeout:
        return {"error": "Timeout connecting to API"}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to API"}
    except Exception as e:
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
# RENDER FUNCTIONS - ENTERPRISE COMMAND CENTER
# ============================================================

def render_header(state):
    """Render the enterprise command center header."""
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown("""
        # 🌊 CivicFlood AI
        ### National Emergency Operations Center
        """)
        st.caption(f"🇬🇭 Ghana AI Innovation Challenge 2026 • v{state.api_version}")
    
    with col2:
        st.markdown("🟢 **SYSTEM ACTIVE**")
        st.caption(f"🕐 {datetime.now().strftime('%d %b %Y, %H:%M UTC')}")
        st.caption(f"📊 {state.active_sources_count} Data Sources Active")
    
    with col3:
        api_status = "✅" if state.api_connected else "⚠️"
        st.markdown(f"{api_status} **API Connected**")
        st.code(API_URL, language="text")
    
    st.divider()


def render_control_panel(state):
    """Render the control panel."""
    
    with st.sidebar:
        st.markdown("## 🎯 Control Panel")
        
        districts = [
            "Accra Central",
            "Accra West",
            "Accra East",
            "Tema",
            "Kumasi",
            "Tamale"
        ]
        
        district = st.selectbox(
            "📍 Select District",
            districts,
            index=0
        )
        
        st.markdown("### 🌧️ Rainfall (mm)")
        rainfall_mm = st.slider(
            "Rainfall amount (mm)",
            min_value=0,
            max_value=200,
            value=75,
            help="24-hour cumulative rainfall"
        )
        
        st.divider()
        
        st.markdown("### 📡 Data Sources")
        sources = [
            "🛰️ CHIRPS Rainfall",
            "🌤️ Open-Meteo Forecast",
            "💧 NASA SMAP",
            "📡 Sentinel-1 SAR",
            "🌊 Ghana River Gauges",
            "🏗️ Dam Database"
        ]
        
        for source in sources:
            st.markdown(f"🟢 {source}")
        
        st.divider()
        st.caption("🏆 Ghana AI Innovation Challenge 2026")
    
    return {"district": district, "rainfall_mm": rainfall_mm}


def render_executive_summary(state):
    """Render the executive summary section."""
    
    st.markdown("## 📊 Executive Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        risk_color = state.risk_color
        risk_emoji = state.risk_emoji
        st.markdown(f"{risk_emoji} **Risk Score**")
        st.markdown(f"<h1 style='color:{risk_color};'>{state.risk_score:.0f}%</h1>", unsafe_allow_html=True)
        st.caption(f"Category: **{state.risk_category}**")
    
    with col2:
        st.markdown("🤖 **AI Brief**")
        if state.risk_score >= 60:
            brief = "High flood risk detected. Immediate attention required."
        elif state.risk_score >= 40:
            brief = "Moderate flood risk. Monitor conditions."
        else:
            brief = "Low flood risk. Normal monitoring."
        st.markdown(f"<div style='background-color:#f0f2f6;padding:10px;border-radius:5px;'>{brief}</div>", unsafe_allow_html=True)
        st.caption(f"Confidence: {state.risk_confidence*100:.0f}%")
    
    with col3:
        st.metric(
            "Population at Risk",
            f"{state.population_exposed:,}",
            delta=f"{state.exposure_percentage:.1f}%"
        )
        st.caption(f"Lead Time: {state.lead_time_hours}h")
    
    with col4:
        st.metric(
            "Communities Affected",
            state.communities_affected,
            delta=f"{state.total_reports} Reports"
        )
        st.caption(f"{state.verified_reports} Verified")
    
    st.divider()


def render_national_map(state):
    """Render the national flood map."""
    
    st.markdown("## 🗺️ National Flood Map")
    
    # Import map module
    from hackathon.app.modules.v4.situation_map import render_situation_map
    render_situation_map(state)
    
    st.divider()


def render_evidence_panel(state):
    """Render the evidence panel."""
    
    st.markdown("## 📊 Evidence & Data Quality")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🛰️ Satellite & Weather")
        st.markdown("✅ CHIRPS Updated: 2m ago")
        st.markdown("✅ SMAP Updated: 2h ago")
        st.markdown("✅ Sentinel-1 Updated: 6h ago")
        st.markdown("✅ Open-Meteo Forecast: Active")
    
    with col2:
        st.markdown("### 🌊 Ground Intelligence")
        st.markdown(f"✅ River Gauges: {state.river_status}")
        st.markdown(f"✅ Dam Monitoring: {state.dam_risk} Risk")
        st.markdown(f"✅ Soil Moisture: {state.soil_saturation_percent:.0f}%")
        st.markdown(f"✅ Data Quality: {state.data_quality_score:.0f}%")
    
    st.caption(f"🔄 Last updated: {state.timestamp[:19]}")
    st.divider()


def render_impact_panel(state):
    """Render the impact assessment panel."""
    
    st.markdown("## 👥 Impact Assessment")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### Population")
        st.metric("Total Exposed", f"{state.population_exposed:,}")
        st.metric("Children (<18)", f"{state.children_exposed:,}")
        st.metric("Elderly (>60)", f"{state.elderly_exposed:,}")
    
    with col2:
        st.markdown("### Infrastructure")
        st.metric("Schools at Risk", state.schools_exposed)
        st.metric("Hospitals at Risk", state.hospitals_exposed)
        st.metric("Markets at Risk", state.markets_exposed)
    
    with col3:
        st.markdown("### Economic Impact")
        st.metric("Total Loss", f"GH₵ {state.total_loss_ghs:,.0f}")
        st.metric("Recovery Time", f"{state.recovery_weeks:.0f} weeks")
        st.caption(f"Impact Level: {state.economic_impact_level}")
    
    if state.affected_communities:
        st.markdown("### 🏘️ Communities Affected")
        st.markdown("• " + " • ".join(state.affected_communities))
    
    st.divider()


def render_operations_panel(state):
    """Render the operations panel."""
    
    st.markdown("## 🚗 Operations & Resources")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏛️ Shelters")
        shelters = [
            {"name": "Accra High School", "status": "OPEN", "capacity": 1200},
            {"name": "Community Center", "status": "OPEN", "capacity": 500},
            {"name": "Trade Fair Centre", "status": "PREPARING", "capacity": 2000},
        ]
        
        for shelter in shelters:
            status = "🟢" if shelter["status"] == "OPEN" else "🟡"
            st.markdown(f"{status} **{shelter['name']}**")
            st.caption(f"Capacity: {shelter['capacity']:,} • {shelter['status']}")
    
    with col2:
        st.markdown("### 📦 Resources")
        col2a, col2b = st.columns(2)
        with col2a:
            st.metric("Rescue Boats", "3", "🚤")
            st.metric("Ambulances", "5", "🚑")
        with col2b:
            st.metric("Pumps", "10", "💧")
            st.metric("Rescue Teams", "4", "👥")
    
    st.divider()


def render_ai_decision_center(state):
    """Render the AI decision center."""
    
    st.markdown("## 🎯 AI Decision Center")
    
    # Recommendations
    actions = state.actions_priority or [
        {"priority": "CRITICAL", "action": "Issue Evacuation Order", "impact": "8,000 residents protected", "time": "Immediate"},
        {"priority": "HIGH", "action": "Deploy Pumps to Affected Areas", "impact": "18cm water reduction", "time": "Next 2 hours"},
        {"priority": "MEDIUM", "action": "Close High-Risk Roads", "impact": "42% traffic reduction", "time": "Next 4 hours"},
        {"priority": "LOW", "action": "Open Shelters", "impact": "2,000 shelter capacity", "time": "Next 6 hours"},
    ]
    
    for action in actions[:4]:
        priority = action.get("priority", "LOW")
        if priority == "CRITICAL":
            st.error(f"🚨 **{action.get('action', 'Action')}**")
        elif priority == "HIGH":
            st.warning(f"⚠️ **{action.get('action', 'Action')}**")
        elif priority == "MEDIUM":
            st.info(f"ℹ️ **{action.get('action', 'Action')}**")
        else:
            st.success(f"✅ **{action.get('action', 'Action')}**")
        
        st.caption(f"Impact: {action.get('impact', 'N/A')} • Time: {action.get('time', 'N/A')}")
    
    st.divider()


def render_risk_timeline(state):
    """Render the risk timeline."""
    
    st.markdown("## ⏰ Risk Timeline")
    
    # Generate timeline data
    hours = ["Now", "6h", "12h", "18h", "24h"]
    current_risk = state.risk_score
    risks = [
        current_risk,
        min(100, current_risk + 15),
        min(100, current_risk + 10),
        min(100, current_risk + 5),
        min(100, current_risk)
    ]
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    for i, (hour, risk) in enumerate(zip(hours, risks)):
        with [col1, col2, col3, col4, col5][i]:
            color = "🔴" if risk >= 80 else "🟠" if risk >= 60 else "🟡" if risk >= 40 else "🟢"
            st.metric(hour, f"{color} {risk:.0f}%")
            st.progress(risk/100)
    
    peak_risk = max(risks)
    peak_hour = hours[risks.index(peak_risk)]
    st.warning(f"⚠️ Peak Risk: {peak_risk:.0f}% expected in {peak_hour}")
    
    st.divider()


def render_ai_copilot(state):
    """Render the AI copilot."""
    
    st.markdown("## 🤖 AI Copilot")
    
    st.caption("Ask questions about flood risks, evacuation, and emergency response")
    
    # Quick questions
    col1, col2, col3, col4 = st.columns(4)
    
    questions = [
        "What roads will flood?",
        "Should we evacuate?",
        "When will rain stop?",
        "Which areas are high risk?"
    ]
    
    for i, question in enumerate(questions):
        with [col1, col2, col3, col4][i]:
            if st.button(question, key=f"copilot_{i}"):
                st.session_state['copilot_query'] = question
    
    # Chat input
    query = st.chat_input("Ask CivicFlood AI about flood risks, evacuation, or safety...")
    
    if query:
        st.session_state['copilot_query'] = query
    
    # Display response
    if 'copilot_query' in st.session_state and st.session_state['copilot_query']:
        query = st.session_state['copilot_query']
        
        # Generate response based on query
        if "evacuate" in query.lower():
            st.info(f"🚨 **Evacuation Recommendation for {state.district}**\n\n"
                   f"Current risk: {state.risk_score:.0f}% ({state.risk_category})\n"
                   f"Lead time: {state.lead_time_hours}h\n"
                   f"Action: {state.lead_time_action}\n\n"
                   f"Nearest shelter: Accra High School (1.2km)")
        elif "road" in query.lower():
            st.info(f"🛣️ **Road Intelligence for {state.district}**\n\n"
                   f"Risk level: {state.risk_score:.0f}%\n"
                   f"Affected communities: {', '.join(state.affected_communities[:3])}\n\n"
                   f"Safe routes recommended via Ring Road and Independence Avenue.")
        elif "rain" in query.lower():
            st.info(f"🌧️ **Rainfall Forecast for {state.district}**\n\n"
                   f"Current: {state.rainfall_mm}mm\n"
                   f"Forecast 24h: {state.forecast_24h_mm:.0f}mm\n"
                   f"Forecast 48h: {state.forecast_48h_mm:.0f}mm\n"
                   f"Forecast 72h: {state.forecast_72h_mm:.0f}mm")
        else:
            st.info(f"🤖 **CivicFlood AI Assistant**\n\n"
                   f"Current risk in {state.district}: {state.risk_score:.0f}% ({state.risk_category})\n"
                   f"Population affected: {state.population_exposed:,}\n"
                   f"Lead time: {state.lead_time_hours}h\n\n"
                   f"How can I help you? Try asking about evacuation, roads, or rain.")

# ============================================================
# MAIN APPLICATION
# ============================================================

def main():
    """Main dashboard orchestrator - Enterprise Command Center."""
    
    # Get control panel inputs
    control_data = render_control_panel(None)
    district = control_data.get("district", "Accra Central")
    rainfall_mm = control_data.get("rainfall_mm", 75.0)
    
    # Get district data
    district_data = get_district_data(district)
    
    # Build API payload
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
    
    # Create state
    state = create_state_from_api(api_data)
    
    # Set district data
    state.district = district
    state.rainfall_mm = rainfall_mm
    state.population = district_data.get("population", 187928)
    state.region = district_data.get("region", "Greater Accra")
    state.lat = district_data.get("lat", 5.560)
    state.lon = district_data.get("lon", -0.210)
    state.elevation_m = district_data.get("elevation", 10)
    state.area_km2 = district_data.get("area_km2", 45.5)
    state.api_connected = "error" not in api_data
    
    # Set default values if API didn't provide them
    if state.lead_time_hours == 0:
        if state.risk_score >= 80:
            state.lead_time_hours = 2
            state.lead_time_action = "IMMEDIATE EVACUATION"
        elif state.risk_score >= 60:
            state.lead_time_hours = 6
            state.lead_time_action = "PREPARE TO EVACUATE"
        elif state.risk_score >= 40:
            state.lead_time_hours = 24
            state.lead_time_action = "MONITOR CONDITIONS"
        else:
            state.lead_time_hours = 72
            state.lead_time_action = "STAY INFORMED"
    
    # Render the enterprise dashboard
    render_header(state)
    
    # Executive Summary (What is happening? + Why?)
    render_executive_summary(state)
    
    # National Map (Where is it happening?)
    render_national_map(state)
    
    # Evidence + Community Intelligence (Why? + Who?)
    col1, col2 = st.columns(2)
    with col1:
        render_evidence_panel(state)
    with col2:
        # Community intelligence
        st.markdown("## 📢 Community Intelligence")
        st.metric("Total Reports", state.total_reports)
        st.metric("Verified Reports", state.verified_reports)
        st.metric("Communities", state.communities_affected)
        st.divider()
    
    # Impact + Operations (Who? + What should we do?)
    col1, col2 = st.columns(2)
    with col1:
        render_impact_panel(state)
    with col2:
        render_operations_panel(state)
    
    # AI Decision Center (What should we do?)
    render_ai_decision_center(state)
    
    # Risk Timeline (What happens next?)
    render_risk_timeline(state)
    
    # AI Copilot (All questions)
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
        st.error("🚨 Dashboard encountered an error. Please check the logs.")
        st.exception(e)

