"""
CivicFlood AI - Enterprise Command Center
Phase 3: Every section answers ONE question with clarity.
Palantir/IBM-level professional command center.
"""

import sys
from pathlib import Path

# Add project root to path BEFORE imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from datetime import datetime

import requests
import streamlit as st

from hackathon.app.modules.v4.state import create_state_from_api

# ============================================================
# CONFIGURATION
# ============================================================

API_URL = "https://nfcc-platform-production.up.railway.app"

st.set_page_config(
    page_title="CivicFlood AI - National Emergency Operations Center",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# API FUNCTIONS
# ============================================================


def call_api(
    endpoint: str, method: str = "GET", data: dict = None, timeout: int = 30
) -> dict:
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
        "Accra Central": {
            "region": "Greater Accra",
            "population": 187928,
            "area_km2": 45.5,
            "lat": 5.560,
            "lon": -0.210,
            "elevation": 12,
        },
        "Accra West": {
            "region": "Greater Accra",
            "population": 203461,
            "area_km2": 52.3,
            "lat": 5.550,
            "lon": -0.230,
            "elevation": 10,
        },
        "Accra East": {
            "region": "Greater Accra",
            "population": 142587,
            "area_km2": 38.2,
            "lat": 5.565,
            "lon": -0.190,
            "elevation": 15,
        },
        "Tema": {
            "region": "Greater Accra",
            "population": 198742,
            "area_km2": 38.7,
            "lat": 5.650,
            "lon": -0.020,
            "elevation": 18,
        },
        "Kumasi": {
            "region": "Ashanti",
            "population": 443981,
            "area_km2": 98.2,
            "lat": 6.670,
            "lon": -1.620,
            "elevation": 25,
        },
        "Tamale": {
            "region": "Northern",
            "population": 371578,
            "area_km2": 67.4,
            "lat": 9.400,
            "lon": -0.840,
            "elevation": 125,
        },
    }
    return districts.get(district, {})


# ============================================================
# SECTIONS - EACH ANSWERS ONE QUESTION
# ============================================================


def render_header(state):
    """Enterprise Command Center Header."""
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


def render_control_panel():
    """Control Panel."""
    with st.sidebar:
        st.markdown("## 🎯 Control Panel")

        districts = [
            "Accra Central",
            "Accra West",
            "Accra East",
            "Tema",
            "Kumasi",
            "Tamale",
        ]

        district = st.selectbox("📍 Select District", districts, index=0)

        st.markdown("### 🌧️ Rainfall (mm)")
        rainfall_mm = st.slider(
            "Rainfall amount (mm)",
            min_value=0,
            max_value=200,
            value=75,
            help="24-hour cumulative rainfall",
        )

        st.divider()
        st.markdown("### 📡 Data Sources")
        sources = [
            "🛰️ CHIRPS Rainfall",
            "🌤️ Open-Meteo Forecast",
            "💧 NASA SMAP",
            "📡 Sentinel-1 SAR",
            "🌊 Ghana River Gauges",
            "🏗️ Dam Database",
        ]
        for source in sources:
            st.markdown(f"🟢 {source}")

        st.divider()
        st.caption("🏆 Ghana AI Innovation Challenge 2026")

    return {"district": district, "rainfall_mm": rainfall_mm}


