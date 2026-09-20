"""
Situation Map Module - Full Implementation
Surgical fix: Plain text popups only.
"""

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from hackathon.app.modules.v4.state import TRACKED_DISTRICT_COUNT


def render_situation_map(state):
    """Render the complete interactive situation map."""

    st.markdown("## 🗺️ National Flood Situation Map")
    st.caption(
        "Real community and shelter names for the selected district, at "
        "approximate positions (no per-community geocoding or risk data "
        "exists yet - all markers share the district's one real risk tier)."
    )

    # Color legend
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown("🔴 **EXTREME**")
        st.caption("Immediate evacuation")
    with col2:
        st.markdown("🟠 **HIGH**")
        st.caption("Prepare to evacuate")
    with col3:
        st.markdown("🟡 **MODERATE**")
        st.caption("Monitor conditions")
    with col4:
        st.markdown("🟢 **LOW**")
        st.caption("Normal monitoring")
    with col5:
        st.markdown("🏛️ **Shelter**")
        st.caption("Safe location")

    risk_colors = {
        "EXTREME": "#ff0000",
        "CRITICAL": "#cc0000",
        "HIGH": "#ff6600",
        "MODERATE": "#ffaa00",
        "LOW": "#00cc00",
    }

    try:
        center_lat = getattr(state, "lat", 5.560)
        center_lon = getattr(state, "lon", -0.210)
        district_risk = getattr(state, "risk_category", "MODERATE")
        marker_color = risk_colors.get(
            district_risk, getattr(state, "risk_color", "#ffaa00")
        )

        # Real per-district community/shelter NAMES (see
        # fetch_situation_state in dashboard.py: state.affected_communities
        # from src/exposure/community_names.py, state.shelter_names from
        # src/exposure/shelter_candidates.py via /situation) - this used to
        # be a fixed Alajo/Kaneshie/Circle/Nima/Mamobi list and 3 fixed
        # Accra shelter names regardless of the selected district. No real
        # per-community lat/lon or per-community risk level exists anywhere
        # in the codebase (only a district-level risk score), so markers
        # are positioned at small illustrative offsets around the real
        # district center and all colored by the district's one real risk
        # tier - deliberately uniform rather than inventing distinct
        # per-community risk levels that don't exist.
        communities = getattr(state, "affected_communities", None) or [
            getattr(state, "district", "This district")
        ]
        shelter_names = getattr(state, "shelter_names", None) or []

        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=12,
            # Deliberately kept as the standard light basemap, not a dark
            # one - a real street/satellite map reads better for actually
            # locating flooded areas and infrastructure than a dark
            # basemap would, even though the rest of the dashboard uses a
            # dark theme.
            tiles="OpenStreetMap",
            control_scale=True,
        )

        # Small deterministic ring offsets (~0.6-1km) around the real
        # district center - illustrative positions, not surveyed
        # coordinates, since no real per-community geocoding exists.
        _offsets = [(0.006, 0.0), (0.002, 0.007), (-0.005, 0.004), (-0.005, -0.004), (0.002, -0.007)]
        for i, name in enumerate(communities[:5]):
            d_lat, d_lon = _offsets[i % len(_offsets)]
            popup_text = (
                f"{name} | District risk: {district_risk} "
                "(approximate location)"
            )
            folium.CircleMarker(
                location=[center_lat + d_lat, center_lon + d_lon],
                radius=14,
                color=marker_color,
                fill=True,
                fill_color=marker_color,
                fill_opacity=0.7,
                weight=2,
                popup=popup_text,
            ).add_to(m)

        _shelter_offsets = [(0.010, 0.005), (-0.009, 0.008), (0.004, -0.011)]
        for i, name in enumerate(shelter_names[:3]):
            d_lat, d_lon = _shelter_offsets[i % len(_shelter_offsets)]
            popup_text = f"{name} (approximate location - exact coordinates not available)"
            folium.Marker(
                location=[center_lat + d_lat, center_lon + d_lon],
                popup=popup_text,
                icon=folium.Icon(color="green", icon="home", prefix="fa"),
            ).add_to(m)

        st_folium(m, width=800, height=500)

        # Districts Monitored / Active Flood Zones now come from GET
        # /national/summary (real river-discharge-based computation via
        # Open-Meteo's Flood API, dashboard.py's get_national_summary),
        # passed through on map_state - previously hardcoded "10"/"3" with
        # no data behind either number. Shelters Available has no real
        # source anywhere in the codebase (no live shelter registry
        # exists) and stays illustrative. Verified Reports uses the real
        # count from src/community/community_memory.py via /situation
        # instead of a hardcoded "4" that never matched
        # state.verified_reports (already correctly wired, reads 0 - no
        # real report has ever been submitted, no reporting channel built).
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                "Districts Monitored",
                getattr(state, "district_count", TRACKED_DISTRICT_COUNT),
            )
        with col2:
            st.metric("Active Flood Zones", getattr(state, "active_flood_zones", 3))
        with col3:
            st.metric("Shelters Available", getattr(state, "shelters_available", 3))
        with col4:
            st.metric("Verified Reports", getattr(state, "verified_reports", 0))

        st.caption("🗺️ Click a marker for its name and district risk tier")

    except Exception as e:
        # Re-reads from `state` directly rather than the try block's local
        # variables (communities/district_risk) - those may not have been
        # assigned yet if the exception happened before they were set, and
        # this used to reference risk_data, a name that no longer exists
        # in this function at all since the fixed Accra-only list was
        # replaced with real per-district data.
        st.warning("⚠️ Map temporarily unavailable")
        st.markdown("### 📍 Affected Areas")

        fallback_communities = getattr(state, "affected_communities", None) or [
            getattr(state, "district", "This district")
        ]
        risk_df = pd.DataFrame(
            [
                {
                    "Community": name,
                    "District Risk": getattr(state, "risk_category", "MODERATE"),
                }
                for name in fallback_communities[:5]
            ]
        )
        st.dataframe(risk_df, use_container_width=True)


def render_map_fallback():
    """Fallback function when map fails to load."""
    st.warning("⚠️ Map unavailable - showing data instead")
    st.markdown("### 📍 Affected Areas")
    risk_data = [
        {"name": "Alajo", "lat": 5.565, "lon": -0.218, "risk": "EXTREME", "pop": 18750},
        {
            "name": "Kaneshie",
            "lat": 5.555,
            "lon": -0.228,
            "risk": "EXTREME",
            "pop": 22340,
        },
        {"name": "Circle", "lat": 5.575, "lon": -0.225, "risk": "HIGH", "pop": 15620},
        {"name": "Nima", "lat": 5.555, "lon": -0.215, "risk": "HIGH", "pop": 48230},
        {
            "name": "Mamobi",
            "lat": 5.545,
            "lon": -0.212,
            "risk": "MODERATE",
            "pop": 34320,
        },
    ]
    import pandas as pd

    risk_df = pd.DataFrame(
        [
            {"Community": r["name"], "Risk": r["risk"], "Population": f"{r['pop']:,}"}
            for r in risk_data
        ]
    )
    st.dataframe(risk_df, use_container_width=True)


def render_minimal_map():
    """Minimal map for testing."""
    try:
        m = folium.Map(
            location=[5.6037, -0.1870],
            zoom_start=10,
        )
        folium.Marker([5.6037, -0.1870], popup="Test Marker").add_to(m)
        st_folium(m, width=700, height=500, key="minimal_map_test")
        return True
    except Exception as e:
        st.error(f"Minimal map failed: {str(e)}")
        return None
