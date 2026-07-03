"""
CivicFlood AI - Streamlit Cloud Entry Point
Single source of truth - loads the canonical dashboard
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
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

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