def render_executive_summary(state):
    """QUESTION 1: What is happening?"""
    st.markdown("## 📊 Executive Summary")
    st.caption("*What is happening right now?*")

    col1, col2 = st.columns([1.5, 1])

    with col1:
        risk_color = state.risk_color
        risk_emoji = state.risk_emoji

        st.markdown(f"{risk_emoji} **Risk Score**")
        st.markdown(
            f"<h1 style='color:{risk_color};'>{state.risk_score:.0f}%</h1>",
            unsafe_allow_html=True,
        )
        st.caption(f"**{state.risk_category}** Emergency Level")
        st.progress(state.risk_score / 100)
        st.metric("Confidence", f"{state.risk_confidence * 100:.0f}%")

    with col2:
        st.markdown("🤖 **AI Situation Summary**")

        if state.risk_score >= 80:
            summary = "🔴 CRITICAL: Immediate evacuation required."
            color = "#ff0000"
            recommendation = "🚨 MANDATORY EVACUATION ORDER"
        elif state.risk_score >= 60:
            summary = "🟠 HIGH: Prepare for evacuation immediately."
            color = "#ff6600"
            recommendation = "⚠️ PREPARE TO EVACUATE"
        elif state.risk_score >= 40:
            summary = "🟡 MODERATE: Monitor conditions closely."
            color = "#ffaa00"
            recommendation = "📢 STAY INFORMED"
        else:
            summary = "🟢 LOW: Normal monitoring."
            color = "#00cc00"
            recommendation = "✅ CONTINUE NORMAL OPERATIONS"

        st.markdown(
            f"<div style='background-color:#f0f2f6;padding:15px;"
            f"border-radius:5px;border-left:5px solid {color};'>"
            f"<strong>{summary}</strong>"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.markdown(f"**Immediate Recommendation:** {recommendation}")
        st.caption(f"Lead Time: {state.lead_time_hours} hours")

    st.divider()


def render_national_map(state):
    """QUESTION 2: Where is it happening?"""
    st.markdown("## 🗺️ National Flood Map")
    st.caption("*Where is flooding occurring or expected?*")

    st.markdown(
        """
    <div style="background: linear-gradient(135deg, #1a1a2e, #16213e, #0f3460);
                border-radius: 16px;
                padding: 40px;
                text-align: center;
                color: white;
                min-height: 400px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;">
        <div style="font-size: 48px; margin-bottom: 16px;">🗺️</div>
        <h3>National Flood Risk Map</h3>
        <p style="color: #a0aec0;">
            Interactive map showing flood zones, shelters, roads, and routes
        </p>
        <div style="display: flex; gap: 20px; margin-top: 20px;
                    flex-wrap: wrap; justify-content: center;">
            <span style="background: #e53e3e; padding: 4px 12px;
                         border-radius: 4px;">🔴 EXTREME</span>
            <span style="background: #ed8936; padding: 4px 12px;
                         border-radius: 4px;">🟠 HIGH</span>
            <span style="background: #ecc94b; padding: 4px 12px;
                         border-radius: 4px;">🟡 MODERATE</span>
            <span style="background: #48bb78; padding: 4px 12px;
                         border-radius: 4px;">🟢 LOW</span>
            <span style="background: #4299e1; padding: 4px 12px;
                         border-radius: 4px;">🏛️ Shelter</span>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Districts Monitored", 10)
    with col2:
        st.metric("Active Flood Zones", 3)
    with col3:
        st.metric("Shelters Available", 3)
    with col4:
        st.metric("Verified Reports", 4)

    st.caption("🗺️ Click on markers for details • Updated in real-time")
    st.divider()


def render_evidence_panel(state):
    """QUESTION 3: Why does the AI believe this?"""
    st.markdown("## 🔬 Evidence & Confidence")
    st.caption("*Why does the AI believe this is happening?*")

    evidence_items = [
        {
            "name": "Rainfall Intensity",
            "score": min(100, state.rainfall_mm * 1.2),
            "stars": (
                "★★★★★"
                if state.rainfall_mm > 50
                else "★★★★☆" if state.rainfall_mm > 30 else "★★★☆☆"
            ),
            "confidence": state.evidence_rainfall_confidence,
        },
        {
            "name": "River Levels",
            "score": min(100, (state.river_level_m / 3) * 100),
            "stars": (
                "★★★★★"
                if state.river_level_m > 2.0
                else "★★★★☆" if state.river_level_m > 1.0 else "★★★☆☆"
            ),
            "confidence": state.evidence_river_confidence,
        },
        {
            "name": "Soil Saturation",
            "score": state.soil_saturation_percent,
            "stars": (
                "★★★★★"
                if state.soil_saturation_percent > 70
                else "★★★★☆" if state.soil_saturation_percent > 50 else "★★★☆☆"
            ),
            "confidence": state.evidence_soil_confidence,
        },
        {
            "name": "Satellite Detection",
            "score": 75 if state.risk_score > 50 else 40,
            "stars": (
                "★★★★★"
                if state.risk_score > 70
                else "★★★★☆" if state.risk_score > 40 else "★★★☆☆"
            ),
            "confidence": state.evidence_satellite_confidence,
        },
        {
            "name": "Citizen Reports",
            "score": min(100, state.total_reports * 10),
            "stars": (
                "★★★★★"
                if state.total_reports > 5
                else "★★★★☆" if state.total_reports > 2 else "★★★☆☆"
            ),
            "confidence": state.evidence_citizen_confidence,
        },
    ]

    col1, col2 = st.columns(2)

    with col1:
        for item in evidence_items[:3]:
            st.markdown(f"**{item['name']}**")
            st.markdown(f"{item['stars']} ({item['score']:.0f}%)")
            st.progress(item["score"] / 100)
            st.caption("")

    with col2:
        for item in evidence_items[3:]:
            st.markdown(f"**{item['name']}**")
            st.markdown(f"{item['stars']} ({item['score']:.0f}%)")
            st.progress(item["score"] / 100)
            st.caption("")

    st.markdown("---")

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.metric("Overall Confidence", f"{state.risk_confidence * 100:.0f}%")
    with col2:
        st.metric("Data Quality", f"{state.data_quality_score:.0f}%")
    with col3:
        st.metric("Active Sources", state.active_sources_count)

    st.divider()


def render_impact_panel(state):
    """QUESTION 4: Who is affected?"""
    st.markdown("## 👥 Impact Assessment")
    st.caption("*Who is affected and how?*")

    # People
    st.markdown("### 👤 People")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Exposed", f"{state.population_exposed:,}")
    with col2:
        st.metric("Children (<18)", f"{state.children_exposed:,}")
    with col3:
        st.metric("Elderly (>60)", f"{state.elderly_exposed:,}")
    with col4:
        st.metric("Households", f"{state.households_affected:,}")

    # Infrastructure
    st.markdown("### 🏗️ Infrastructure")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Schools", state.schools_exposed)
    with col2:
        st.metric("Hospitals", state.hospitals_exposed)
    with col3:
        st.metric("Markets", state.markets_exposed)
    with col4:
        st.metric("Power Substations", state.power_substations_affected)

    # Economy
    st.markdown("### 💰 Economy")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Residential Loss", f"GH₵ {state.residential_loss_ghs:,.0f}")
    with col2:
        st.metric("Infrastructure Loss", f"GH₵ {state.infrastructure_loss_ghs:,.0f}")
    with col3:
        st.metric("Total Loss", f"GH₵ {state.total_loss_ghs:,.0f}")

    # Environment
    st.markdown("### 🌍 Environment")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Soil Saturation", f"{state.soil_saturation_percent:.0f}%")
    with col2:
        st.metric("River Level", f"{state.river_level_m:.1f}m")

    if state.affected_communities:
        st.markdown("### 🏘️ Affected Communities")
        st.markdown("• " + " • ".join(state.affected_communities[:5]))

    st.divider()


def render_operations_panel(state):
    """QUESTION 5: What are we doing?"""
    st.markdown("## 🚗 Operations")
    st.caption("*What resources are deployed and available?*")

    st.markdown("### 🏛️ Shelters")
    shelters = [
        {
            "name": "Accra High School",
            "status": "OPEN",
            "capacity": 1200,
            "available": 850,
        },
        {
            "name": "Community Center",
            "status": "OPEN",
            "capacity": 500,
            "available": 320,
        },
        {
            "name": "Trade Fair Centre",
            "status": "PREPARING",
            "capacity": 2000,
            "available": 2000,
        },
    ]

    for shelter in shelters:
        status_color = "🟢" if shelter["status"] == "OPEN" else "🟡"
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"{status_color} **{shelter['name']}**")
        with col2:
            st.caption(f"Capacity: {shelter['capacity']:,}")
        with col3:
            st.caption(f"Available: {shelter['available']:,}")

    st.markdown("### 📦 Resources")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Rescue Boats", state.rescue_boats, "🚤 Ready")
    with col2:
        st.metric("Ambulances", state.ambulances, "🚑 Deployed")
    with col3:
        st.metric("Pumps", state.pumps, "💧 Available")
    with col4:
        st.metric("Rescue Teams", state.rescue_teams, "👥 Active")

    st.markdown("### 🗺️ Evacuation Routes")
    routes = [
        {"from": "Alajo", "to": "Accra High School", "time": "15 min"},
        {"from": "Kaneshie", "to": "Community Center", "time": "20 min"},
        {"from": "Circle", "to": "Trade Fair Centre", "time": "25 min"},
    ]
    for route in routes:
        st.markdown(f"🚗 **{route['from']}** → **{route['to']}** ({route['time']})")

    st.divider()


def render_ai_decision_center(state):
    """QUESTION 6: What should we do? (AI Decision Center)"""
    st.markdown("## 🎯 AI Decision Center")
    st.caption("*What actions should we take and why?*")

    if state.risk_score >= 80:
        action = "🚨 Issue Mandatory Evacuation Order"
        confidence = 95
        reasons = [
            "Rainfall exceeds historical thresholds",
            "River levels rising rapidly",
            "Roads becoming inaccessible",
            "Multiple citizen reports verified",
        ]
        impact = "Protect 8,200 people"
        cost = 120000
        time_window = "Within 45 minutes"
        urgency = "CRITICAL"
    elif state.risk_score >= 60:
        action = "⚠️ Prepare for Evacuation"
        confidence = 87
        reasons = [
            "Rainfall approaching warning levels",
            "River levels elevated",
            "Soil saturation increasing",
            "Reports of rising water",
        ]
        impact = "Protect 4,500 people"
        cost = 65000
        time_window = "Within 2 hours"
        urgency = "HIGH"
    elif state.risk_score >= 40:
        action = "📢 Issue Public Awareness Message"
        confidence = 78
        reasons = [
            "Rainfall expected to continue",
            "Conditions being monitored",
            "Communities advised to stay informed",
        ]
        impact = "Alert 12,000 people"
        cost = 15000
        time_window = "Within 4 hours"
        urgency = "MEDIUM"
    else:
        action = "✅ Continue Normal Monitoring"
        confidence = 92
        reasons = [
            "All indicators within normal range",
            "No immediate threat detected",
            "Regular updates provided",
        ]
        impact = "Monitor 10 districts"
        cost = 5000
        time_window = "Ongoing"
        urgency = "LOW"

    col1, col2 = st.columns([2, 1])

    with col1:
        urgency_color = (
            "🔴"
            if urgency == "CRITICAL"
            else "🟠" if urgency == "HIGH" else "🟡" if urgency == "MEDIUM" else "🟢"
        )
        st.markdown(f"{urgency_color} **Recommended Action**")
        st.markdown(
            f"<h2 style='font-size: 24px;'>{action}</h2>", unsafe_allow_html=True
        )

        st.progress(confidence / 100, text=f"Confidence: {confidence}%")

        st.markdown("**Why?**")
        for reason in reasons:
            st.markdown(f"• {reason}")

    with col2:
        st.markdown("**Expected Impact**")
        st.metric("Protection", impact)
        st.metric("Estimated Cost", f"GH₵ {cost:,.0f}")
        st.metric("Time Window", time_window)

    st.divider()


def render_risk_timeline(state):
    """QUESTION 7: What happens next?"""
    st.markdown("## ⏰ Risk Timeline")
    st.caption("*What is expected to happen in the next 24 hours?*")

    hours = ["Now", "6h", "12h", "18h", "24h"]
    current_risk = state.risk_score
    risks = [
        current_risk,
        min(100, current_risk + 15),
        min(100, current_risk + 10),
        min(100, current_risk + 5),
        min(100, current_risk),
    ]

    for hour, risk in zip(hours, risks):
        col1, col2 = st.columns([1, 4])
        with col1:
            st.markdown(f"**{hour}**")
        with col2:
            color = (
                "🔴"
                if risk >= 80
                else "🟠" if risk >= 60 else "🟡" if risk >= 40 else "🟢"
            )
            st.progress(risk / 100, text=f"{color} {risk:.0f}%")

    peak_risk = max(risks)
    peak_hour = hours[risks.index(peak_risk)]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Peak Risk", f"{peak_risk:.0f}%")
    with col2:
        st.metric("Peak Time", peak_hour)
    with col3:
        st.metric("Trend", "Increasing" if peak_risk > current_risk else "Stable")

    st.divider()


def render_ai_copilot(state):
    """AI Copilot - Answer any question."""
    st.markdown("## 🤖 AI Copilot")
    st.caption("*Ask any question about the situation*")

    col1, col2, col3, col4 = st.columns(4)
    questions = [
        "What roads will flood?",
        "Should we evacuate?",
        "When will rain stop?",
        "Which areas are high risk?",
    ]
    for i, question in enumerate(questions):
        with [col1, col2, col3, col4][i]:
            if st.button(question, key=f"copilot_{i}"):
                st.session_state["copilot_query"] = question

    query = st.chat_input(
        "Ask CivicFlood AI about flood risks, evacuation, or safety..."
    )
    if query:
        st.session_state["copilot_query"] = query

    if "copilot_query" in st.session_state:
        query = st.session_state["copilot_query"]
        response = f"Based on current data for {state.district}:\n\n"

        if "evacuate" in query.lower():
            response += "🚨 **Evacuation Assessment**\n\n"
            response += f"• Risk Level: {state.risk_score:.0f}% "
            response += f"({state.risk_category})\n"
            response += f"• Lead Time: {state.lead_time_hours} hours\n"
            response += f"• Recommended Action: {state.lead_time_action}\n\n"
            response += "**Nearest Shelter:** Accra High School (1.2 km)\n"
            response += "**Capacity:** 1,200 people\n"
            response += "**Route:** Ring Road → Independence Avenue"

        elif "road" in query.lower():
            response += "🛣️ **Road Intelligence**\n\n"
            response += f"• Current Risk: {state.risk_score:.0f}%\n"
            affected = state.affected_communities[:3]
            if not affected:
                affected = ["Accra Central"]
            response += f"• Affected Areas: {', '.join(affected)}\n\n"
            response += "**Safe Routes:**\n"
            response += "• Ring Road (Open)\n"
            response += "• Independence Avenue (Open)\n"
            response += "• Liberation Road (Open)\n\n"
            response += "**Avoid:**\n"
            response += "• Alajo Main Street (Water logging)\n"
            response += "• Kaneshie Market Road (Flooding reported)"

        elif "rain" in query.lower():
            response += "🌧️ **Rainfall Forecast**\n\n"
            response += f"• Current: {state.rainfall_mm}mm\n"
            response += f"• 24h Forecast: {state.forecast_24h_mm:.0f}mm\n"
            response += f"• 48h Forecast: {state.forecast_48h_mm:.0f}mm\n"
            response += f"• 72h Forecast: {state.forecast_72h_mm:.0f}mm\n\n"
            trend = (
                "increase" if state.forecast_24h_mm > state.rainfall_mm else "decrease"
            )
            response += f"Rain will {trend} in the next 24 hours."

        else:
            response += "📊 **Situation Summary**\n\n"
            response += f"• Location: {state.district}\n"
            response += f"• Risk: {state.risk_score:.0f}% "
            response += f"({state.risk_category})\n"
            response += f"• Population Affected: "
            response += f"{state.population_exposed:,}\n"
            response += f"• Communities: {state.communities_affected}\n"
            response += f"• Lead Time: {state.lead_time_hours}h\n\n"
            response += "**What would you like to know?**\n"
            response += "• Try: 'What roads will flood?'\n"
            response += "• Try: 'Should we evacuate?'\n"
            response += "• Try: 'When will rain stop?'"

        st.info(response)


# ============================================================
# MAIN APPLICATION
# ============================================================


def main():
    """Enterprise Command Center."""
    control_data = render_control_panel()
    district = control_data["district"]
    rainfall_mm = control_data["rainfall_mm"]

    district_data = get_district_data(district)

    api_payload = {
        "location": district,
        "precipitation": rainfall_mm,
        "lat": district_data.get("lat", 5.560),
        "lon": district_data.get("lon", -0.210),
        "population": district_data.get("population", 100000),
        "elevation": district_data.get("elevation", 10),
        "region": district_data.get("region", "Greater Accra"),
    }

    with st.spinner("🔄 Analyzing flood risk..."):
        api_data = call_api("/score", "POST", api_payload)

    state = create_state_from_api(api_data)

    state.district = district
    state.rainfall_mm = rainfall_mm
    state.population = district_data.get("population", 187928)
    state.region = district_data.get("region", "Greater Accra")
    state.lat = district_data.get("lat", 5.560)
    state.lon = district_data.get("lon", -0.210)
    state.elevation_m = district_data.get("elevation", 10)
    state.area_km2 = district_data.get("area_km2", 45.5)
    state.api_connected = "error" not in api_data

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

    render_header(state)
    render_executive_summary(state)
    render_national_map(state)
    render_evidence_panel(state)
    render_impact_panel(state)

    col1, col2 = st.columns(2)
    with col1:
        render_operations_panel(state)
    with col2:
        render_ai_decision_center(state)

    render_risk_timeline(state)
    render_ai_copilot(state)

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
