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
        "Interactive map showing flood risk, affected areas, shelters, and infrastructure"
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

    # Define risk_data BEFORE try block
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

    risk_colors = {
        "EXTREME": "#ff0000",
        "HIGH": "#ff6600",
        "MODERATE": "#ffaa00",
        "LOW": "#00cc00",
    }

    try:
        center_lat = getattr(state, "lat", 5.560)
        center_lon = getattr(state, "lon", -0.210)

        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=12,
            # Dark basemap (free, no API key) to match the dashboard's
            # Finelo-inspired dark theme - the default light OpenStreetMap
            # tile would otherwise be a bright rectangle on an otherwise
            # near-black page.
            tiles="CartoDB dark_matter",
            control_scale=True,
        )

        for area in risk_data:
            color = risk_colors.get(area["risk"], "#808080")
            radius = max(8, min(45, int(area["pop"] / 1000)))

            # PLAIN TEXT - NO HTML
            popup_text = (
                f"{area['name']} | Risk: {area['risk']} | Population: {area['pop']:,}"
            )

            folium.CircleMarker(
                location=[area["lat"], area["lon"]],
                radius=radius,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7,
                weight=2,
                popup=popup_text,
            ).add_to(m)

        shelters = [
            {
                "name": "Accra High School",
                "lat": 5.578,
                "lon": -0.222,
                "capacity": 1200,
            },
            {"name": "Community Center", "lat": 5.562, "lon": -0.218, "capacity": 500},
            {
                "name": "Trade Fair Centre",
                "lat": 5.565,
                "lon": -0.185,
                "capacity": 2000,
            },
        ]

        for shelter in shelters:
            popup_text = f"{shelter['name']} | Capacity: {shelter['capacity']:,} | OPEN"

            folium.Marker(
                location=[shelter["lat"], shelter["lon"]],
                popup=popup_text,
                icon=folium.Icon(color="green", icon="home", prefix="fa"),
            ).add_to(m)

        river_points = [
            [5.560, -0.205],
            [5.555, -0.210],
            [5.550, -0.215],
            [5.545, -0.220],
            [5.540, -0.225],
        ]

        folium.PolyLine(
            river_points, color="blue", weight=3, opacity=0.7, popup="Odaw River"
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

        st.caption("🗺️ Click on markers for details • Updated in real-time")

    except Exception as e:
        st.warning(f"⚠️ Map temporarily unavailable")
        st.markdown("### 📍 Affected Areas")

        risk_df = pd.DataFrame(
            [
                {
                    "Community": r["name"],
                    "Risk": r["risk"],
                    "Population": f"{r['pop']:,}",
                }
                for r in risk_data
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
