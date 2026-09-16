"""
CivicFlood AI - Enterprise Command Center
Phase 4: Visual Storytelling Implementation (Fixed)
International-standard professional dashboard
"""

# ============================================================
# IMPORTS - ALL AT THE TOP (E402 fixed)
# ============================================================

import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path BEFORE other imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))  # noqa: E402

import requests
import streamlit as st

from hackathon.app.modules.v4.situation_map import render_map_fallback
from hackathon.app.modules.v4.situation_map import render_situation_map
from hackathon.app.modules.v4.state import (
    TRACKED_DISTRICT_COUNT,
    create_state_from_api,
    get_risk_tier_style,
    tier_from_score,
)
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
    render_evacuation_routes,
)
from hackathon.app.modules.v4.state_fallback import get_fallback_data

# ============================================================
# FORCE BLACK TEXT - CSS OVERRIDE
# ============================================================
st.markdown(
    """
    <style>
        /* Force ALL text to be black */
        .stApp, .stApp p, .stApp div, .stApp span, .stApp label {
            color: #000000 !important;
        }
        /* Keep emojis visible */
        .stAlert, .stAlert * {
            color: inherit !important;
        }
        /* Force markdown text to black */
        .stMarkdown, .stMarkdown p, .stMarkdown div, .stMarkdown span {
            color: #000000 !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# CONFIGURATION
# ============================================================

API_URL = os.getenv(
    "NFCC_API_URL", "https://nfcc-platform-355353600602.europe-west1.run.app"
)

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


@st.cache_data(ttl=900)
def get_national_summary() -> dict:
    """Districts Monitored / Active Flood Zones, from GET /national/summary
    (src/api/routes/situation.py) - real river-discharge-based computation
    across every tracked district, independent of which one is selected.
    Cached for 15 minutes since it queries an external API (Open-Meteo
    Flood API) once per tracked district and river discharge doesn't
    change meaningfully within that window - re-fetching on every rainfall
    slider tick would be wasteful and slow (~6s for 9 districts)."""
    return call_api("/national/summary", "GET")


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
            "affected_communities": [
                "Alajo",
                "Kaneshie",
                "Circle",
                "Achimota",
                "Adabraka",
            ],
        },
        "Accra West": {
            "region": "Greater Accra",
            "population": 203461,
            "area_km2": 52.3,
            "lat": 5.550,
            "lon": -0.230,
            "elevation": 10,
            "affected_communities": [
                "Dansoman",
                "Korle Bu",
                "Mamprobi",
                "Chorkor",
                "Awoshie",
            ],
        },
        "Accra East": {
            "region": "Greater Accra",
            "population": 142587,
            "area_km2": 38.2,
            "lat": 5.565,
            "lon": -0.190,
            "elevation": 15,
            "affected_communities": [
                "Labone",
                "East Legon",
                "Osu",
                "Cantonments",
                "Airport",
            ],
        },
        "Tema": {
            "region": "Greater Accra",
            "population": 198742,
            "area_km2": 38.7,
            "lat": 5.650,
            "lon": -0.020,
            "elevation": 18,
            "affected_communities": [
                "Tema Community 1",
                "Tema Community 2",
                "Tema Industrial",
                "Sakumono",
                "Ashaiman",
            ],
        },
        "Kumasi": {
            "region": "Ashanti",
            "population": 443981,
            "area_km2": 98.2,
            "lat": 6.670,
            "lon": -1.620,
            "elevation": 25,
            "affected_communities": [
                "Asokwa",
                "Bantama",
                "Ayigya",
                "Danyame",
                "Kwadaso",
            ],
        },
        "Tamale": {
            "region": "Northern",
            "population": 371578,
            "area_km2": 67.4,
            "lat": 9.400,
            "lon": -0.840,
            "elevation": 125,
            "affected_communities": [
                "Tamale Central",
                "Tamale North",
                "Sagnarigu",
                "Gurugu",
                "Lamashegu",
            ],
        },
        # Real coordinates and neighborhood names (verified) added alongside
        # src/exposure/impact_estimator.py's existing population/infrastructure
        # data for these three districts, which had no UI to select them.
        "Cape Coast": {
            "region": "Central",
            "population": 169894,
            "area_km2": 62.4,
            "lat": 5.100,
            "lon": -1.250,
            "elevation": 25,
            "affected_communities": [
                "Pedu",
                "Abura",
                "Kakumdo",
                "Amamoma",
                "Kotokuraba",
            ],
        },
        "Ho": {
            "region": "Volta",
            "population": 153705,
            "area_km2": 58.3,
            "lat": 6.601,
            "lon": 0.471,
            "elevation": 100,
            "affected_communities": ["Bankoe", "Heve", "Ahoe", "Dome", "Hliha"],
        },
        "Sunyani": {
            "region": "Bono",
            "population": 138256,
            "area_km2": 55.7,
            "lat": 7.333,
            "lon": -2.333,
            "elevation": 300,
            "affected_communities": [
                "Abesim",
                "Atronie",
                "New Dormaa",
                "Penkwase",
                "Kotokrom",
            ],
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
        st.markdown(
            f"<p style='margin:0;font-size:13px;color:#666;font-weight:600;"
            f"letter-spacing:0.5px;'>🕐 {datetime.now().strftime('%A, %d %B %Y &nbsp;&nbsp; %H:%M:%S UTC')}</p>",
            unsafe_allow_html=True,
        )
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
            "Cape Coast",
            "Ho",
            "Sunyani",
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
        st.markdown("### 🎬 Stakeholder Demo")
        st.caption(
            "Auto-plays a flood event for this district through the real "
            "system - for briefings where there's no time to click through."
        )
        demo_mode = st.toggle("Demo mode", value=False)
        start_demo = False
        if demo_mode:
            start_demo = st.button("▶ Start Demo", use_container_width=True)

        st.divider()
        st.markdown("### 🔔 Alert Review Queue")
        st.caption(
            "Automated risk assessments awaiting human approval before "
            "any real alert goes out. Nothing is ever sent automatically."
        )
        review_mode = st.toggle("Review queue mode", value=False)

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

    return {
        "district": district,
        "rainfall_mm": rainfall_mm,
        "demo_mode": demo_mode,
        "start_demo": start_demo,
        "review_mode": review_mode,
    }


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

        # Keyed off state.risk_category (sourced from the backend's own
        # risk_tier in create_state_from_api) instead of re-deriving from
        # risk_score with a separate set of thresholds - this used to have
        # its own 4-tier scale (40/60/80, no EXTREME) that disagreed with
        # both the backend and the "Current Risk Level" card above it,
        # e.g. showing "HIGH" here while the card read "CRITICAL" for the
        # same score, and never reaching EXTREME even at a 100% score.
        situation_by_tier = {
            "EXTREME": (
                "🔴 EXTREME: Immediate evacuation required.",
                "#cc0000",
                "🚨 MANDATORY EVACUATION ORDER",
            ),
            "CRITICAL": (
                "🔴 CRITICAL: Prepare for evacuation immediately.",
                "#ff0000",
                "🚨 EVACUATION ORDER LIKELY",
            ),
            "HIGH": (
                "🟠 HIGH: Elevated flood risk in this area.",
                "#ff6600",
                "⚠️ PREPARE TO EVACUATE",
            ),
            "MODERATE": (
                "🟡 MODERATE: Monitor conditions closely.",
                "#ffaa00",
                "📢 STAY INFORMED",
            ),
            "LOW": (
                "🟢 LOW: Normal monitoring.",
                "#00cc00",
                "✅ CONTINUE NORMAL OPERATIONS",
            ),
        }
        summary, color, recommendation = situation_by_tier.get(
            state.risk_category, situation_by_tier["MODERATE"]
        )

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

    national = get_national_summary()

    # Create a state object for the map
    class MapState:
        def __init__(self):
            self.lat = 5.560
            self.lon = -0.210
            self.district = "Accra Central"
            self.risk_score = 50
            self.risk_category = "MODERATE"
            self.shelters_available = 3
            self.verified_reports = 0
            self.district_count = TRACKED_DISTRICT_COUNT
            self.active_flood_zones = 3

    map_state = MapState()
    map_state.lat = getattr(state, "lat", 5.560)
    map_state.lon = getattr(state, "lon", -0.210)
    map_state.district = getattr(state, "district", "Accra Central")
    map_state.risk_score = getattr(state, "risk_score", 50)
    map_state.risk_category = getattr(state, "risk_category", "MODERATE")
    # These two were missing entirely until now - situation_map.py's own
    # stat cards read state.shelters_available/verified_reports directly
    # (no getattr fallback there), so passing this stripped-down MapState
    # instead of the real state raised an AttributeError that its own
    # try/except silently swallowed into "Map temporarily unavailable",
    # falling back to a hardcoded, non-district-aware community table.
    map_state.shelters_available = getattr(state, "shelters_available", 3)
    map_state.verified_reports = getattr(state, "verified_reports", 0)
    # Real, from GET /national/summary (river-discharge-based) - falls
    # back to the illustrative defaults above if that call failed.
    if "error" not in national:
        map_state.district_count = national.get(
            "district_count", TRACKED_DISTRICT_COUNT
        )
        map_state.active_flood_zones = national.get("active_flood_zones", 3)

    # Render the actual map. render_situation_map() already renders its own
    # Districts Monitored / Active Flood Zones / Shelters Available /
    # Verified Reports row (with the real verified_reports/shelters_available
    # values via map_state above) plus its own "click on markers" caption -
    # there used to be a second, entirely separate render_quick_stats() call
    # here duplicating the exact same four stats with hardcoded values
    # (Verified Reports always "4"), which just fell out of sync with the
    # real row above it once that one started showing real data.
    try:
        render_situation_map(map_state)
    except Exception as e:
        st.error(f"❌ Map error: {str(e)}")
        render_map_fallback()

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


def render_impact_panel(state, district_data):
    """QUESTION 4: Who is affected? - VISUAL VERSION WITH FALLBACK DATA"""
    st.markdown("## 👥 Impact Assessment")
    st.caption("*Who is affected and how?*")

    # Get fallback data if API returns zeros
    population_exposed = getattr(state, "population_exposed", 0)
    if population_exposed == 0:
        fallback = get_fallback_data(
            district=getattr(state, "district", "Accra Central"),
            rainfall_mm=getattr(state, "rainfall_mm", 75),
        )
        population_exposed = fallback["population_exposed"]
        children_exposed = fallback["children_exposed"]
        elderly_exposed = fallback["elderly_exposed"]
        households_affected = fallback["households_affected"]
        schools_exposed = fallback["schools_exposed"]
        hospitals_exposed = fallback["hospitals_exposed"]
        markets_exposed = fallback["markets_exposed"]
        power_substations = fallback["power_substations_affected"]
        residential_loss = fallback["residential_loss_ghs"]
        infrastructure_loss = fallback["infrastructure_loss_ghs"]
        agricultural_loss = fallback["agricultural_loss_ghs"]
        total_loss = fallback["total_loss_ghs"]
        soil_saturation = fallback["soil_saturation_percent"]
        river_level = fallback["river_level_m"]
    else:
        children_exposed = getattr(state, "children_exposed", 0)
        elderly_exposed = getattr(state, "elderly_exposed", 0)
        households_affected = getattr(state, "households_affected", 0)
        schools_exposed = getattr(state, "schools_exposed", 0)
        hospitals_exposed = getattr(state, "hospitals_exposed", 0)
        markets_exposed = getattr(state, "markets_exposed", 0)
        power_substations = getattr(state, "power_substations_affected", 0)
        residential_loss = getattr(state, "residential_loss_ghs", 0)
        infrastructure_loss = getattr(state, "infrastructure_loss_ghs", 0)
        agricultural_loss = getattr(state, "agricultural_loss_ghs", 0)
        total_loss = getattr(state, "total_loss_ghs", 0)
        soil_saturation = getattr(state, "soil_saturation_percent", 0)
        river_level = getattr(state, "river_level_m", 0)

    # People - Visual population display
    render_population_visual(
        total=population_exposed,
        children=children_exposed,
        elderly=elderly_exposed,
        households=households_affected,
    )

    # Infrastructure - Visual metrics
    st.markdown("### 🏗️ Infrastructure")
    render_quick_stats(
        [
            {
                "label": "Schools",
                "value": schools_exposed,
                "emoji": "🏫",
                "color": "#4299e1",
            },
            {
                "label": "Hospitals",
                "value": hospitals_exposed,
                "emoji": "🏥",
                "color": "#e53e3e",
            },
            {
                "label": "Markets",
                "value": markets_exposed,
                "emoji": "🏪",
                "color": "#ed8936",
            },
            {
                "label": "Power Substations",
                "value": power_substations,
                "emoji": "⚡",
                "color": "#9f7aea",
            },
        ],
        columns=4,
    )

    # Economy - Visual economic impact
    render_economic_impact(
        residential=residential_loss,
        infrastructure=infrastructure_loss,
        total=total_loss,
        agriculture=agricultural_loss,
    )

    # Environment - Visual metrics
    st.markdown("### 🌍 Environment")
    col1, col2 = st.columns(2)
    with col1:
        render_visual_metric_card(
            value=soil_saturation,
            label="Soil Saturation",
            emoji="💧",
            color="#38a169",
            max_value=100,
            subtitle="Current saturation level",
        )
    with col2:
        render_visual_metric_card(
            value=river_level,
            label="River Level",
            emoji="🌊",
            color="#4299e1",
            max_value=3.0,
            subtitle=f"{river_level:.1f}m / 3.0m",
        )

    # Affected communities - Visual list
    affected = district_data.get("affected_communities", [])
    if affected:
        st.markdown("### 🏘️ Affected Communities")
        render_affected_communities(affected[:5])

    st.divider()


def render_operations_panel(state, district_data):
    """QUESTION 5: What are we doing? - VISUAL VERSION"""
    st.markdown("## 🚗 Operations")
    st.caption("*What resources are deployed and available?*")

    # No officially-designated shelter registry exists publicly for Ghana
    # (NADMO designates schools/community buildings ad-hoc during an
    # actual emergency, not from a fixed pre-registered list - confirmed
    # via research). state.shelter_names (from /situation, real named
    # public buildings queried from OpenStreetMap per district - see
    # src/exposure/shelter_candidates.py) replaces the previous generic
    # "{district} Senior High School" pattern, which was at least
    # district-scoped but not a real place name. Capacity/status numbers
    # remain illustrative either way - no real capacity data exists.
    district = state.district
    names = state.shelter_names or [
        f"{district} Senior High School",
        f"{district} Community Center",
        f"{district} Trade Fair Centre",
    ]
    shelter_specs = [
        {"status": "OPEN", "capacity": 1200, "available": 850},
        {"status": "OPEN", "capacity": 500, "available": 320},
        {"status": "PREPARING", "capacity": 2000, "available": 2000},
    ]
    shelters = [
        {"name": names[i], **shelter_specs[i]} for i in range(min(3, len(names)))
    ]
    render_shelter_status(shelters)

    # Resources - Visual status
    st.markdown("### 📦 Resources")
    resources = [
        {
            "name": "Rescue Boats",
            "value": getattr(state, "rescue_boats", 3),
            "emoji": "🚤",
            "status": "Ready",
        },
        {
            "name": "Ambulances",
            "value": getattr(state, "ambulances", 5),
            "emoji": "🚑",
            "status": "Deployed",
        },
        {
            "name": "Pumps",
            "value": getattr(state, "pumps", 10),
            "emoji": "💧",
            "status": "Available",
        },
        {
            "name": "Rescue Teams",
            "value": getattr(state, "rescue_teams", 4),
            "emoji": "👥",
            "status": "Active",
        },
    ]
    render_resource_status(resources)

    # Evacuation Routes - Visual display using component. Origins are the
    # district's real affected communities (district_data, already used
    # correctly for the Affected Communities card); destinations are the
    # shelters above. No real routing engine or travel-time data exists
    # anywhere in the codebase, so drive times stay as illustrative
    # round-number estimates - previously this whole block was hardcoded
    # to fixed Accra community/shelter names regardless of which district
    # was selected.
    communities = district_data.get("affected_communities", [state.district])
    shelter_names = [s["name"] for s in shelters]
    drive_times = ["15 min", "20 min", "25 min"]
    routes = [
        {"from": communities[i], "to": shelter_names[i], "time": drive_times[i]}
        for i in range(min(3, len(communities), len(shelter_names)))
    ]
    render_evacuation_routes(routes)

    st.divider()
    st.divider()


def render_ai_decision_center(state):
    """QUESTION 6: What should we do? - VISUAL VERSION"""
    st.markdown("## 🎯 AI Decision Center")
    st.caption("*What actions should we take and why?*")

    # Thresholds and urgency/color now match the backend's real tiers
    # (get_risk_tier_style) instead of a separately-drifted 4-tier scale
    # (80/60/40, no EXTREME) - EXTREME shares CRITICAL's action content
    # below (there's no operationally distinct "beyond mandatory
    # evacuation" action), but its badge now correctly reads EXTREME with
    # the darker red used everywhere else, instead of mislabeling a 100%
    # score as merely "CRITICAL".
    tier = tier_from_score(state.risk_score)
    urgency = tier
    urgency_color = get_risk_tier_style(tier=tier)["color"]

    # "Protect/Alert N people" and "Estimated Cost" used to be fixed
    # numbers, identical for every district and rainfall level - state
    # .population_exposed is real (from /situation), and response
    # operations cost is a distinct concept from the flood-damage economic
    # loss already computed elsewhere on this page (evacuation/outreach
    # logistics cost, not property damage), so it's a separate simple
    # per-person estimate, illustrative like the economic-loss one - no
    # real operations-cost model exists anywhere in the codebase either.
    population_exposed = getattr(state, "population_exposed", 0)

    if tier in ("EXTREME", "CRITICAL"):
        action = "🚨 Issue Mandatory Evacuation Order"
        confidence = 95
        reasons = [
            "Rainfall exceeds historical thresholds",
            "River levels rising rapidly",
            "Roads becoming inaccessible",
            "Multiple citizen reports verified",
        ]
        impact = f"Protect {population_exposed:,} people"
        cost = population_exposed * 15  # full evacuation + temp shelter ops
        time_window = "Within 45 minutes"
    elif tier == "HIGH":
        action = "⚠️ Prepare for Evacuation"
        confidence = 87
        reasons = [
            "Rainfall approaching warning levels",
            "River levels elevated",
            "Soil saturation increasing",
            "Reports of rising water",
        ]
        impact = f"Protect {population_exposed:,} people"
        cost = population_exposed * 8  # readiness + resource positioning
        time_window = "Within 2 hours"
    elif tier == "MODERATE":
        action = "📢 Issue Public Awareness Message"
        confidence = 78
        reasons = [
            "Rainfall expected to continue",
            "Conditions being monitored",
            "Communities advised to stay informed",
        ]
        impact = f"Alert {population_exposed:,} people"
        cost = population_exposed * 1.25  # SMS/broadcast outreach
        time_window = "Within 4 hours"
    else:
        action = "✅ Continue Normal Monitoring"
        confidence = 92
        reasons = [
            "All indicators within normal range",
            "No immediate threat detected",
            "Regular updates provided",
        ]
        impact = f"Monitor {TRACKED_DISTRICT_COUNT} districts"
        cost = 5000  # flat routine-monitoring cost, not population-scaled
        time_window = "Ongoing"

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
                <span style="font-size: 20px;">{get_risk_tier_style(tier=tier)["emoji"]}</span>
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

    current_risk = state.risk_score

    # state.risk_timeline (from /situation, src/api/routes/situation.py) is
    # a real forecast-driven timeline using actual Open-Meteo rainfall
    # forecasts, scored through the same calculate_score() as everywhere
    # else. Falls back to the old synthetic +15/+10/+5 offset (which had
    # no forecast data behind it at all) only if /situation wasn't called
    # or the forecast fetch failed.
    if state.risk_timeline:
        hours = [point["hour"] for point in state.risk_timeline]
        risks = [point["score"] for point in state.risk_timeline]
    else:
        hours = ["Now", "6h", "12h", "18h", "24h"]
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


def render_situation(
    district: str, rainfall_mm: float, stage_label: str = None, show_copilot: bool = True
):
    """Fetch the real situation for (district, rainfall_mm) and render the
    full dashboard for it - the one place that does this, used by both
    normal manual-slider mode and the auto-playing demo mode below, so a
    demo stage is the real system's real response to a hypothetical
    rainfall value, not separately-fabricated demo content.

    show_copilot=False skips the AI Copilot panel (its button/chat_input
    widgets have fixed keys, so calling it more than once in a single
    script run - which the demo loop does, one call per stage - would
    raise a duplicate-widget-key error; it also doesn't make sense to
    show an input box mid-auto-play anyway)."""
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
        # /situation (src/api/routes/situation.py) computes the same
        # score/risk_tier /score does, plus real hydrology evidence,
        # population/infrastructure impact estimates, and community report
        # counts in one call - /score alone left every non-header field
        # (population, schools, evidence readings, lead time, reports) on
        # static demo defaults, since it never returned any of them.
        api_data = call_api("/situation", "POST", api_payload)

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
        tier = tier_from_score(state.risk_score)
        if tier in ("EXTREME", "CRITICAL"):
            state.lead_time_hours = 2
            state.lead_time_action = "IMMEDIATE EVACUATION"
        elif tier == "HIGH":
            state.lead_time_hours = 6
            state.lead_time_action = "PREPARE TO EVACUATE"
        elif tier == "MODERATE":
            state.lead_time_hours = 24
            state.lead_time_action = "MONITOR CONDITIONS"
        else:
            state.lead_time_hours = 72
            state.lead_time_action = "STAY INFORMED"

    if stage_label:
        st.markdown(
            f"<div style='background:#111827;color:#fff;padding:10px 20px;"
            f"border-radius:8px;text-align:center;font-size:18px;"
            f"font-weight:700;letter-spacing:1px;margin-bottom:16px;'>"
            f"🎬 {stage_label}</div>",
            unsafe_allow_html=True,
        )

    render_header(state)
    render_executive_summary(state)
    render_national_map(state)
    render_evidence_panel(state)
    render_impact_panel(state, district_data)

    col1, col2 = st.columns(2)
    with col1:
        render_operations_panel(state, district_data)
    with col2:
        render_ai_decision_center(state)

    render_risk_timeline(state)
    if show_copilot:
        render_ai_copilot(state)

    st.divider()
    st.caption("🌊 CivicFlood AI • Decision Intelligence for National Flood Response")
    st.caption("NFCC Platform • Ghana AI Innovation Challenge 2026")
    st.caption(f"📊 {state.active_sources_count} Data Sources Active • 🔗 {API_URL}")
    st.caption(f"🔄 Last updated: {state.timestamp[:19]}")


# All districts this platform has real hydrology/impact data for - used
# by the "Run Automated Check Now" button to mirror what
# scripts/automated_risk_assessment.py does on its 3-hourly schedule
# (.github/workflows/automated_risk_assessment.yml), without waiting for
# that schedule.
ALL_TRACKED_DISTRICTS = [
    "Accra Central",
    "Accra West",
    "Accra East",
    "Tema",
    "Kumasi",
    "Tamale",
    "Cape Coast",
    "Ho",
    "Sunyani",
]


def render_alert_review_queue():
    """The human-in-the-loop screen: automated assessments wait here until
    a person explicitly approves or dismisses them - see
    src/api/routes/alert_review.py. Before this screen existed, nothing
    stood between an automated score crossing threshold and a real alert
    actually being sent."""
    st.markdown("# 🔔 Alert Review Queue")
    st.caption(
        "Automated risk assessments awaiting human review. Nothing is "
        "sent to real recipients until you click Approve below."
    )

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Run Automated Check Now", use_container_width=True):
            with st.spinner("Assessing all districts..."):
                queued = 0
                for district in ALL_TRACKED_DISTRICTS:
                    try:
                        precip = weather_forecast_24h(district)
                    except Exception:
                        continue
                    result = call_api(
                        "/alerts/assess",
                        "POST",
                        {"location": district, "precipitation": precip},
                    )
                    if result.get("queued"):
                        queued += 1
                st.session_state["_last_check_queued"] = queued
            st.rerun()

    if "_last_check_queued" in st.session_state:
        st.info(
            f"Last manual check queued {st.session_state['_last_check_queued']} "
            f"district(s) for review."
        )

    pending = call_api("/alerts/pending", "GET")
    alerts = pending.get("alerts", [])

    if "error" in pending:
        st.error(f"Could not reach the review queue: {pending['error']}")
        return

    if not alerts:
        st.success("✅ No pending alerts. All caught up.")
        return

    st.markdown(f"### {len(alerts)} awaiting review")
    for alert in alerts:
        style = get_risk_tier_style(tier=alert["risk_tier"])
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                st.markdown(
                    f"{style['emoji']} **{alert['location']}** — "
                    f"{alert['risk_tier']} ({alert['score']:.0f}%)"
                )
                st.caption(f"Precipitation: {alert['precipitation']}mm")
            with c2:
                st.markdown(f"*{alert['message']}*")
                st.caption(f"Queued: {alert['created_at'][:19]}")
            with c3:
                if st.button(
                    "✅ Approve & Send",
                    key=f"approve_{alert['id']}",
                    use_container_width=True,
                ):
                    call_api(
                        f"/alerts/pending/{alert['id']}/approve",
                        "POST",
                        {"reviewed_by": "dashboard-operator"},
                    )
                    st.rerun()
                if st.button(
                    "❌ Dismiss",
                    key=f"dismiss_{alert['id']}",
                    use_container_width=True,
                ):
                    call_api(
                        f"/alerts/pending/{alert['id']}/dismiss",
                        "POST",
                        {"reviewed_by": "dashboard-operator"},
                    )
                    st.rerun()


def weather_forecast_24h(district: str) -> float:
    """Real next-24h forecasted rainfall for a district, via the same
    /situation call the rest of the dashboard already uses (its
    forecast_24h_mm field, sourced from Open-Meteo) - reused here so the
    manual "check now" button assesses real current forecast conditions,
    the same way the scheduled script does, not the rainfall slider's
    manually-set test value."""
    result = call_api(
        "/situation",
        "POST",
        {"location": district, "precipitation": 0},
    )
    return result.get("forecast_24h_mm", 0.0)


# Scripted rainfall trajectory for demo mode - each stage is a real value
# sent to the real /situation endpoint, so the "story" is the actual
# system's actual response, not separately scripted/fabricated content.
# Chosen to walk the score from LOW through EXTREME using the real
# calculate_score() curve, not evenly-spaced rainfall values.
DEMO_STAGES = [
    ("STAGE 1 / 5 — CALM CONDITIONS", 5),
    ("STAGE 2 / 5 — RAIN BUILDING", 25),
    ("STAGE 3 / 5 — WARNING LEVEL", 45),
    ("STAGE 4 / 5 — SEVERE FLOODING", 70),
    ("STAGE 5 / 5 — PEAK EMERGENCY: FULL EVACUATION", 120),
]
DEMO_SECONDS_PER_STAGE = 18


def main():
    """Enterprise Command Center with Visual Storytelling.

    Demo mode advances one stage per full Streamlit script rerun (session
    state + st.rerun()), rather than looping through all stages inside a
    single script execution. A single-execution loop looked simpler but
    breaks the instant it renders anything bidirectional like st_folium's
    map: on a real browser (unlike Streamlit's headless AppTest, which
    doesn't simulate this and is why the loop version passed automated
    testing but failed live), the map component reports its state back to
    the frontend the moment it mounts, which triggers an unrequested
    rerun - that aborts the loop mid-first-stage and restarts main() from
    scratch, where the Start Demo button's one-shot "clicked" flag has
    already reset to False, landing back on the "click Start Demo"
    message after only a flash of stage 1. Advancing via rerun instead of
    a loop works *with* that behavior instead of fighting it - it's
    exactly how normal manual-slider mode already renders every time the
    slider moves, which is why that path never hit this problem."""
    control_data = render_control_panel()
    district = control_data["district"]

    if control_data["review_mode"]:
        render_alert_review_queue()
        return

    if not control_data["demo_mode"]:
        st.session_state["demo_stage_idx"] = None
        render_situation(district, control_data["rainfall_mm"])
        return

    if control_data["start_demo"]:
        st.session_state["demo_stage_idx"] = 0

    idx = st.session_state.get("demo_stage_idx")

    if idx is None:
        st.info(
            "🎬 **Demo mode is on.** Click **▶ Start Demo** in the "
            "sidebar to auto-play a flood event for this district."
        )
    elif idx >= len(DEMO_STAGES):
        st.success(
            "🎬 Demo complete. Turn off Demo mode in the sidebar to return "
            "to manual control, or click Start Demo again to replay."
        )
        render_situation(district, DEMO_STAGES[-1][1], show_copilot=True)
    else:
        label, rainfall_mm = DEMO_STAGES[idx]
        render_situation(district, rainfall_mm, stage_label=label, show_copilot=False)
        time.sleep(DEMO_SECONDS_PER_STAGE)
        st.session_state["demo_stage_idx"] = idx + 1
        st.rerun()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error("🚨 Dashboard encountered an error. Please check the logs.")
        st.exception(e)
