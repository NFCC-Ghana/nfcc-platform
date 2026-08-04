"""Forecast Module - 24h/48h/72h predictions."""

from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st


def render_forecast(district: str, current_risk: float) -> None:
    """Render forecast panel."""

    st.markdown("### 📈 Flood Forecast")

    # Simulate forecast data (in production: from NFCC model)
    hours = [6, 12, 24, 48, 72]
    risk_values = [
        current_risk,
        min(100, current_risk * 1.1),
        min(100, current_risk * 1.2),
        min(100, current_risk * 0.9),
        min(100, current_risk * 0.85),
    ]

    # Trend interpretation
    trends = ["Current", "Rising", "Peak", "Falling", "Stabilizing"]

    df = pd.DataFrame(
        {"Timeframe": [f"{h}h" for h in hours], "Risk": risk_values, "Trend": trends}
    )

    # Color based on risk
    colors = [
        (
            "#ff0000"
            if r >= 80
            else "#ff6600" if r >= 60 else "#ffaa00" if r >= 40 else "#00cc00"
        )
        for r in risk_values
    ]

    fig = px.line(
        df, x="Timeframe", y="Risk", title="Risk Forecast (Next 72 Hours)", markers=True
    )

    fig.update_traces(line_color="#0f3460", line_width=3)
    fig.update_layout(height=250, yaxis_range=[0, 100], yaxis_title="Risk Score (%)")

    # Add risk threshold lines
    fig.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="EXTREME")
    fig.add_hline(y=60, line_dash="dash", line_color="orange", annotation_text="HIGH")

    st.plotly_chart(fig, use_container_width=True)

    # Summary
    peak_risk = max(risk_values)
    peak_time = df[df["Risk"] == peak_risk]["Timeframe"].iloc[0]

    if peak_risk >= 80:
        st.error(f"⚠️ Peak risk of {peak_risk:.1f}% expected at {peak_time}")
    elif peak_risk >= 60:
        st.warning(f"⚠️ Peak risk of {peak_risk:.1f}% expected at {peak_time}")
    else:
        st.info(f"ℹ️ Peak risk of {peak_risk:.1f}% expected at {peak_time}")
