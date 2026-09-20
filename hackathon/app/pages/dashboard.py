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
from typing import Optional

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
# DARK THEME - Finelo-inspired (near-black background, bright lime-green
# accent, bold light text). Matches .streamlit/config.toml's theme
# section (which handles native widgets - sliders, buttons, inputs) and
# hackathon/app/modules/v4/visual_components.py's Theme class (which
# handles the custom HTML cards) - all three should be edited together
# if this palette ever changes.
# ============================================================
st.markdown(
    """
    <style>
        .stApp {
            background-color: #0a0a0a;
            color: #F5F5F5;
        }
        .stApp p, .stApp span, .stApp label {
            color: #F5F5F5;
        }
        .stMarkdown, .stMarkdown p, .stMarkdown div, .stMarkdown span {
            color: #F5F5F5;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #F5F5F5 !important;
            font-weight: 700 !important;
        }
        /* Keep emojis and alert-box tinted text as Streamlit intends */
        .stAlert, .stAlert * {
            color: inherit !important;
        }
        /* Rounded, bold, Finelo-style buttons. The default (secondary)
           button variant is styled explicitly here, not left to
           Streamlit's own theme defaults - on this Streamlit version
           those can render as a light/white button, which combined with
           our global light text color made the label invisible (the AI
           Copilot's four suggested-question buttons). */
        .stButton > button, .stChatInput button {
            border-radius: 10px !important;
            font-weight: 600 !important;
        }
        .stButton > button {
            background-color: #161616 !important;
            color: #F5F5F5 !important;
            border: 1px solid #2A2A2A !important;
        }
        .stButton > button:hover {
            border-color: #8CD867 !important;
            color: #8CD867 !important;
        }
        .stButton > button[kind="primary"] {
            background-color: #8CD867 !important;
            color: #0a0a0a !important;
            border: none !important;
        }
        .stButton > button[kind="primary"]:hover {
            color: #0a0a0a !important;
            opacity: 0.9;
        }
        /* Chat input and any other text inputs - same white-on-white
           risk as the buttons above if left to native styling. */
        .stChatInput textarea, .stChatInput input,
        .stTextInput input, .stTextArea textarea,
        .stNumberInput input {
            background-color: #161616 !important;
            color: #F5F5F5 !important;
            border: 1px solid #2A2A2A !important;
        }
        .stChatInput, .stChatInput > div {
            background-color: #161616 !important;
        }
        /* Sidebar and metric containers get the same dark card look as
           the custom HTML components in visual_components.py */
        section[data-testid="stSidebar"] {
            background-color: #121212;
        }
        div[data-testid="stMetric"] {
            background-color: #161616;
            border: 1px solid #2A2A2A;
            border-radius: 12px;
            padding: 12px 16px;
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
# Sent as the X-API-Key header (src/api/auth.py's fixed header name -
# settings.API_KEY_HEADER on the backend) on every request below. Set
# via this app's Streamlit Cloud "Secrets" panel, matching the same
# nfcc-api-key value already bound to Cloud Run as API_KEY. Harmless to
# send even before the backend enforces it - verify_api_key() only
# checks the header once settings.API_KEY is configured, and sending an
# unrecognized header to an endpoint that ignores it is a no-op.
API_KEY = os.getenv("NFCC_API_KEY", "")

st.set_page_config(
    page_title="CivicFlood AI - National Emergency Operations Center",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# API FUNCTIONS
# ============================================================


def _auth_headers() -> dict:
    return {"X-API-Key": API_KEY} if API_KEY else {}


def call_api(
    endpoint: str, method: str = "GET", data: dict = None, timeout: int = 30
) -> dict:
    """Call the NFCC API with robust error handling."""
    url = f"{API_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=timeout, headers=_auth_headers())
        elif method == "POST":
            response = requests.post(url, json=data, timeout=timeout, headers=_auth_headers())
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


def fetch_cap_xml(alert_id: int) -> Optional[str]:
    """Real OASIS CAP v1.2 XML for one review-queue alert (see
    src/api/routes/cap_export.py) - a plain XML body, not JSON, so this
    bypasses call_api's response.json() and just returns the raw text (or
    None on any failure, so a broken export never crashes the queue view)."""
    try:
        response = requests.get(
            f"{API_URL}/alerts/pending/{alert_id}/cap.xml", timeout=15, headers=_auth_headers()
        )
        return response.text if response.status_code == 200 else None
    except requests.exceptions.RequestException:
        return None


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


@st.cache_data(ttl=300)
def get_data_source_health() -> dict:
    """Real per-source status from GET /v1/health/data-sources
    (src/api/v1/health.py) - Earth Engine, DAHITI, Open-Meteo, Ghana
    River Gauges, community reports DB. Cached for 5 minutes: this makes
    one live network call (to Open-Meteo) itself, and the sidebar
    re-renders on every widget interaction (slider drag, district
    change) - without caching, every one of those would re-trigger that
    live call for a status view that doesn't need per-second freshness."""
    return call_api("/v1/health/data-sources", "GET")


