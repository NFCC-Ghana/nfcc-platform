"""
CivicFlood AI - Streamlit Cloud Entry Point
"""

import streamlit as st
import sys
from pathlib import Path

# ============================================================
# PATH SETUP
# ============================================================
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="CivicFlood AI - National Emergency Operations Center",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# DASHBOARD
# ============================================================
try:
    from hackathon.app.pages.dashboard import main
    main()
except Exception as e:
    st.error(f"🚨 Dashboard error")
    st.exception(e)
