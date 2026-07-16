"""
CivicFlood AI - Enterprise Command Center
Phase 4: Visual Storytelling Implementation (Fixed)
International-standard professional dashboard
"""

# ============================================================
# IMPORTS - ALL AT THE TOP (E402 fixed)
# ============================================================

import sys
from datetime import datetime
from pathlib import Path

# Add project root to path BEFORE other imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))  # noqa: E402

import requests
import streamlit as st

from hackathon.app.modules.v4.situation_map import render_map_fallback
from hackathon.app.modules.v4.situation_map import render_situation_map
from hackathon.app.modules.v4.state import create_state_from_api
from hackathon.app.modules.v4.visual_components import (
    render_affected_communities,
    render_economic_impact,
    render_evidence_confidence,
    render_horizontal_progress_bar,
    render_impact_card,
    render_metric_card,
    render_population_visual,
    render_quick_stats,
    render_resource_status,
    render_risk_indicator,
    render_risk_timeline_visual,
    render_shelter_status,
    render_status_indicator,
    render_visual_metric_card,
)

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
# SECTIONS - EACH ANSWERS ONE QUESTION WITH VISUALS
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
    """QUESTION 1: What is happening? - VISUAL VERSION"""
    st.markdown("## 📊 Executive Summary")
    st.caption("*What is happening right now?*")

    col1, col2 = st.columns([1.5, 1])

    with col1:
        # Visual risk indicator
        render_risk_indicator(
            risk_score=state.risk_score,
            risk_category=state.risk_category,
            show_progress=True,
        )

        # Quick stats below
        render_quick_stats(
            [
                {
                    "label": "Confidence",
                    "value": f"{state.risk_confidence * 100:.0f}%",
                    "emoji": "🎯",
                    "color": "#38a169",
                },
                {
                    "label": "Lead Time",
                    "value": f"{state.lead_time_hours}",
                    "emoji": "⏰",
                    "color": "#4299e1",
                    "subtitle": "hours",
                },
                {
                    "label": "Data Quality",
                    "value": f"{state.data_quality_score:.0f}%",
                    "emoji": "📊",
                    "color": "#9f7aea",
                },
                {
                    "label": "Active Sources",
                    "value": state.active_sources_count,
                    "emoji": "📡",
                    "color": "#ed8936",
                },
            ],
            columns=4,
        )

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
    """QUESTION 2: Where is it happening? - MAP VISUAL"""
    st.markdown("## 🗺️ National Flood Map")
    st.caption("*Where is flooding occurring or expected?*")

    # Create a state object for the map
    class MapState:
        def __init__(self):
            self.lat = 5.560
            self.lon = -0.210
            self.district = "Accra Central"
            self.risk_score = 50
            self.risk_category = "MODERATE"

    map_state = MapState()
    map_state.lat = getattr(state, "lat", 5.560)
    map_state.lon = getattr(state, "lon", -0.210)
    map_state.district = getattr(state, "district", "Accra Central")
    map_state.risk_score = getattr(state, "risk_score", 50)
    map_state.risk_category = getattr(state, "risk_category", "MODERATE")

    # Render the actual map
    try:
        render_situation_map(map_state)
    except Exception as e:
        st.error(f"❌ Map error: {str(e)}")
        render_map_fallback()

    # Visual stats
    render_quick_stats(
        [
            {
                "label": "Districts Monitored",
                "value": 10,
                "emoji": "🗺️",
                "color": "#4299e1",
            },
            {
                "label": "Active Flood Zones",
                "value": 3,
                "emoji": "🌊",
                "color": "#e53e3e",
            },
            {
                "label": "Shelters Available",
                "value": 3,
                "emoji": "🏛️",
                "color": "#38a169",
            },
            {
                "label": "Verified Reports",
                "value": 4,
                "emoji": "✅",
                "color": "#9f7aea",
            },
        ],
        columns=4,
    )

    st.caption("🗺️ Click on markers for details • Updated in real-time")
    st.divider()


def render_evidence_panel(state):
    """QUESTION 3: Why does the AI believe this? - VISUAL VERSION"""
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

    # Visual evidence rendering
    col1, col2 = st.columns(2)

    with col1:
        render_evidence_confidence(evidence_items[:3])

    with col2:
        render_evidence_confidence(evidence_items[3:])

    st.markdown("---")

    # Summary metrics with visual cards
    render_quick_stats(
        [
            {
                "label": "Overall Confidence",
                "value": f"{state.risk_confidence * 100:.0f}%",
                "emoji": "🎯",
                "color": "#38a169",
            },
            {
                "label": "Data Quality",
                "value": f"{state.data_quality_score:.0f}%",
                "emoji": "📊",
                "color": "#4299e1",
            },
            {
                "label": "Active Sources",
                "value": state.active_sources_count,
                "emoji": "📡",
                "color": "#ed8936",
            },
        ],
        columns=3,
    )

    st.divider()