# Previously a hardcoded list of 6 sources, all unconditionally shown as
# green regardless of anything real - "NASA SMAP" had no backing code
# anywhere in this repo, and "Ghana River Gauges" was marked healthy
# despite src/hydrology/river_gauge_api.py never having had a real API
# key wired in at all. Same fabrication pattern already fixed in the AI
# Decision Center, just in the sidebar instead.
_STATUS_BADGE = {
    "connected": "🟢",
    "configured": "🟢",
    "not_configured": "🟡",
    "unavailable": "🔴",
}


def render_data_source_status() -> None:
    health = get_data_source_health()
    if "error" in health:
        st.caption(f"⚠️ Could not reach health endpoint: {health['error']}")
        return

    for source in health.get("sources", []):
        badge = _STATUS_BADGE.get(source["status"], "⚪")
        st.markdown(f"{badge} {source['name']}")
        st.caption(source["detail"])

    checked_at = health.get("checked_at", "")
    if checked_at:
        st.caption(f"Checked: {checked_at[:19]}")


# Single source of truth for tier -> (summary text, color, recommendation),
# matching the backend's real 5-tier system. Used by both the full
# dashboard's AI Situation Summary and the compact broadcast view - was
# previously defined only inline inside render_executive_summary, which
# meant the broadcast view (below) would have needed its own duplicate
# copy to show the same message.
SITUATION_BY_TIER = {
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
        # Previously always said "API Connected" regardless of
        # state.api_connected, just swapping the emoji - so a real
        # failure (e.g. a missing/incorrect NFCC_API_KEY secret) still
        # visually claimed to be connected next to a warning triangle.
        if state.api_connected:
            st.markdown("✅ **API Connected**")
        else:
            st.markdown("⚠️ **API Unavailable - showing fallback data**")
        st.code(API_URL, language="text")

    if not state.api_connected:
        st.error(
            "The dashboard could not reach the live platform API for this "
            "request, so the figures below are illustrative fallback "
            "values, not real current data. If this persists, check that "
            "NFCC_API_KEY is set correctly in this app's Streamlit Cloud "
            "secrets (Settings → Secrets) and matches the platform's "
            "nfcc-api-key.",
            icon="\U0001F6A8",
        )
        # Diagnostic for exactly this failure mode: two independent
        # careful re-copies of the secret still failed with "Invalid API
        # key" (not "Missing header"), meaning Streamlit IS sending a
        # key - it just doesn't match. A plain character count in a text
        # editor won't reveal a stray invisible character (trailing
        # newline, non-breaking space, etc.), so this shows the raw
        # repr() of the first/last 2 characters plus the length - repr()
        # prints hidden whitespace as visible escape sequences (\n, \xa0,
        # ...) instead of silently rendering it as blank space. Never
        # logs the full key. Remove once the mismatch is resolved.
        with st.expander("🔧 Debug: what key is this app actually sending?"):
            st.write(f"Length: {len(API_KEY)} (should be 24)")
            if API_KEY:
                st.code(
                    f"starts: {API_KEY[:2]!r}  ends: {API_KEY[-2:]!r}  "
                    f"has_whitespace: {API_KEY != API_KEY.strip()}",
                    language="text",
                )
            else:
                st.write("NFCC_API_KEY is empty or not set at all in this app's environment.")

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
        render_data_source_status()

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
                    # Real signal, not decorative: degraded (missing
                    # high-trust sources) shows orange, healthy shows
                    # green - src/models/multi_source_confidence.py.
                    "color": "#dd6b20" if state.confidence_degraded else "#38a169",
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
        # The real "why" behind the Confidence tile above - generated
        # from actual source agreement/coverage
        # (src/models/multi_source_confidence.py), not a static caption.
        if state.confidence_explanation:
            st.caption(f"💡 {state.confidence_explanation}")

    with col2:
        st.markdown("🤖 **AI Situation Summary**")

        # Keyed off state.risk_category (sourced from the backend's own
        # risk_tier in create_state_from_api) instead of re-deriving from
        # risk_score with a separate set of thresholds - this used to have
        # its own 4-tier scale (40/60/80, no EXTREME) that disagreed with
        # both the backend and the "Current Risk Level" card above it,
        # e.g. showing "HIGH" here while the card read "CRITICAL" for the
        # same score, and never reaching EXTREME even at a 100% score.
        summary, color, recommendation = SITUATION_BY_TIER.get(
            state.risk_category, SITUATION_BY_TIER["MODERATE"]
        )

        st.markdown(
            f"<div style='background-color:#161616;padding:15px;"
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
            self.risk_color = "#ffaa00"
            self.affected_communities = []
            self.shelter_names = []
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
    map_state.risk_color = getattr(state, "risk_color", "#ffaa00")
    # Real per-district data (see fetch_situation_state) - the map used to
    # plot a fixed Alajo/Kaneshie/Circle/Nima/Mamobi list and 3 fixed
    # Accra shelter names no matter which district was selected, which
    # broke (showed the wrong city's places) the moment anyone changed
    # the district dropdown - one of the first things a reviewer tries.
    map_state.affected_communities = getattr(state, "affected_communities", [])
    map_state.shelter_names = getattr(state, "shelter_names", [])
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
        # river_level_m is None for 8 of the 9 tracked districts - real
        # DAHITI satellite altimetry coverage exists only for Tamale (see
        # src/hydrology/river_level_intelligence.py); it used to always be
        # a number (np.random.seed(hash(gauge_id)) fabricated with zero
        # real signal behind it) shown here as if genuine for every
        # district. Labeled "(no real gauge nearby)" rather than removed,
        # matching the same disclosure convention already used for
        # simulated satellite detection below.
        {
            "name": (
                "River Levels"
                if state.river_level_m is not None
                else "River Levels (no real gauge nearby)"
            ),
            "score": (
                min(100, (state.river_level_m / 3) * 100)
                if state.river_level_m is not None
                else 0
            ),
            "stars": (
                "☆☆☆☆☆"
                if state.river_level_m is None
                else (
                    "★★★★★"
                    if state.river_level_m > 2.0
                    else "★★★★☆" if state.river_level_m > 1.0 else "★★★☆☆"
                )
            ),
            "confidence": (
                state.evidence_river_confidence
                if state.river_level_m is not None
                else 0
            ),
        },
        {
            "name": (
                "Soil Saturation"
                if state.soil_moisture_available
                else "Soil Saturation (no real SMAP reading)"
            ),
            "score": state.soil_saturation_percent if state.soil_moisture_available else 0,
            "stars": (
                "☆☆☆☆☆"
                if not state.soil_moisture_available
                else (
                    "★★★★★"
                    if state.soil_saturation_percent > 70
                    else "★★★★☆" if state.soil_saturation_percent > 50 else "★★★☆☆"
                )
            ),
            "confidence": (
                state.evidence_soil_confidence if state.soil_moisture_available else 0
            ),
        },
        {
            # Real Sentinel-1 SAR satellite flood detection (Google Earth
            # Engine via src/hydrology/sentinel_processor.py) when
            # reachable - this used to be a fabricated score with no
            # satellite data behind it at all
            # (75/40 purely from risk_score, which is itself derived from
            # rainfall, not satellite imagery). Label discloses when it's
            # simulated rather than a real detection.
            "name": (
                "Satellite Detection"
                if state.satellite_source == "Sentinel-1 SAR"
                else "Satellite Detection (simulated)"
            ),
            "score": min(100, state.satellite_flood_extent_km2 * 10),
            "stars": (
                "★★★★★"
                if state.satellite_water_detected and state.satellite_flood_extent_km2 > 5
                else "★★★★☆" if state.satellite_water_detected else "★★★☆☆"
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
                "color": "#dd6b20" if state.confidence_degraded else "#38a169",
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
    if state.confidence_explanation:
        st.caption(f"💡 {state.confidence_explanation}")

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
        # 0 (not the possibly-stale default) when real NASA SMAP data
        # is unavailable - render_visual_metric_card divides by
        # max_value and would crash on None, and showing the stale
        # default number would misrepresent it as a current reading.
        soil_saturation = (
            getattr(state, "soil_saturation_percent", 0)
            if getattr(state, "soil_moisture_available", True)
            else 0
        )
        # river_level_m is None for 8 of the 9 tracked districts (real
        # DAHITI coverage exists only for Tamale) - getattr's default only
        # applies when the attribute is missing, not when its value is
        # None, so this stays None here rather than silently becoming 0.
        river_level = getattr(state, "river_level_m", None)

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
            subtitle=(
                "Current saturation level (NASA SMAP)"
                if getattr(state, "soil_moisture_available", True)
                else "No real SMAP reading available"
            ),
        )
    with col2:
        render_visual_metric_card(
            value=river_level if river_level is not None else 0,
            label="River Level" if river_level is not None else "River Level (no real gauge nearby)",
            emoji="🌊",
            color="#4299e1",
            max_value=3.0,
            subtitle=(
                f"{river_level:.1f}m above typical low"
                if river_level is not None
                else "No real gauge close enough to this district"
            ),
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
    # This whole panel's honesty gap was already documented in code
    # comments below (shelter/resource/drive-time fields) but never
    # surfaced to anyone actually looking at the dashboard - a stakeholder
    # had no way to tell "Rescue Boats: 3" apart from a real live count.
    # Shelter and community NAMES are real (src/exposure/
    # shelter_candidates.py, src/exposure/community_names.py); resource
    # counts, shelter capacity/occupancy, and drive times are illustrative
    # placeholders because no live inventory or routing system exists yet.
    st.caption(
        "ℹ️ Shelter and community names are real. Resource counts, "
        "capacity/occupancy figures, and drive times below are "
        "illustrative placeholders - no live inventory or routing system "
        "exists yet."
    )

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


# Purely presentational (which icon to show for a given action type) -
# not a data claim, so it stays in the frontend even though the action
# itself now comes from the backend.
_ACTION_ICON_BY_TYPE = {
    "EVACUATE_ALL": "🚨",
    "EVACUATE_VULNERABLE": "🚨",
    "PREPARE": "⚠️",
    "MONITOR": "📢",
}


def render_ai_decision_center(state):
    """QUESTION 6: What should we do? - VISUAL VERSION.

    Calls the backend's POST /decision/card (src/api/routes/decision_card.py)
    - the single source of truth for action/priority/confidence/evidence/
    data_gaps - instead of recomputing any of it here. This function used
    to independently reimplement the same evidence-gathering and
    confidence-scoring logic the backend now owns, which is exactly the
    two-implementations-of-one-fact drift risk this platform has hit and
    fixed repeatedly elsewhere (risk tier thresholds, lead time tables,
    district lists). This is now purely a renderer: formatting choices
    (which icon, how to phrase a hint-count as a display string) stay
    here; every actual claim, number, and confidence value comes from
    the response."""
    st.markdown("## 🎯 AI Decision Center")
    st.caption("*What actions should we take and why?*")

    card = call_api(
        "/decision/card",
        "POST",
        {"location": state.district, "precipitation": state.rainfall_mm},
    )
    if "error" in card or "action" not in card:
        st.error(
            f"Could not reach the AI Decision Engine: {card.get('error', 'unknown error')}"
        )
        st.divider()
        return

    tier = card["risk_tier"]
    style = get_risk_tier_style(tier=tier)
    urgency_color = style["color"]
    action_icon = _ACTION_ICON_BY_TYPE.get(card["action"]["type"], "🎯")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(
            f"""
        <div style="
            background: #161616;
            padding: 16px 20px;
            border-radius: 10px;
            box-shadow: 0 0 0 1px rgba(255,255,255,0.08);
            border-left: 6px solid {urgency_color};
        ">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                <span style="font-size: 20px;">{style["emoji"]}</span>
                <span style="font-weight: 600; color: {urgency_color}; font-size: 14px;">
                    {tier}
                </span>
            </div>
            <h2 style="font-size: 22px; margin: 0 0 12px 0;">{action_icon} {card["action"]["label"]}</h2>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Confidence bar - basis shown alongside so the number is
        # explainable (what raised/held it) rather than a bare percentage.
        confidence = card["confidence"]["value"]
        st.progress(confidence / 100, text=f"Confidence: {confidence}%")
        st.caption(f"Based on: {' • '.join(card['confidence']['basis'])}")

        # fused_risk_score is a real, independent noisy-OR combination
        # of rainfall (pluvial) and river/dam (fluvial) pathways
        # (src/models/multi_source_confidence.py) - score above is
        # rainfall-only. When fused_risk_score is meaningfully higher,
        # a real threat (almost always a dam/river one, since that's
        # the only other pathway that can outrun rainfall) is active
        # that the rainfall-only tier above cannot see on its own -
        # exactly the "dam overflow floods a district with no rain"
        # case this platform must never leave silent.
        fused_score = card.get("fused_risk_score")
        if fused_score is not None and fused_score > card.get("score", 0) + 10:
            st.warning(
                f"⚠️ **Independent pathway check**: {card.get('risk_attribution', '')} "
                f"Fused risk is **{card.get('fused_risk_tier', '?')}** "
                f"({fused_score:.0f}%) even though rainfall alone is only {tier}."
            )
        elif card.get("risk_attribution"):
            st.caption(f"🔎 {card['risk_attribution']}")

        st.markdown("**Why?**")
        # `reason` is a single real, period-joined sentence from the
        # backend - split purely for bullet-point display, never
        # reinterpreted or added to.
        for part in [p.strip() for p in card["reason"].split(". ") if p.strip()]:
            st.markdown(f"• {part.rstrip('.')}.")

        # What the platform explicitly does NOT know for this district -
        # e.g. Bagre Dam's unresolved cross-border notification gap for
        # Tamale - shown so a gap reads as a disclosed unknown, not
        # silence that could be mistaken for "no dam risk here".
        if card["data_gaps"]:
            st.markdown("**⚠️ Data Gaps**")
            for gap in card["data_gaps"]:
                st.caption(f"• {gap}")

    with col2:
        st.markdown("**Expected Impact**")
        impact = card["expected_impact"]
        population = impact.get("population_exposed") or 0
        cost = impact.get("estimated_cost_ghs") or 0
        # Which verb/scope to show is a phrasing choice, not a data claim
        # (the underlying population/cost numbers are all real, from the
        # response) - LOW tier describes routine district monitoring
        # rather than a specific population count, matching this app's
        # tier semantics elsewhere (src/exposure/impact_estimator.py's
        # own LOW/VERY_LOW "MONITOR CONDITIONS"/"NORMAL ACTIVITIES").
        if tier in ("LOW", "VERY_LOW"):
            detail = f"Monitor {TRACKED_DISTRICT_COUNT} districts"
        elif tier == "MODERATE":
            detail = f"Alert {population:,} people"
        else:
            detail = f"Protect {population:,} people"
        render_impact_card(
            value=cost,
            label="Estimated Cost",
            emoji="💰",
            color="#ed8936",
            detail=detail,
        )

        lead_time_hours = card.get("time_window_hours")
        if tier in ("LOW", "VERY_LOW") or not lead_time_hours:
            time_window = "Ongoing"
        elif lead_time_hours <= 1:
            time_window = "Immediately"
        else:
            time_window = f"Within {lead_time_hours} hours"
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


def render_risk_history_chart(state):
    """Real recorded risk history (GET /v1/districts/{district}/risk/
    history, src/api/v1/risk_history.py) - a genuinely new capability,
    distinct from render_risk_timeline above: that panel projects what
    the score is EXPECTED to do over the next 24h; this one shows what
    it ACTUALLY was, recorded by the scheduled automated assessment
    (scripts/automated_risk_assessment.py, every 3 hours) - past fact
    vs. future projection, not two views of the same thing."""
    st.markdown("## 📊 Risk History (Recorded)")
    st.caption("*What has actually been recorded for this district over time?*")

    history = call_api(f"/v1/districts/{state.district}/risk/history", "GET")
    if "error" in history:
        st.caption(f"⚠️ Could not reach risk history: {history['error']}")
        st.divider()
        return

    points = history.get("history", [])
    if not points:
        st.info(
            "No recorded history yet for this district - snapshots are "
            "taken automatically every 3 hours by the scheduled risk "
            "assessment job. Check back after it next runs."
        )
        st.divider()
        return

    import plotly.graph_objects as go

    timestamps = [p["recorded_at"] for p in points]
    scores = [p["score"] for p in points]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=scores,
            mode="lines+markers",
            line=dict(color="#0f3460", width=3),
            name="Risk score",
        )
    )
    # Same 30/50/70/85 tier thresholds used everywhere else
    # (src/alerts/formatter.py:get_risk_tier) - not a separate scale.
    for threshold, label, color in (
        (85, "EXTREME", "#cc0000"),
        (70, "CRITICAL", "#ff0000"),
        (50, "HIGH", "#ff6600"),
        (30, "MODERATE", "#ffaa00"),
    ):
        fig.add_hline(
            y=threshold, line_dash="dash", line_color=color, annotation_text=label
        )
    fig.update_layout(
        height=280,
        yaxis_range=[0, 100],
        yaxis_title="Risk Score (%)",
        xaxis_title="Recorded at",
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"{len(points)} recorded snapshot(s) shown")

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
        # Popped (not just read) so a real, paid LLM call fires exactly
        # once per question - previously this branch just re-formatted a
        # static string, so re-running it on every unrelated Streamlit
        # rerun (e.g. a slider drag elsewhere on the page) was free; now
        # it's a live call to POST /v1/copilot/ask, so it must not
        # re-fire on reruns that aren't a new question.
        query = st.session_state.pop("copilot_query")
        with st.spinner("Checking the platform's live data..."):
            result = call_api(
                "/v1/copilot/ask",
                "POST",
                {"question": query, "district": state.district},
                timeout=60,
            )

        if "error" in result:
            st.error(f"Copilot could not reach the platform's live data: {result['error']}")
        else:
            st.info(result.get("answer", "No answer returned."))
            tool_calls = result.get("tool_calls", [])
            if tool_calls:
                with st.expander(f"🔎 Evidence used - {len(tool_calls)} live platform call(s)"):
                    for call in tool_calls:
                        st.code(f"{call['tool']}({call['input']})", language="text")


# ============================================================
# MAIN APPLICATION
# ============================================================


def apply_confidence_to_state(state, confidence_data) -> None:
    """Maps GET /v1/districts/{district}/evidence's real confidence
    block (src/models/multi_source_confidence.py) onto a DashboardState
    in place - pulled out of fetch_situation_state so this mapping is
    testable without a Streamlit runtime. Leaves state untouched (its
    dataclass defaults stand) if the call failed or returned no
    confidence block, rather than crashing the whole page render."""
    if not isinstance(confidence_data, dict):
        return
    confidence_block = confidence_data.get("confidence")
    if not confidence_block:
        return
    state.risk_confidence = confidence_block["value"] / 100.0
    state.evidence_overall_confidence = confidence_block["value"]
    state.confidence_explanation = confidence_block["explanation"]
    state.confidence_degraded = confidence_block["degraded"]


def fetch_situation_state(district: str, rainfall_mm: float):
    """Real fetch-and-build-state logic, shared by the full detailed
    dashboard (render_situation) and the compact broadcast view
    (render_broadcast_view) - both show the real system's real response
    to (district, rainfall_mm), just laid out differently. Returns
    (state, district_data)."""
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
    # Real per-district community names (src/exposure/community_names.py,
    # mirrored client-side in get_district_data) - this field existed on
    # DashboardState already but nothing ever assigned it, so every
    # consumer either fell back to state.district alone or (the National
    # Flood Map) used a hardcoded Accra-only list regardless of the
    # selected district. See render_situation_map's own fix for why this
    # matters.
    state.affected_communities = district_data.get("affected_communities", [])

    # Real multi-source fusion confidence (src/models/multi_source_
    # confidence.py) - replaces the fixed 0.80 DashboardState default,
    # which no code path ever overwrote before this. /situation doesn't
    # carry a confidence field, so this is a second, real call rather
    # than something derivable from api_data above.
    confidence_data = call_api(
        f"/v1/districts/{district}/evidence?precipitation_mm={rainfall_mm}", "GET"
    )
    apply_confidence_to_state(state, confidence_data)

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

    return state, district_data


def render_situation(
    district: str, rainfall_mm: float, stage_label: str = None, show_copilot: bool = True
):
    """Fetch the real situation for (district, rainfall_mm) and render the
    full, detailed dashboard for it - every panel, meant for an operator
    who needs to scroll through and inspect everything. See
    render_broadcast_view for the compact single-screen alternative used
    by demo mode.

    show_copilot=False skips the AI Copilot panel (its button/chat_input
    widgets have fixed keys, so calling it more than once in a single
    script run - which the demo loop does, one call per stage - would
    raise a duplicate-widget-key error; it also doesn't make sense to
    show an input box mid-auto-play anyway)."""
    state, district_data = fetch_situation_state(district, rainfall_mm)

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
    render_risk_history_chart(state)
    if show_copilot:
        render_ai_copilot(state)

    st.divider()
    st.caption("🌊 CivicFlood AI • Decision Intelligence for National Flood Response")
    st.caption("NFCC Platform • Ghana AI Innovation Challenge 2026")
    st.caption(f"📊 {state.active_sources_count} Data Sources Active • 🔗 {API_URL}")
    st.caption(f"🔄 Last updated: {state.timestamp[:19]}")


def render_broadcast_view(district: str, rainfall_mm: float, stage_label: str):
    """Compact, single-screen 'TV broadcast' view for demo mode - one
    dominant risk indicator, a handful of key numbers, no scrolling.

    render_situation (the full dashboard) repeated every single detailed
    panel per stage, which was exactly as long and scroll-heavy during
    the demo as normal manual mode - the opposite of a quick, glanceable
    presentation for a 5-minute stakeholder briefing. This shows the same
    real fetch_situation_state() data, just as one condensed screen
    instead of the full operational console."""
    state, _ = fetch_situation_state(district, rainfall_mm)
    summary, color, recommendation = SITUATION_BY_TIER.get(
        state.risk_category, SITUATION_BY_TIER["MODERATE"]
    )
    style = get_risk_tier_style(tier=state.risk_category)

    # Real peak risk in the next 24h, from the forecast-driven risk
    # timeline (src/api/routes/situation.py) - not a synthetic estimate.
    peak_score = (
        max(p["score"] for p in state.risk_timeline)
        if state.risk_timeline
        else state.risk_score
    )

    st.markdown(
        f"<div style='background:#111827;color:#fff;padding:10px 24px;"
        f"border-radius:8px;display:flex;justify-content:space-between;"
        f"align-items:center;margin-bottom:16px;'>"
        f"<span style='font-size:18px;font-weight:700;letter-spacing:1px;'>"
        f"🎬 {stage_label}</span>"
        f"<span style='font-size:14px;color:#9ca3af;'>{district} • "
        f"{datetime.now().strftime('%H:%M:%S UTC')}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"<div style='background:{style['color']};color:#fff;"
        f"padding:36px 24px;border-radius:16px;text-align:center;"
        f"margin-bottom:20px;'>"
        f"<div style='font-size:72px;line-height:1;'>{style['emoji']}</div>"
        f"<div style='font-size:64px;font-weight:800;line-height:1.1;'>"
        f"{state.risk_score:.0f}%</div>"
        f"<div style='font-size:28px;font-weight:700;letter-spacing:2px;'>"
        f"{state.risk_category}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    render_quick_stats(
        [
            {
                "label": "Population at Risk",
                "value": state.population_exposed,
                "emoji": "👥",
                "color": style["color"],
            },
            {
                "label": "Lead Time",
                "value": f"{state.lead_time_hours}h",
                "emoji": "⏰",
                "color": style["color"],
            },
            {
                "label": "Peak Risk (24h)",
                "value": f"{peak_score:.0f}%",
                "emoji": "📈",
                "color": style["color"],
            },
            {
                "label": "Confidence",
                "value": f"{state.risk_confidence * 100:.0f}%",
                "emoji": "🎯",
                "color": style["color"],
            },
        ],
        columns=4,
    )
    if state.confidence_explanation:
        st.caption(f"💡 {state.confidence_explanation}")

    st.markdown(
        f"<div style='background:#161616;padding:16px 20px;"
        f"border-radius:8px;border-left:6px solid {color};"
        f"margin-top:16px;font-size:16px;'>"
        f"<strong>{summary}</strong><br>"
        f"<span style='font-size:14px;'>Recommended: {recommendation}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Three real readings driving the score - condensed to one line, not
    # the full 5-item Evidence & Confidence panel.
    sat_note = (
        "🛰️ Water detected"
        if state.satellite_water_detected
        else "🛰️ No water detected"
    )
    river_note = (
        f"🌊 River: {state.river_level_m:.1f}m above typical low"
        if state.river_level_m is not None
        else "🌊 River: no real gauge nearby"
    )
    soil_note = (
        f"💧 Soil saturation: {state.soil_saturation_percent:.0f}%"
        if getattr(state, "soil_moisture_available", True)
        else "💧 Soil saturation: no real SMAP reading"
    )
    st.caption(
        f"🌧️ Rainfall: {state.rainfall_mm:.0f}mm  •  "
        f"{river_note}  •  "
        f"{soil_note}  •  "
        f"{sat_note} ({state.satellite_source})"
    )


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


# basis distinguishes independent CAUSAL PATHWAYS, not just data
# sources: forward-looking forecast rainfall, backward-looking
# antecedent accumulation (src/hydrology/antecedent_rainfall.py), and
# dam/river levels (src/hydrology/fluvial_pathway.py) - the last one is
# NOT a rainfall signal at all (its "precipitation" field is really a
# 0-100 risk score, see score_override), it's real evidence of a
# dam/river-driven flood that can occur with zero local rain. A
# reviewer needs to know which pathway queued a given item, since they
# carry genuinely different meaning and different required response.
_BASIS_LABELS = {
    "forecast_next_24h": "🔮 Forecast (next 24h)",
    "antecedent_3d_accumulation": "🌧️ Observed accumulation (last 3 days, CHIRPS)",
    "antecedent_3d_observed_fallback": "🌧️ Observed accumulation (last 3 days, fallback)",
    "dam_river_pathway": "🌊 Dam/river level (independent of local rainfall)",
}


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

    # CAP status=Exercise: lets the team practice the full review workflow
    # (assess -> queue -> approve -> retract) on demand, for any district/
    # tier, without waiting for real rain - approving or cancelling one of
    # these never calls AlertEngine.process() (see src/api/routes/
    # alert_review.py), so it is physically impossible for a drill to
    # reach a real recipient.
    with st.expander("🎓 Create Practice Exercise (training drill, never sent for real)"):
        ex_col1, ex_col2, ex_col3 = st.columns([2, 2, 1])
        with ex_col1:
            ex_district = st.selectbox(
                "District", ALL_TRACKED_DISTRICTS, key="exercise_district"
            )
        with ex_col2:
            ex_tier = st.selectbox(
                "Simulated tier",
                ["MODERATE", "HIGH", "CRITICAL", "EXTREME"],
                index=1,
                key="exercise_tier",
            )
        with ex_col3:
            st.write("")
            st.write("")
            if st.button("Queue Drill", use_container_width=True):
                call_api(
                    "/alerts/exercise",
                    "POST",
                    {"location": ex_district, "risk_tier": ex_tier},
                )
                st.rerun()

    pending = call_api("/alerts/pending", "GET")
    alerts = pending.get("alerts", [])

    if "error" in pending:
        st.error(f"Could not reach the review queue: {pending['error']}")
        return

    if not alerts:
        st.success("✅ No pending alerts. All caught up.")
    else:
        st.markdown(f"### {len(alerts)} awaiting review")
        for alert in alerts:
            style = get_risk_tier_style(tier=alert["risk_tier"])
            is_exercise = alert.get("cap_status") == "Exercise"
            with st.container(border=True):
                if is_exercise:
                    st.warning(
                        "🎓 **EXERCISE — THIS IS A DRILL.** Approving this "
                        "cannot send a real message to anyone.",
                        icon="🎓",
                    )
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    st.markdown(
                        f"{style['emoji']} **{alert['location']}** — "
                        f"{alert['risk_tier']} ({alert['score']:.0f}%)"
                    )
                    basis_label = _BASIS_LABELS.get(alert.get("basis"), "Precipitation")
                    st.caption(f"{basis_label}: {alert['precipitation']}mm")
                    # Common Alerting Protocol's three independent
                    # decision axes (OASIS CAP standard) - Severity from
                    # the risk tier, Urgency from real lead-time
                    # (src/exposure/impact_estimator.py), Certainty from
                    # real Sentinel-1 satellite confirmation when
                    # available (src/hydrology/sentinel_processor.py) -
                    # richer context than the single score/tier above.
                    if alert.get("severity"):
                        st.caption(
                            f"📋 CAP: **{alert['severity']}** severity • "
                            f"**{alert['urgency']}** urgency • "
                            f"**{alert['certainty']}** certainty"
                        )
                    # Geotargeting - the real named communities within this
                    # district (src/exposure/community_names.py), not just
                    # the district name, so a reviewer sees exactly who
                    # this would reach.
                    communities = alert.get("affected_communities") or []
                    if communities:
                        st.caption(f"📍 Targets: {', '.join(communities)}")
                with c2:
                    st.markdown(f"*{alert['message']}*")
                    st.caption(f"Queued: {alert['created_at'][:19]}")
                    # JMA-style tiered response guidance - who specifically
                    # should act at this severity, not just a generic
                    # "take precautions" line.
                    if alert.get("response_guidance"):
                        st.caption(f"🎯 {alert['response_guidance']}")
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
                    # Real OASIS CAP v1.2 XML (src/api/routes/cap_export.py)
                    # for this exact alert - the same schema FEMA IPAWS/EU/
                    # Japan/Canada distributors consume, so this could be
                    # handed to a real CAP-compliant system without a
                    # bespoke integration. Read-only export; never sent
                    # anywhere by this button.
                    cap_xml = fetch_cap_xml(alert["id"])
                    if cap_xml:
                        st.download_button(
                            "📄 CAP XML",
                            data=cap_xml,
                            file_name=f"nfcc-alert-{alert['id']}.cap.xml",
                            mime="application/cap+xml",
                            key=f"cap_xml_{alert['id']}",
                            use_container_width=True,
                        )

    # Retraction (CAP msgType=Cancel) for already-sent alerts - directly
    # motivated by South Korea's May 2023 false missile alert, where the
    # public endured ~20 minutes of confusion partly because there was no
    # fast, clear correction path. A sent alert is never truly final here.
    st.divider()
    st.markdown("### 📤 Recently Sent (can be retracted)")
    sent = call_api("/alerts/pending?status=approved", "GET")
    sent_alerts = sent.get("alerts", [])[:10]

    if not sent_alerts:
        st.caption("No sent alerts to retract.")
    else:
        for alert in sent_alerts:
            style = get_risk_tier_style(tier=alert["risk_tier"])
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    exercise_tag = (
                        " 🎓 EXERCISE (drill only, nothing was sent)"
                        if alert.get("cap_status") == "Exercise"
                        else ""
                    )
                    st.markdown(
                        f"{style['emoji']} **{alert['location']}** — "
                        f"{alert['risk_tier']} • sent {alert['reviewed_at'][:19]}"
                        f"{exercise_tag}"
                    )
                    reason = st.text_input(
                        "Retraction reason (required)",
                        key=f"cancel_reason_{alert['id']}",
                        placeholder="e.g. Rainfall did not materialize as forecast",
                    )
                with c2:
                    st.write("")
                    if st.button(
                        "🔴 Retract Alert",
                        key=f"cancel_{alert['id']}",
                        use_container_width=True,
                        disabled=not reason,
                    ):
                        call_api(
                            f"/alerts/pending/{alert['id']}/cancel",
                            "POST",
                            {"reviewed_by": "dashboard-operator", "reason": reason},
                        )
                        st.rerun()
                    cap_xml = fetch_cap_xml(alert["id"])
                    if cap_xml:
                        st.download_button(
                            "📄 CAP XML",
                            data=cap_xml,
                            file_name=f"nfcc-alert-{alert['id']}.cap.xml",
                            mime="application/cap+xml",
                            key=f"cap_xml_sent_{alert['id']}",
                            use_container_width=True,
                        )


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
        # Cleanly stop any in-progress demo rather than leaving
        # demo_stage_idx frozen mid-sequence - without this, switching
        # Review Queue mode off again would silently resume the demo from
        # wherever it was interrupted instead of returning to a fresh
        # "click Start Demo" state.
        if st.session_state.get("demo_stage_idx") is not None:
            st.session_state["demo_stage_idx"] = None
            st.info("🎬 Demo stopped because Review Queue mode was opened.")
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
        # Compact broadcast view, not the full scrolling dashboard - see
        # render_broadcast_view's docstring for why.
        render_broadcast_view(district, rainfall_mm, stage_label=label)
        time.sleep(DEMO_SECONDS_PER_STAGE)
        st.session_state["demo_stage_idx"] = idx + 1
        st.rerun()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error("🚨 Dashboard encountered an error. Please check the logs.")
        st.exception(e)
