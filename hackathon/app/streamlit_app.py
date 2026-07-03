"""
CivicFlood AI - Streamlit Cloud Entry Point
Single source of truth - loads the canonical dashboard
"""

import streamlit as st
import sys
from pathlib import Path
import os

# ============================================================
# FIX: ADD PROJECT ROOT TO PYTHON PATH
# ============================================================
# Get the project root (3 levels up from this file)
# hackathon/app/streamlit_app.py -> project root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Also add the hackathon directory directly
hackathon_path = project_root / "hackathon"
sys.path.insert(0, str(hackathon_path))

# Debug: Print paths (remove after fixing)
# st.write(f"Project root: {project_root}")
# st.write(f"Python path: {sys.path[:3]}")

# ============================================================
# PAGE CONFIG - MUST BE FIRST
# ============================================================
st.set_page_config(
    page_title="CivicFlood AI - National Flood Intelligence",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# API CONFIGURATION
# ============================================================
os.environ["NFCC_API_URL"] = os.getenv(
    "NFCC_API_URL",
    "https://nfcc-platform-production.up.railway.app"
)

# ============================================================
# LOAD CANONICAL DASHBOARD - SINGLE SOURCE OF TRUTH
# ============================================================
try:
    from hackathon.app.pages.dashboard import main
    main()
except Exception as e:
    st.error(f"❌ Dashboard Error: {e}")
    st.info("📱 Please check the deployment configuration.")
    st.code(f"Error details: {str(e)}", language="python")
