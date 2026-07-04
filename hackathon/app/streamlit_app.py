"""
CivicFlood AI - Streamlit Cloud Entry Point

This is the SINGLE entry point for the application.
All dashboard logic is in hackathon/app/pages/dashboard.py
"""

import streamlit as st
import sys
import logging
from pathlib import Path
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Add hackathon directory to path
hackathon_path = project_root / "hackathon"
sys.path.insert(0, str(hackathon_path))

# ============================================================
# PAGE CONFIG - ONLY HERE
# ============================================================
st.set_page_config(
    page_title="CivicFlood AI - National Emergency Operations Center",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# APPLICATION ENTRY
# ============================================================

try:
    from hackathon.app.pages.dashboard import main
    main()
except ImportError as e:
    logger.error(f"Import error: {e}")
    st.error("🚨 Could not load the dashboard. Please check the deployment.")
    st.exception(e)
except Exception as e:
    logger.exception("Dashboard error")
    st.error("🚨 Dashboard encountered an error. Please check the logs.")
    st.exception(e)
