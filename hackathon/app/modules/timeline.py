"""Flood Timeline Prediction - 6h, 12h, 24h, 48h."""

import pandas as pd
import plotly.express as px
import streamlit as st


def render_timeline(current_risk: float) -> None:
    """Render flood timeline prediction."""

    st.markdown("### ⏰ Flood Timeline")

    timeline = [
        {"time": "Now", "risk": current_risk, "status": "HIGH"},
        {
            "time": "+6 Hours",
            "risk": min(100, current_risk * 1.15),
            "status": "EXTREME",
        },
        {
            "time": "+12 Hours",
            "risk": min(100, current_risk * 1.25),
            "status": "EXTREME",
        },
        {"time": "+24 Hours", "risk": min(100, current_risk * 1.1), "status": "HIGH"},
        {
            "time": "+48 Hours",
            "risk": max(20, current_risk * 0.8),
            "status": "MODERATE",
        },
    ]

    df = pd.DataFrame(timeline)

    colors = [
        (
            "#ff0000"
            if r >= 80
            else "#ff6600" if r >= 60 else "#ffaa00" if r >= 40 else "#00cc00"
        )
        for r in df["risk"]
    ]

    fig = px.bar(
        df,
        x="time",
        y="risk",
        title="Flood Risk Timeline (Next 48 Hours)",
        color="risk",
        color_continuous_scale="RdYlGn_r",
        range_color=[0, 100],
        text=df["risk"].apply(lambda x: f"{x:.0f}%"),
    )

    fig.update_traces(textposition="outside")
    fig.update_layout(
        height=300, yaxis_title="Risk Score (%)", yaxis_range=[0, 105], showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

    peak = max(timeline, key=lambda x: x["risk"])
    st.warning(f"⚠️ Peak risk of {peak['risk']:.0f}% expected at {peak['time']}")
