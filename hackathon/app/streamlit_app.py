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

# ============================================================
# FIX: Add the project root to Python path
# This works whether you run from the root or from hackathon/
# ============================================================

# Get the project root (where hackathon/ is located)
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent  # Go up from app/ to project root

# If project_root doesn't contain hackathon/, try going up more
if not (project_root / "hackathon").exists():
    project_root = current_file.parent.parent  # Try going up from app/ to hackathon/

# Add project root to path
sys.path.insert(0, str(project_root))

# Add hackathon directory to path
hackathon_path = project_root / "hackathon"
if hackathon_path.exists():
    sys.path.insert(0, str(hackathon_path))

# For debugging - remove in production
logger.info(f"Project root: {project_root}")
logger.info(f"Python path: {sys.path[:3]}")

# ============================================================
# SINGLE PAGE CONFIG - ONLY HERE
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
    # Try importing from hackathon.app.pages (when run from root)
    from hackathon.app.pages.dashboard import main
except ImportError:
    try:
        # Try importing from app.pages (when run from hackathon/)
        from app.pages.dashboard import main
    except ImportError:
        logger.error("Could not import dashboard. Please check the path.")
        st.error("🚨 Could not load the dashboard. Please check the deployment.")
        raise

    main()
