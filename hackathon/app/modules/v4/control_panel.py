"""Control panel module with sidebar."""

import streamlit as st


def render_control_panel():
    """Render the sidebar control panel."""
    with st.sidebar:
        st.markdown("## 🎯 Control Panel")
        
        district = st.selectbox(
            "📍 Select District",
            [
                "Accra Central",
                "Accra West",
                "Accra East",
                "Tema",
                "Kumasi",
                "Tamale"
            ],
            index=0
        )
        
        st.markdown("### 🌧️ Rainfall (mm)")
        rainfall_mm = st.slider(
            "Rainfall amount (mm)",
            min_value=0,
            max_value=200,
            value=75,
            help="24-hour cumulative rainfall"
        )
        
        st.divider()
        
        st.markdown("### 📡 Data Sources")
        sources = [
            ("🛰️", "CHIRPS Rainfall", True),
            ("🌤️", "Open-Meteo Forecast", True),
            ("💧", "NASA SMAP", True),
            ("📡", "Sentinel-1 SAR", True),
            ("🌊", "Ghana River Gauges", True),
            ("🏗️", "Dam Database", True),
        ]
        
        for emoji, name, active in sources:
            status = "🟢" if active else "🔴"
            st.markdown(f"{status} {emoji} {name}")
        
        st.divider()
        
        st.markdown("### ✅ API Connected")
        st.code("https://nfcc-platform-production.up.railway.app", language="text")
        
        st.divider()
        st.caption("🏆 Ghana AI Innovation Challenge 2026")
    
    return {"district": district, "rainfall_mm": rainfall_mm}
