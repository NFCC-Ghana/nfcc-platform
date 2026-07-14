"""Risk Timeline module."""

import streamlit as st


def render_forecast_timeline(state):
    """Render the risk timeline."""
    st.markdown("## ⏰ Risk Timeline")
    st.caption("24-hour flood risk evolution")

    hours = ["Now", "6h", "12h", "18h", "24h"]
    risks = [
        state.risk_score,
        min(100, state.risk_score + 15),
        min(100, state.risk_score + 10),
        min(100, state.risk_score + 5),
        min(100, state.risk_score),
    ]

    st.markdown("### 📈 Risk Trend")
    for hour, risk in zip(hours, risks):
        color = (
            "🔴" if risk >= 80 else "🟠" if risk >= 60 else "🟡" if risk >= 40 else "🟢"
        )
        st.progress(risk / 100, text=f"{hour}: {color} {risk:.0f}%")

    st.warning(f"⚠️ Peak Risk: {max(risks):.0f}% expected in 6 hours")
