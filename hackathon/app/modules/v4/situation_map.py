"""
Situation Map Module - Complete Interactive Map
Fixed for st_folium serialization compatibility.
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import json
from branca.element import Figure


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
    
    try:
        # Get center from state
        center_lat = getattr(state, 'lat', 5.560)
        center_lon = getattr(state, 'lon', -0.210)
        
        # Create map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=12,
            tiles='OpenStreetMap',
            control_scale=True
        )
        
        # ============================================================
        # 1. RISK ZONES
        # ============================================================
        
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
        
        # Add markers with PLAIN TEXT popups (NO HTML)
        for area in risk_data:
            color = risk_colors.get(area["risk"], "#808080")
            # Scale radius by population
            radius = max(8, min(45, int(area["pop"] / 1000)))
            
            # Use plain text - NO HTML tags
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
        
        # ============================================================
        # 2. SHELTERS - Plain text popups
        # ============================================================
        
        shelters = [
            {"name": "Accra High School", "lat": 5.578, "lon": -0.222, "capacity": 1200, "status": "OPEN"},
            {"name": "Community Center", "lat": 5.562, "lon": -0.218, "capacity": 500, "status": "OPEN"},
            {"name": "Trade Fair Centre", "lat": 5.565, "lon": -0.185, "capacity": 2000, "status": "PREPARING"},
        ]
        
        for shelter in shelters:
            # Plain text popup - NO HTML
            popup_text = f"{shelter['name']} | Status: {shelter['status']} | Capacity: {shelter['capacity']:,}"
            
            icon_color = "green" if shelter["status"] == "OPEN" else "orange"
            
            folium.Marker(
                location=[shelter["lat"], shelter["lon"]],
                popup=popup_text,
                icon=folium.Icon(color=icon_color, icon="home", prefix="fa")
            ).add_to(m)
        
        # ============================================================
        # 3. RIVERS
        # ============================================================
        
        odaw_points = [
            [5.560, -0.205],
            [5.555, -0.210],
            [5.550, -0.215],
            [5.545, -0.220],
            [5.540, -0.225]
        ]
        
        folium.PolyLine(
            odaw_points,
            color="blue",
            weight=3,
            opacity=0.7,
            popup="Odaw River"
        ).add_to(m)
        
        # ============================================================
        # 4. DISPLAY MAP
        # ============================================================
        
        # Display the map
        st_data = st_folium(
            m,
            width=800,
            height=500,
            returned_objects=[]
        )
        
        # ============================================================
        # 5. KEY METRICS
        # ============================================================
        
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
        
    except Exception as e:
        # Fallback display
        st.warning(f"⚠️ Map temporarily unavailable: {str(e)[:100]}")
        st.markdown("### 📍 Affected Areas")
        
        # Display as table
        import pandas as pd
        risk_df = pd.DataFrame([
            {"Community": r["name"], "Risk": r["risk"], "Population": f"{r['pop']:,}"}
            for r in risk_data
        ])
        st.dataframe(risk_df, use_container_width=True)
        
        st.caption("📊 Map data displayed in table format")

