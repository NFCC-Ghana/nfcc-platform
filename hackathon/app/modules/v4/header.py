"""Dashboard header module."""

from datetime import datetime

import streamlit as st


def render_header(state):
    """Render the dashboard header."""
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.markdown("# 🌊 CivicFlood AI")
        st.markdown("*National Emergency Operations Center*")

    with col2:
        st.markdown(f"🟢 SYSTEM ACTIVE")
        st.caption(f"🕐 {datetime.now().strftime('%d %b %Y, %H:%M UTC')}")

    with col3:
        st.markdown("**v3.0.0**")
        st.caption("🏆 Ghana AI Innovation Challenge 2026")
        st.caption("🇬🇭 Public Services AI")

    st.caption(f"📊 {state.active_sources_count} Data Sources Active")
    st.divider()
