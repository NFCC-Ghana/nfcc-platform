"""Evacuation Routes and Shelter Locations."""

import streamlit as st


def render_evacuation_info(district: str) -> None:
    """Render evacuation routes and shelters."""

    st.markdown("### 🚗 Evacuation Intelligence")

    shelters = {
        "Accra Central": [
            {"name": "Accra High School", "distance": 1.2, "capacity": 1200},
            {"name": "Community Center", "distance": 2.5, "capacity": 500},
            {"name": "Trade Fair Centre", "distance": 4.0, "capacity": 2000},
        ],
        "Accra West": [
            {"name": "Dansoman Community Center", "distance": 1.5, "capacity": 600}
        ],
        "Tema": [{"name": "Tema Sports Stadium", "distance": 2.0, "capacity": 1500}],
    }

    district_shelters = shelters.get(
        district, [{"name": "No shelters listed", "distance": 0, "capacity": 0}]
    )

    st.markdown("#### 🏛️ Nearest Shelters")

    cols = st.columns(3)
    for i, shelter in enumerate(district_shelters[:3]):
        with cols[i]:
            st.markdown(
                f"""
            <div style="background: #f8f9fa; padding: 0.8rem; border-radius: 8px;">
                <b>{shelter['name']}</b><br>
                📍 {shelter['distance']}km away<br>
                🏠 Capacity: {shelter['capacity']}
            </div>
            """,
                unsafe_allow_html=True,
            )

    st.markdown("#### 🗺️ Safe Evacuation Routes")

    routes = [
        {
            "from": "Alajo",
            "to": "Accra High School",
            "via": "Ring Road",
            "time": "15 min",
        },
        {
            "from": "Kaneshie",
            "to": "Community Center",
            "via": "Winneba Road",
            "time": "20 min",
        },
        {
            "from": "Circle",
            "to": "Trade Fair Centre",
            "via": "Independence Avenue",
            "time": "25 min",
        },
    ]

    for route in routes:
        st.markdown(
            f"""
        <div style="background: #e8f5e9; padding: 0.5rem 1rem; border-radius: 8px; margin-bottom: 0.3rem; border-left: 4px solid #4caf50;">
            <b>{route['from']}</b> → {route['to']}<br>
            Via: {route['via']} • Estimated: {route['time']}
        </div>
        """,
            unsafe_allow_html=True,
        )
