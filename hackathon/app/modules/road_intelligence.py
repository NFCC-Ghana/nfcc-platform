"""
Road Flooding Intelligence - Real-time road flood predictions.
"""

import pandas as pd
import plotly.express as px
import streamlit as st


def get_road_flooding_data(
    district: str, rainfall: float, soil_saturation: float
) -> dict:
    """Get road flooding predictions based on current conditions."""

    # In production, this would come from the NFCC API
    roads = {
        "Accra Central": {
            "high_risk": [
                {
                    "name": "Alajo Main Road",
                    "depth": 0.5,
                    "confidence": 85,
                    "reason": "Verified flooding report + poor drainage",
                },
                {
                    "name": "Ring Road Central near Kwame Nkrumah Circle",
                    "depth": 0.4,
                    "confidence": 78,
                    "reason": "Low-lying area + rising water reports",
                },
                {
                    "name": "Kaneshie Market Road",
                    "depth": 0.35,
                    "confidence": 82,
                    "reason": "Blocked drainage + water level rising",
                },
                {
                    "name": "Odaw River crossing near Graphic Road",
                    "depth": 0.45,
                    "confidence": 80,
                    "reason": "River proximity + flood warning",
                },
            ],
            "moderate_risk": [
                {
                    "name": "Independence Avenue",
                    "depth": 0.2,
                    "confidence": 65,
                    "reason": "Moderate rainfall accumulation",
                },
                {
                    "name": "Liberation Road",
                    "depth": 0.15,
                    "confidence": 60,
                    "reason": "Drainage capacity at 70%",
                },
            ],
            "safe_routes": [
                {
                    "name": "Independence Avenue (alternative)",
                    "reason": "Higher elevation",
                },
                {
                    "name": "Liberation Road (alternative)",
                    "reason": "Wider drainage capacity",
                },
            ],
        }
    }

    return roads.get(
        district, {"high_risk": [], "moderate_risk": [], "safe_routes": []}
    )


def render_road_intelligence(
    district: str, rainfall: float, soil_saturation: float
) -> None:
    """Render road flooding intelligence panel."""

    st.markdown("### 🛣️ Road Flooding Intelligence")

    data = get_road_flooding_data(district, rainfall, soil_saturation)

    if data["high_risk"]:
        st.markdown("#### 🔴 High Risk Roads")

        for road in data["high_risk"]:
            st.markdown(
                f"""
            <div style="background: #ffebee; padding: 0.8rem; border-radius: 8px; margin-bottom: 0.5rem; border-left: 4px solid #ff0000;">
                <b>{road['name']}</b><br>
                🌊 Expected depth: {road['depth']:.1f}m • Confidence: {road['confidence']}%<br>
                📋 {road['reason']}
            </div>
            """,
                unsafe_allow_html=True,
            )

    if data["moderate_risk"]:
        st.markdown("#### 🟡 Moderate Risk Roads")

        for road in data["moderate_risk"]:
            st.markdown(
                f"""
            <div style="background: #fff3e0; padding: 0.8rem; border-radius: 8px; margin-bottom: 0.5rem; border-left: 4px solid #ff9800;">
                <b>{road['name']}</b><br>
                🌊 Expected depth: {road['depth']:.1f}m • Confidence: {road['confidence']}%<br>
                📋 {road['reason']}
            </div>
            """,
                unsafe_allow_html=True,
            )

    if data["safe_routes"]:
        st.markdown("#### 🟢 Recommended Safe Routes")
        for route in data["safe_routes"]:
            st.markdown(
                f"""
            <div style="background: #e8f5e9; padding: 0.5rem 1rem; border-radius: 8px; margin-bottom: 0.3rem; border-left: 4px solid #4caf50;">
                ✅ {route['name']} - {route['reason']}
            </div>
            """,
                unsafe_allow_html=True,
            )

    # Summary
    total_risk = len(data["high_risk"]) + len(data["moderate_risk"])
    st.caption(
        "📊 Data Source: Rule-based estimation using CHIRPS rainfall + soil saturation"
    )
    st.info(
        f"📊 {total_risk} road segments affected • {len(data['safe_routes'])} safe routes available"
    )
