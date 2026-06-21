"""
CivicFlood AI - Streamlit Cloud Entry Point
Uses the complete enhanced dashboard
"""

import streamlit as st
import sys
from pathlib import Path
import os

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
# ADD PROJECT ROOT TO PATH
# ============================================================
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# ============================================================
# API CONFIGURATION
# ============================================================
os.environ["NFCC_API_URL"] = os.getenv(
    "NFCC_API_URL", 
    "https://nfcc-platform-production.up.railway.app"
)

# ============================================================
# RUN THE COMPLETE DASHBOARD
# ============================================================
try:
    from hackathon.app.pages.dashboard_enhanced import main
    main()
except ImportError as e:
    st.error(f"Error loading dashboard: {e}")
    st.info("Falling back to simple dashboard...")
    try:
        from hackathon.app.pages.dashboard import main
        main()
    except ImportError:
        st.title("🌊 CivicFlood AI")
        st.markdown("### National Flood Intelligence Platform")
        st.markdown("**Ghana AI Innovation Challenge 2026**")
        st.info("📱 Dashboard loading... Please check your deployment configuration.")
        st.markdown("---")
        st.markdown("🔗 Backend API: https://nfcc-platform-production.up.railway.app")

