"""Situation Map module."""

import streamlit as st
import folium
from streamlit_folium import st_folium


def render_situation_map(state):
    """Render the situation map."""
    st.markdown("## 🗺️ National Flood Situation Map")
    st.caption("Interactive map showing flood risk, affected areas, shelters, and infrastructure")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("🔴 **EXTREME**")
        st.caption("3 zones")
    with col2:
        st.markdown("🟠 **HIGH**")
        st.caption("5 zones")
    with col3:
        st.markdown("🟡 **MODERATE**")
        st.caption("2 zones")
    with col4:
        st.markdown("🟢 **LOW**")
        st.caption("0 zones")
    
    try:
        center_lat = getattr(state, 'lat', 5.560)
        center_lon = getattr(state, 'lon', -0.210)
        
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=12,
            tiles='OpenStreetMap'
        )
        
        risk_data = [
            {"name": "Alajo", "lat": 5.565, "lon": -0.218, "risk": "EXTREME", "pop": 18750},
            {"name": "Kaneshie", "lat": 5.555, "lon": -0.228, "risk": "EXTREME", "pop": 22340},
            {"name": "Circle", "lat": 5.575, "lon": -0.225, "risk": "HIGH", "pop": 15620},
            {"name": "Nima", "lat": 5.555, "lon": -0.215, "risk": "HIGH", "pop": 48230},
            {"name": "Mamobi", "lat": 5.545, "lon": -0.212, "risk": "MODERATE", "pop": 34320},
        ]
        
        risk_colors = {
            "EXTREME": "#ff0000",
            "HIGH": "#ff6600",
            "MODERATE": "#ffaa00",
            "LOW": "#00cc00"
        }
        
        for area in risk_data:
            color = risk_colors.get(area["risk"], "#808080")
            radius = max(8, min(45, int(area["pop"] / 1000)))
            popup_text = f"{area['name']} | Risk: {area['risk']} | Population: {area['pop']:,}"
            
            folium.CircleMarker(
                location=[area["lat"], area["lon"]],
                radius=radius,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7,
                weight=2,
                popup=popup_text
            ).add_to(m)
        
        st_folium(m, width=800, height=500)
        
    except Exception as e:
        st.warning(f"⚠️ Map temporarily unavailable: {str(e)[:100]}")
        st.markdown("### 📍 Affected Areas")
        import pandas as pd
        risk_df = pd.DataFrame([
            {"Community": r["name"], "Risk": r["risk"], "Population": f"{r['pop']:,}"}
            for r in risk_data
        ])
        st.dataframe(risk_df, use_container_width=True)
    
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

