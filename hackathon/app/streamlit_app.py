"""
CivicFlood AI - Streamlit Entry Point
Single authoritative entry point for the enterprise dashboard.
"""

import streamlit as st

# ============================================================
# SINGLE PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="CivicFlood AI - National Emergency Operations Center",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# LOAD THE ENTERPRISE DASHBOARD
# ============================================================
try:
    from hackathon.app.pages.dashboard import main
    main()
except Exception as e:
    st.error("🚨 Dashboard encountered an error. Please check the logs.")
    st.exception(e)
