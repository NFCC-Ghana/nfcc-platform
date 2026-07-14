"""Hydrological Intelligence Module - Full river, dam, soil data."""

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st


def render_hydrological_intelligence(district: str) -> None:
    """Render full hydrological intelligence panel."""

    st.markdown("### 🌊 Hydrological Intelligence")

    # Get data (from API in production)
    # For now, use simulated data that matches NFCC capabilities

    # River data
    rivers = [
        {"name": "Odaw", "level": 0.45, "status": "NORMAL", "trend": "STABLE"},
        {"name": "Densu", "level": 1.20, "status": "NORMAL", "trend": "RISING"},
        {"name": "Volta", "level": 3.80, "status": "WARNING", "trend": "RISING"},
        {"name": "White Volta", "level": 2.10, "status": "NORMAL", "trend": "STABLE"},
        {"name": "Black Volta", "level": 4.20, "status": "WARNING", "trend": "RISING"},
        {"name": "Pra", "level": 2.80, "status": "NORMAL", "trend": "STABLE"},
        {"name": "Ankobra", "level": 1.50, "status": "NORMAL", "trend": "FALLING"},
        {"name": "Tano", "level": 3.00, "status": "NORMAL", "trend": "STABLE"},
    ]

    # River status cards
    cols = st.columns(4)
    for i, river in enumerate(rivers[:4]):
        with cols[i]:
            status_color = (
                "🟢"
                if river["status"] == "NORMAL"
                else "🟡" if river["status"] == "WARNING" else "🔴"
            )
            st.markdown(
                f"""
            <div style="background: #f8f9fa; padding: 0.8rem; border-radius: 8px; margin-bottom: 0.5rem;">
                <b>{status_color} {river['name']}</b><br>
                Level: {river['level']}m<br>
                Status: {river['status']}<br>
                <span style="font-size: 0.8rem; color: #666;">{river['trend']}</span>
            </div>
            """,
                unsafe_allow_html=True,
            )

    # Dam data
    dams = [
        {"name": "Akosombo", "capacity": 88.2, "risk": "MEDIUM"},
        {"name": "Kpong", "capacity": 75.0, "risk": "LOW"},
        {"name": "Bui", "capacity": 82.0, "risk": "LOW"},
        {"name": "Bagre", "capacity": 90.0, "risk": "HIGH"},
    ]

    st.markdown("#### 🏗️ Dam Status")
    cols = st.columns(4)
    for i, dam in enumerate(dams):
        with cols[i]:
            risk_color = (
                "🟢"
                if dam["risk"] == "LOW"
                else "🟡" if dam["risk"] == "MEDIUM" else "🔴"
            )
            st.markdown(
                f"""
            <div style="background: #f8f9fa; padding: 0.8rem; border-radius: 8px;">
                <b>{dam['name']}</b><br>
                {dam['capacity']}% full<br>
                Risk: {risk_color} {dam['risk']}
            </div>
            """,
                unsafe_allow_html=True,
            )

    # Soil moisture
    soil_data = {
        "Accra Central": 85,
        "Accra West": 78,
        "Accra East": 65,
        "Tema": 72,
        "Kumasi": 55,
        "Tamale": 45,
    }

    st.markdown("#### 💧 Soil Moisture")

    soil_df = pd.DataFrame(
        {"District": list(soil_data.keys()), "Saturation (%)": list(soil_data.values())}
    )

    fig = px.bar(
        soil_df,
        x="District",
        y="Saturation (%)",
        title="Soil Saturation by District",
        color="Saturation (%)",
        color_continuous_scale="RdYlGn_r",
        range_color=[30, 100],
    )

    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)
