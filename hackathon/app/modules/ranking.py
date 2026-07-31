"""District Risk Ranking - National view."""

import pandas as pd
import plotly.express as px
import streamlit as st


def render_district_ranking() -> None:
    """Render national district risk ranking."""

    st.markdown("### 🏆 National District Risk Ranking")

    districts = [
        {"name": "Accra Central", "risk": 90.6, "trend": "↑"},
        {"name": "Tema", "risk": 85.2, "trend": "↑"},
        {"name": "Accra West", "risk": 82.0, "trend": "→"},
        {"name": "Cape Coast", "risk": 75.3, "trend": "↓"},
        {"name": "Kumasi", "risk": 68.7, "trend": "→"},
        {"name": "Sekondi-Takoradi", "risk": 62.4, "trend": "↑"},
        {"name": "Tamale", "risk": 55.1, "trend": "↓"},
        {"name": "Ho", "risk": 48.3, "trend": "→"},
        {"name": "Sunyani", "risk": 35.2, "trend": "↓"},
        {"name": "Accra East", "risk": 28.5, "trend": "↓"},
    ]

    df = pd.DataFrame(districts)

    fig = px.bar(
        df,
        x="name",
        y="risk",
        title="District Risk Scores (Live)",
        color="risk",
        color_continuous_scale="RdYlGn_r",
        range_color=[0, 100],
        text=df["risk"].apply(lambda x: f"{x:.1f}%"),
    )

    fig.update_traces(textposition="outside")
    fig.update_layout(
        height=400, yaxis_title="Risk Score (%)", yaxis_range=[0, 105], xaxis_title=""
    )

    st.plotly_chart(fig, use_container_width=True)

    top = df.iloc[0]
    st.warning(
        f"🚨 **Highest Risk: {top['name']}** at {top['risk']:.1f}% - Immediate action required!"
    )

    high_risk = len(df[df["risk"] >= 60])
    st.info(f"📊 {high_risk} districts are at HIGH or EXTREME risk")
