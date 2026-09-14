"""Risk display module."""

import streamlit as st


def render_risk_display(state):
    """Render the risk display section."""
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"## {state.risk_emoji} Risk Score")
        st.markdown(
            f"<h1 style='color:{state.risk_color};'>{state.risk_score:.1f}%</h1>",
            unsafe_allow_html=True,
        )
        st.caption(f"Category: **{state.risk_category}**")

    with col2:
        st.metric("Population", f"{state.population:,}", "District total")
        st.metric("Rainfall", f"{state.rainfall_mm} mm", "24-hour accumulation")

    with col3:
        st.markdown(f"## {state.river_emoji} River Status")
        st.markdown(f"**{state.river_name}**")
        st.caption(f"Level: {state.river_level_m}m • {state.river_status}")