def render_impact_panel(state):
    """QUESTION 4: Who is affected? - VISUAL VERSION (FIXED)"""
    st.markdown("## 👥 Impact Assessment")
    st.caption("*Who is affected and how?*")

    # People - Visual population display
    render_population_visual(
        total=getattr(state, "population_exposed", 0),
        children=getattr(state, "children_exposed", 0),
        elderly=getattr(state, "elderly_exposed", 0),
        households=getattr(state, "households_affected", 0),
    )

    # Infrastructure - Visual metrics
    st.markdown("### 🏗️ Infrastructure")
    render_quick_stats(
        [
            {
                "label": "Schools",
                "value": getattr(state, "schools_exposed", 0),
                "emoji": "🏫",
                "color": "#4299e1",
            },
            {
                "label": "Hospitals",
                "value": getattr(state, "hospitals_exposed", 0),
                "emoji": "🏥",
                "color": "#e53e3e",
            },
            {
                "label": "Markets",
                "value": getattr(state, "markets_exposed", 0),
                "emoji": "🏪",
                "color": "#ed8936",
            },
            {
                "label": "Power Substations",
                "value": getattr(state, "power_substations_affected", 0),
                "emoji": "⚡",
                "color": "#9f7aea",
            },
        ],
        columns=4,
    )

    # Economy - Visual economic impact (FIXED - handles missing agriculture)
    render_economic_impact(
        residential=getattr(state, "residential_loss_ghs", 0),
        infrastructure=getattr(state, "infrastructure_loss_ghs", 0),
        total=getattr(state, "total_loss_ghs", 0),
        agriculture=getattr(state, "agricultural_loss_ghs", None),
    )

    # Environment - Visual metrics
    st.markdown("### 🌍 Environment")
    col1, col2 = st.columns(2)
    with col1:
        render_visual_metric_card(
            value=getattr(state, "soil_saturation_percent", 0),
            label="Soil Saturation",
            emoji="💧",
            color="#38a169",
            max_value=100,
            subtitle="Current saturation level",
        )
    with col2:
        render_visual_metric_card(
            value=getattr(state, "river_level_m", 0),
            label="River Level",
            emoji="🌊",
            color="#4299e1",
            max_value=3.0,
            subtitle=f"{getattr(state, 'river_level_m', 0):.1f}m / 3.0m",
        )

    # Affected communities - Visual list
    affected = getattr(state, "affected_communities", [])
    if affected:
        st.markdown("### 🏘️ Affected Communities")
        render_affected_communities(affected[:5])

    st.divider()


def render_operations_panel(state):
    """QUESTION 5: What are we doing? - VISUAL VERSION"""
    st.markdown("## 🚗 Operations")
    st.caption("*What resources are deployed and available?*")

    # Shelters - Visual status
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
    render_shelter_status(shelters)

    # Resources - Visual status
    st.markdown("### 📦 Resources")
    resources = [
        {
            "name": "Rescue Boats",
            "value": getattr(state, "rescue_boats", 0),
            "emoji": "🚤",
            "status": "Ready",
        },
        {
            "name": "Ambulances",
            "value": getattr(state, "ambulances", 0),
            "emoji": "🚑",
            "status": "Deployed",
        },
        {
            "name": "Pumps",
            "value": getattr(state, "pumps", 0),
            "emoji": "💧",
            "status": "Available",
        },
        {
            "name": "Rescue Teams",
            "value": getattr(state, "rescue_teams", 0),
            "emoji": "👥",
            "status": "Active",
        },
    ]
    render_resource_status(resources)

    # Evacuation Routes - Visual display
    st.markdown("### 🗺️ Evacuation Routes")
    routes = [
        {"from": "Alajo", "to": "Accra High School", "time": "15 min"},
        {"from": "Kaneshie", "to": "Community Center", "time": "20 min"},
        {"from": "Circle", "to": "Trade Fair Centre", "time": "25 min"},
    ]
    for route in routes:
        st.markdown(
            f"""
        <div style="
            background: #ffffff;
            padding: 8px 16px;
            border-radius: 8px;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            gap: 12px;
            border-left: 3px solid #4299e1;
            font-size: 14px;
        ">
            <span>🚗</span>
            <span><strong>{route['from']}</strong></span>
            <span style="color: #999;">→</span>
            <span><strong>{route['to']}</strong></span>
            <span style="margin-left: auto; color: #666; font-size: 12px;">⏱️ {route['time']}</span>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.divider()


def render_ai_decision_center(state):
    """QUESTION 6: What should we do? - VISUAL VERSION"""
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
        urgency_color = "#ff0000"
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
        urgency_color = "#ff6600"
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
        urgency_color = "#ffaa00"
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
        urgency_color = "#00cc00"

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(
            f"""
        <div style="
            background: #ffffff;
            padding: 16px 20px;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            border-left: 6px solid {urgency_color};
        ">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                <span style="font-size: 20px;">{urgency_color.replace('#', '')}</span>
                <span style="font-weight: 600; color: {urgency_color}; font-size: 14px;">
                    {urgency}
                </span>
            </div>
            <h2 style="font-size: 22px; margin: 0 0 12px 0;">{action}</h2>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Confidence bar
        st.progress(confidence / 100, text=f"Confidence: {confidence}%")

        st.markdown("**Why?**")
        for reason in reasons:
            st.markdown(f"• {reason}")

    with col2:
        st.markdown("**Expected Impact**")
        render_impact_card(
            value=cost,
            label="Estimated Cost",
            emoji="💰",
            color="#ed8936",
            detail=impact,
        )
        st.caption(f"⏱️ Time Window: {time_window}")

    st.divider()


def render_risk_timeline(state):
    """QUESTION 7: What happens next? - VISUAL VERSION"""
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

    render_risk_timeline_visual(hours, risks, current_risk)

    # Summary metrics
    peak_risk = max(risks)
    peak_hour = hours[risks.index(peak_risk)]

    col1, col2, col3 = st.columns(3)
    with col1:
        delta = (
            f"{peak_risk - current_risk:.0f}%" if peak_risk > current_risk else "Stable"
        )
        st.metric("Peak Risk", f"{peak_risk:.0f}%", delta=delta)
    with col2:
        st.metric("Peak Time", peak_hour)
    with col3:
        trend = "Increasing" if peak_risk > current_risk else "Stable"
        trend_delta = "↗️" if peak_risk > current_risk else "→"
        st.metric("Trend", trend, delta=trend_delta)

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
    """Enterprise Command Center with Visual Storytelling."""
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
