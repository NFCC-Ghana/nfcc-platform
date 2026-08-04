"""
CivicFlood AI - Interactive GIS Flood Risk Map
Complete and ready to use.
"""

import json
from datetime import datetime

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import folium_static


def create_flood_risk_map(
    district: str = None, risk_level: str = "MODERATE"
) -> folium.Map:
    """
    Create an interactive flood risk map for Ghana.

    Args:
        district: Selected district (e.g., "Accra Central")
        risk_level: Risk level (EXTREME, HIGH, MODERATE, LOW)

    Returns:
        folium.Map object
    """

    # Ghana center coordinates
    m = folium.Map(location=[7.9465, -1.0232], zoom_start=7, tiles="OpenStreetMap")

    # Flood zone data for Ghana (simplified)
    flood_zones = {
        "Accra Central": {
            "coordinates": [5.560, -0.210],
            "risk": "HIGH",
            "color": "orange",
            "communities": ["Alajo", "Kaneshie", "Circle", "Nima", "Mamobi"],
        },
        "Accra West": {
            "coordinates": [5.550, -0.230],
            "risk": "HIGH",
            "color": "orange",
            "communities": ["Dansoman", "Chorkor", "Mallam"],
        },
        "Accra East": {
            "coordinates": [5.565, -0.190],
            "risk": "MODERATE",
            "color": "yellow",
            "communities": ["Labone", "Airport Residential"],
        },
        "Tema": {
            "coordinates": [5.650, -0.020],
            "risk": "HIGH",
            "color": "orange",
            "communities": ["Community 1", "Community 2", "Tema New Town"],
        },
        "Kumasi": {
            "coordinates": [6.670, -1.620],
            "risk": "MODERATE",
            "color": "yellow",
            "communities": ["Asokwa", "Bantama", "Oforikrom"],
        },
        "Tamale": {
            "coordinates": [9.400, -0.840],
            "risk": "MODERATE",
            "color": "yellow",
            "communities": ["Sagnarigu", "Savelugu"],
        },
    }

    # Color mapping for risk levels
    risk_colors = {
        "EXTREME": "red",
        "HIGH": "orange",
        "MODERATE": "yellow",
        "LOW": "green",
    }

    # Add flood zones
    for zone_name, zone_data in flood_zones.items():
        coords = zone_data["coordinates"]
        risk = zone_data["risk"]
        color = risk_colors.get(risk, "blue")

        # Determine if this is the selected district
        is_selected = district and district == zone_name

        # Radius based on risk
        radius = 50 if risk in ["HIGH", "EXTREME"] else 30

        # Add flood zone circle
        folium.Circle(
            location=coords,
            radius=radius * 1000,  # Convert to meters
            popup=f"""
            <b>{zone_name}</b><br>
            Risk: {risk}<br>
            Communities: {', '.join(zone_data['communities'])}
            """,
            color=color,
            fill=True,
            fillOpacity=0.3 if not is_selected else 0.6,
            weight=3 if is_selected else 2,
        ).add_to(m)

        # Add community markers
        for community in zone_data["communities"]:
            # Offset each community slightly
            import random

            random.seed(hash(community) % 2**32)
            offset_lat = random.uniform(-0.01, 0.01)
            offset_lon = random.uniform(-0.01, 0.01)

            folium.CircleMarker(
                location=[coords[0] + offset_lat, coords[1] + offset_lon],
                radius=5,
                popup=community,
                color=color,
                fill=True,
                fillOpacity=0.7,
            ).add_to(m)

    # Add Ghana's major rivers
    rivers = [
        {"name": "Volta", "coords": [[6.0, 0.0], [9.0, -0.5]], "color": "blue"},
        {
            "name": "Odaw",
            "coords": [[5.55, -0.20], [5.60, -0.20]],
            "color": "lightblue",
        },
        {
            "name": "Densu",
            "coords": [[5.55, -0.33], [5.60, -0.33]],
            "color": "lightblue",
        },
    ]

    for river in rivers:
        folium.PolyLine(
            river["coords"],
            color=river["color"],
            weight=3,
            opacity=0.7,
            popup=f"River {river['name']}",
        ).add_to(m)

    # Add layer control
    folium.LayerControl().add_to(m)

    return m


def get_risk_legend() -> str:
    """Get HTML legend for risk levels."""
    return """
    <div style="background: white; padding: 10px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
        <b>Risk Legend</b><br>
        <span style="color: red;">●</span> EXTREME Risk<br>
        <span style="color: orange;">●</span> HIGH Risk<br>
        <span style="color: yellow;">●</span> MODERATE Risk<br>
        <span style="color: green;">●</span> LOW Risk<br>
    </div>
    """


def render_gis_panel(district: str, risk_level: str):
    """Render the complete GIS panel."""
    st.markdown("### 🗺️ Flood Risk Map")

    # Create map
    m = create_flood_risk_map(district, risk_level)

    # Display map
    folium_static(m, width=700, height=500)

    # Display legend
    st.markdown(get_risk_legend(), unsafe_allow_html=True)

    # Display district info
    st.markdown("### 📍 Selected District Details")

    st.markdown(
        f"""
    <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px;">
        <b>District:</b> {district}<br>
        <b>Risk Level:</b> <span style="color: {'red' if risk_level == 'EXTREME' else 'orange' if risk_level == 'HIGH' else 'yellow' if risk_level == 'MODERATE' else 'green'};">{risk_level}</span><br>
        <b>Last Updated:</b> {datetime.now().strftime('%d %b %Y, %H:%M')}
    </div>
    """,
        unsafe_allow_html=True,
    )
