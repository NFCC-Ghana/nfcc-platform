"""
Operations Panel - Shelters, routes, resources, logistics
"""

import streamlit as st

def render_operations_panel(district: str) -> None:
    """Render operations and evacuation panel."""
    
    st.markdown("### 🚗 Operations & Evacuation")
    st.caption("Shelters, evacuation routes, and resource status")
    
    # Shelters
    st.markdown("#### 🏛️ Emergency Shelters")
    
    shelters = [
        {"name": "Accra High School", "distance": "1.2 km", "capacity": "1,200", "status": "OPEN"},
        {"name": "Community Center", "distance": "2.5 km", "capacity": "500", "status": "OPEN"},
        {"name": "Trade Fair Centre", "distance": "4.0 km", "capacity": "2,000", "status": "PREPARING"}
    ]
    
    for shelter in shelters:
        status_color = "🟢" if shelter["status"] == "OPEN" else "🟡"
        st.markdown(f"""
        <div style="background: #f8f9fa; padding: 0.5rem 1rem; border-radius: 8px; margin-bottom: 0.3rem; border-left: 4px solid {'#4caf50' if shelter['status'] == 'OPEN' else '#ff9800'};">
            <b>{shelter['name']}</b>
            <span style="float: right;">{status_color} {shelter['status']}</span><br>
            <span style="font-size: 0.85rem; color: #666;">📍 {shelter['distance']} • Capacity: {shelter['capacity']}</span>
        </div>
        """, unsafe_allow_html=True)
    
    # Evacuation routes
    st.markdown("#### 🗺️ Safe Evacuation Routes")
    
    routes = [
        {"from": "Alajo", "to": "Accra High School", "via": "Ring Road", "time": "15 min"},
        {"from": "Kaneshie", "to": "Community Center", "via": "Winneba Road", "time": "20 min"},
        {"from": "Circle", "to": "Trade Fair Centre", "via": "Independence Avenue", "time": "25 min"}
    ]
    
    for route in routes:
        st.markdown(f"""
        <div style="background: #e8f5e9; padding: 0.3rem 1rem; border-radius: 6px; margin-bottom: 0.2rem; border-left: 4px solid #4caf50;">
            <b>{route['from']}</b> → {route['to']}
            <span style="float: right; font-size: 0.85rem;">Via: {route['via']} • {route['time']}</span>
        </div>
        """, unsafe_allow_html=True)
    
    # Resource status
    st.markdown("#### 📦 Resource Status")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Rescue Boats", "3", delta="🚤 Ready")
    with col2:
        st.metric("Ambulances", "5", delta="🚑 Deployed")
    with col3:
        st.metric("Pumps", "10", delta="💧 Available")
    with col4:
        st.metric("Rescue Teams", "4", delta="👥 Active")
