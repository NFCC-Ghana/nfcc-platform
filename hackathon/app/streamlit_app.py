"""
CivicFlood AI - Streamlit Cloud Entry Point
Shows real error messages for debugging
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

st.title("🌊 CivicFlood AI")
st.markdown("### National Flood Intelligence Platform")
st.markdown("**Ghana AI Innovation Challenge 2026**")

# Show Python version for debugging
st.caption(f"🐍 Python: {sys.version[:20]}")

# ============================================================
# ATTEMPT TO LOAD DASHBOARD WITH DETAILED ERRORS
# ============================================================

st.divider()
st.markdown("🔄 **Loading dashboard...**")

try:
    # Try to import the enhanced dashboard
    from hackathon.app.pages_disabled.dashboard_enhanced import main
    st.success("✅ Dashboard loaded successfully!")
    main()
except Exception as e:
    # Show the actual error so we can fix it
    st.error(f"❌ Error loading dashboard: {e}")
    st.info("📱 Falling back to simple dashboard...")
    
    try:
        from hackathon.app.pages_disabled.dashboard import main
        st.success("✅ Fallback dashboard loaded!")
        main()
    except Exception as e2:
        st.error(f"❌ Fallback dashboard also failed: {e2}")
        st.markdown("---")
        st.markdown("### 🔧 Debug Information")
        st.code(f"Error: {e2}", language="python")
        st.markdown("🔗 Backend API: https://nfcc-platform-production.up.railway.app")
