"""
Situation Map - Interactive National Flood Map
"""

import streamlit as st
import folium
from streamlit_folium import folium_static
import pandas as pd

def create_situation_map(district: str, risk_score: float) -> folium.Map:
    """Create interactive situation map with all layers."""
    
    # Ghana center
    m = folium.Map(location=[7.9465, -1.0232], zoom_start=7, tiles="OpenStreetMap")
    
    # District coordinates
    districts = {
        "Accra Central": [5.560, -0.210],
        "Accra West": [5.550, -0.230],
        "Accra East": [5.565, -0.190],
        "Tema": [5.650, -0.020],
        "Kumasi": [6.670, -1.620],
        "Tamale": [9.400, -0.840]
    }
    
    # Flood risk color
    if risk_score >= 80:
        color = "red"
        fill_color = "red"
    elif risk_score >= 60:
        color = "orange"
        fill_color = "orange"
    elif risk_score >= 40:
        color = "yellow"
        fill_color = "yellow"
    else:
        color = "green"
        fill_color = "green"
    
    # Add flood zones
    for name, coords in districts.items():
        is_selected = name == district
        radius = 50 if risk_score >= 60 else 30
        if is_selected:
            radius = 60
        
        folium.Circle(
            location=coords,
            radius=radius * 1000,
            popup=f"{name}<br>Risk: {risk_score:.0f}%" if is_selected else name,
            color=color,
            fill=True,
            fillOpacity=0.3 if not is_selected else 0.6,
            weight=3 if is_selected else 2
        ).add_to(m)
        
        folium.Marker(
            coords,
            popup=f"{name}<br>Risk: {risk_score:.0f}%" if is_selected else name,
            icon=folium.Icon(color=color, icon="info-sign")
        ).add_to(m)
    
    # Add rivers
    rivers = [
        {"name": "Volta", "coords": [[6.0, 0.0], [9.0, -0.5]]},
        {"name": "Odaw", "coords": [[5.55, -0.20], [5.60, -0.20]]},
        {"name": "Densu", "coords": [[5.55, -0.33], [5.60, -0.33]]}
    ]
    
    for river in rivers:
        folium.PolyLine(
            river["coords"],
            color="blue",
            weight=2,
            opacity=0.6,
            popup=river["name"]
        ).add_to(m)
    
    # Add shelters (simplified)
    shelters = [
        {"name": "Accra High School", "coords": [5.578, -0.222]},
        {"name": "Community Center", "coords": [5.560, -0.225]},
        {"name": "Trade Fair Centre", "coords": [5.565, -0.185]}
    ]
    
    for shelter in shelters:
        folium.Marker(
            shelter["coords"],
            popup=f"🏛️ {shelter['name']}",
            icon=folium.Icon(color="green", icon="home", prefix="fa")
        ).add_to(m)
    
    # Add flood polygons (simplified)
    if risk_score >= 60:
        flood_zones = [
            {"name": "Alajo", "coords": [5.555, -0.215]},
            {"name": "Kaneshie", "coords": [5.555, -0.225]},
            {"name": "Circle", "coords": [5.575, -0.225]}
        ]
        
        for zone in flood_zones:
            folium.CircleMarker(
                zone["coords"],
                radius=20,
                popup=f"🌊 {zone['name']} - Flooding Confirmed",
                color="red",
                fill=True,
                fillOpacity=0.4
            ).add_to(m)
    
    return m


def render_situation_map(district: str, risk_score: float) -> None:
    """Render situation map panel."""
    
    st.markdown("### 🗺️ National Flood Situation Map")
    st.caption("Interactive map showing flood risk, affected areas, shelters, and infrastructure")
    
    # Legend
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown("🔴 **EXTREME**")
    with col2:
        st.markdown("🟠 **HIGH**")
    with col3:
        st.markdown("🟡 **MODERATE**")
    with col4:
        st.markdown("🟢 **LOW**")
    with col5:
        st.markdown("🏛️ **Shelter**")
    
    # Map
    m = create_situation_map(district, risk_score)
    folium_static(m, width=800, height=500)
    
    # Map statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Districts Monitored", "10")
    with col2:
        st.metric("Active Flood Zones", "3" if risk_score >= 60 else "0")
    with col3:
        st.metric("Shelters Available", "3")
    with col4:
        st.metric("Verified Reports", "4")
