"""
Operations Module - Full Implementation
Emergency shelters, evacuation routes, and resource management.
"""

import streamlit as st
import pandas as pd


def render_operations(state):
    """Render the complete operations section."""
    
    st.markdown("## 🚗 Operations & Evacuation")
    st.caption("Shelters, evacuation routes, and resource status")
    
    # Shelters
    st.markdown("### 🏛️ Emergency Shelters")
    
    shelters = [
        {"name": "Accra High School", "status": "OPEN", "distance": "1.2 km", 
         "capacity": 1200, "available": 850, "color": "success"},
        {"name": "Community Center", "status": "OPEN", "distance": "2.5 km",
         "capacity": 500, "available": 320, "color": "success"},
        {"name": "Trade Fair Centre", "status": "PREPARING", "distance": "4.0 km",
         "capacity": 2000, "available": 2000, "color": "warning"},
    ]
    
    for shelter in shelters:
        if shelter["color"] == "success":
            st.success(f"**{shelter['name']}** 🟢 {shelter['status']}")
        elif shelter["color"] == "warning":
            st.warning(f"**{shelter['name']}** 🟡 {shelter['status']}")
        else:
            st.error(f"**{shelter['name']}** 🔴 {shelter['status']}")
        
        st.caption(f"📍 {shelter['distance']} • Capacity: {shelter['capacity']:,}")
        st.caption(f"🏠 Available: {shelter['available']:,} spaces")
        st.divider()
    
    # Evacuation Routes
    st.markdown("### 🗺️ Safe Evacuation Routes")
    
    routes = [
        {"from": "Alajo", "to": "Accra High School", "via": "Ring Road", "time": "15 min"},
        {"from": "Kaneshie", "to": "Community Center", "via": "Winneba Road", "time": "20 min"},
        {"from": "Circle", "to": "Trade Fair Centre", "via": "Independence Avenue", "time": "25 min"},
    ]
    
    for route in routes:
        st.caption(f"🚗 **{route['from']}** → **{route['to']}**")
        st.caption(f"   Via: {route['via']} • {route['time']}")
        st.divider()
    
    # Resources
    st.markdown("### 📦 Resource Status")
    
    resources = [
        {"name": "Rescue Boats", "available": 3, "status": "Ready", "emoji": "🚤"},
        {"name": "Ambulances", "available": 5, "status": "Deployed", "emoji": "🚑"},
        {"name": "Pumps", "available": 10, "status": "Available", "emoji": "💧"},
        {"name": "Rescue Teams", "available": 4, "status": "Active", "emoji": "👥"},
        {"name": "Sandbags", "available": 5000, "status": "Ready", "emoji": "🟫"},
        {"name": "Life Jackets", "available": 200, "status": "Available", "emoji": "🦺"},
    ]
    
    col1, col2, col3 = st.columns(3)
    for i, resource in enumerate(resources):
        with [col1, col2, col3][i % 3]:
            st.metric(
                f"{resource['emoji']} {resource['name']}",
                resource['available'],
                resource['status']
            )
