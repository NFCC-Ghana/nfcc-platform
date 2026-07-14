"""
CivicFlood AI - Streamlit Entry Point
Single authoritative entry point for the enterprise dashboard.
Handles both local and Render deployments.
"""

import sys
from pathlib import Path

import streamlit as st

# ============================================================
# DYNAMIC PATH HANDLING - WORKS EVERYWHERE
# ============================================================

# Get the directory containing this file
current_dir = Path(__file__).resolve().parent

# Project root (where hackathon/ is located)
project_root = current_dir.parent.parent

# Add all possible paths
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "hackathon"))
sys.path.insert(0, str(current_dir.parent))
sys.path.insert(0, str(current_dir))

# ============================================================
# SINGLE PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="CivicFlood AI - National Emergency Operations Center",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# LOAD THE ENTERPRISE DASHBOARD
# ============================================================
try:
    # Try the standard import path
    from hackathon.app.pages.dashboard import main

    main()
except ImportError as e:
    try:
        # Try the relative import path (when running from hackathon/)
        from app.pages.dashboard import main

        main()
    except ImportError as e2:
        st.error("🚨 Could not load the dashboard. Please check the deployment.")
        st.code(f"First error: {e}")
        st.code(f"Second error: {e2}")
        st.code(f"Python path: {sys.path[:5]}")
        raise
