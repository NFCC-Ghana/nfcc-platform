"""
Risk Explanation Engine - Detailed risk breakdown with thresholds.
"""

import pandas as pd
import plotly.express as px
import streamlit as st


def get_risk_breakdown(
    district: str, rainfall: float, soil_saturation: float, river_level: float
) -> dict:
    """Get detailed risk breakdown with thresholds."""

    # In production, this would come from the NFCC API
    return {
        "total_risk": 90.6,
        "drivers": {
            "Rainfall Intensity": {
                "weight": 35,
                "value": rainfall,
                "threshold": 50,
                "status": "CRITICAL",
                "description": f"{rainfall}mm rainfall exceeds threshold",
            },
            "Soil Saturation": {
                "weight": 25,
                "value": soil_saturation,
                "threshold": 70,
                "status": "CRITICAL",
                "description": f"{soil_saturation}% saturation (above 70% threshold)",
            },
            "River Levels": {
                "weight": 20,
                "value": river_level,
                "threshold": 1.5,
                "status": "MODERATE",
                "description": f"{river_level}m (within normal range)",
            },
            "Dam Risk": {
                "weight": 10,
                "value": 85,
                "threshold": 80,
                "status": "HIGH",
                "description": "Akosombo at 88.2% capacity",
            },
            "Community Reports": {
                "weight": 10,
                "value": 4,
                "threshold": 2,
                "status": "ELEVATED",
                "description": "4 active reports (2 verified)",
            },
        },
    }


def render_risk_explainer(
    district: str, rainfall: float, soil_saturation: float, river_level: float
) -> None:
    """Render risk explanation panel."""

    st.markdown("### 🔍 Risk Explanation Engine")

    data = get_risk_breakdown(district, rainfall, soil_saturation, river_level)

    st.markdown(f"#### Total Risk: **{data['total_risk']:.1f}%**")

    # Create driver breakdown
    drivers = []
    for name, info in data["drivers"].items():
        drivers.append(
            {
                "Driver": name,
                "Weight": info["weight"],
                "Value": info["value"],
                "Threshold": info["threshold"],
                "Status": info["status"],
                "Description": info["description"],
            }
        )

    df = pd.DataFrame(drivers)

    # Color coding
    def get_color(status):
        colors = {
            "CRITICAL": "#ff0000",
            "HIGH": "#ff6600",
            "MODERATE": "#ffaa00",
            "ELEVATED": "#ffcc00",
            "NORMAL": "#00cc00",
        }
        return colors.get(status, "#666666")

    # Display drivers
    for _, row in df.iterrows():
        color = get_color(row["Status"])
        st.markdown(
            f"""
        <div style="background: #f8f9fa; padding: 0.8rem; border-radius: 8px; margin-bottom: 0.5rem; border-left: 4px solid {color};">
            <b>{row['Driver']}</b> <span style="font-size: 0.8rem; color: #666;">({row['Weight']}%)</span><br>
            Value: {row['Value']} • Threshold: {row['Threshold']} • Status: <span style="color: {color};"><b>{row['Status']}</b></span><br>
            <span style="font-size: 0.85rem; color: #555;">{row['Description']}</span>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # Visual breakdown
    fig = px.bar(
        df,
        x="Driver",
        y="Weight",
        title="Risk Driver Contributions",
        color="Status",
        color_discrete_map={
            "CRITICAL": "#ff0000",
            "HIGH": "#ff6600",
            "MODERATE": "#ffaa00",
            "ELEVATED": "#ffcc00",
            "NORMAL": "#00cc00",
        },
        text=df["Weight"].apply(lambda x: f"{x}%"),
    )

    fig.update_traces(textposition="outside")
    fig.update_layout(height=300, yaxis_title="Contribution (%)", xaxis_title="")

    st.plotly_chart(fig, use_container_width=True)
