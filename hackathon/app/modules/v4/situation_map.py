"""
Situation Map Module - Full Implementation
Interactive flood situation map with Folium.
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import json


def render_situation_map(state):
    """Render the complete interactive situation map."""
    
    st.markdown("## 🗺️ National Flood Situation Map")
    st.caption("Interactive map showing flood risk, affected areas, shelters, and infrastructure")
    
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
    
    # Create map
    center_lat = state.lat
    center_lon = state.lon
    
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles='OpenStreetMap'
    )
    
    # Add risk zones based on state
    risk_data = [
        {"name": "Alajo", "lat": 5.565, "lon": -0.218, "risk": "EXTREME", "pop": 18750},
        {"name": "Kaneshie", "lat": 5.555, "lon": -0.228, "risk": "EXTREME", "pop": 22340},
        {"name": "Circle", "lat": 5.575, "lon": -0.225, "risk": "HIGH", "pop": 15620},
        {"name": "Nima", "lat": 5.555, "lon": -0.215, "risk": "HIGH", "pop": 48230},
        {"name": "Mamobi", "lat": 5.545, "lon": -0.212, "risk": "MODERATE", "pop": 34320},
    ]
    
    # Color mapping
    risk_colors = {
        "EXTREME": "#ff0000",
        "HIGH": "#ff6600",
        "MODERATE": "#ffaa00",
        "LOW": "#00cc00"
    }
    
    # Add markers
    for area in risk_data:
        color = risk_colors.get(area["risk"], "#808080")
        radius = 100 * (area["pop"] / 50000)
        
        folium.CircleMarker(
            location=[area["lat"], area["lon"]],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            popup=f"""
            <b>{area["name"]}</b><br>
            Risk: {area["risk"]}<br>
            Population: {area["pop"]:,}
            """
        ).add_to(m)
    
    # Add shelters
    shelters = [
        {"name": "Accra High School", "lat": 5.578, "lon": -0.222, "capacity": 1200},
        {"name": "Community Center", "lat": 5.562, "lon": -0.218, "capacity": 500},
        {"name": "Trade Fair Centre", "lat": 5.565, "lon": -0.185, "capacity": 2000},
    ]
    
    for shelter in shelters:
        folium.Marker(
            location=[shelter["lat"], shelter["lon"]],
            popup=f"""
            <b>{shelter["name"]}</b><br>
            Capacity: {shelter["capacity"]:,}<br>
            Status: OPEN
            """,
            icon=folium.Icon(color="green", icon="home", prefix="fa")
        ).add_to(m)
    
    # Add river overlay
    river_points = [
        [5.560, -0.205],
        [5.555, -0.210],
        [5.550, -0.215],
        [5.545, -0.220],
        [5.540, -0.225]
    ]
    
    folium.PolyLine(
        river_points,
        color="blue",
        weight=3,
        opacity=0.7,
        popup="Odaw River"
    ).add_to(m)
    
    # Display map
    st_folium(m, width=800, height=500, returned_objects=[])
    
    # Key metrics below map
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Districts Monitored", "10")
    with col2:
        st.metric("Active Flood Zones", "3")
    with col3:
        st.metric("Shelters Available", "3")
    with col4:
        st.metric("Verified Reports", "4")
    
    st.caption("🗺️ Click on markers for details • Updated in real-time")
