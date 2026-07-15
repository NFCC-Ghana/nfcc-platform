import folium
import streamlit as st
from streamlit_folium import st_folium

def render_situation_map(state=None):
    """
    DIAGNOSTIC VERSION - Minimal map to test if st_folium works at all.
    This will tell us exactly where the failure is happening.
    """
    st.write("🔍 Map function called")
    
    # Create the simplest possible map
    m = folium.Map(
        location=[5.6037, -0.1870],  # Accra
        zoom_start=11,
    )
    
    # Add a simple marker
    folium.Marker(
        [5.6037, -0.1870],
        popup="Accra, Ghana"
    ).add_to(m)
    
    st.write("🗺️ About to render map...")
    
    # Render the map - no returned_objects, no checking
    st_folium(
        m,
        width=900,
        height=600,
    )
    
    st.write("✅ Map finished rendering")

def render_minimal_map():
    """Same as above for testing."""
    render_situation_map()

def render_map_fallback():
    """Fallback if map fails."""
    st.warning("⚠️ Map unavailable - showing data instead")
    st.dataframe([
        {"Location": "Accra", "Lat": 5.6037, "Lon": -0.1870, "Status": "Active"},
        {"Location": "Kumasi", "Lat": 6.6961, "Lon": -1.6134, "Status": "Active"},
    ])
