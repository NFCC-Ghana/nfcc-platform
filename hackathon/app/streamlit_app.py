"""
CivicFlood AI - Streamlit Cloud Entry Point
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
# ATTEMPT TO LOAD DASHBOARD
# ============================================================
st.title("🌊 CivicFlood AI")
st.markdown("### National Flood Intelligence Platform")
st.markdown("**Ghana AI Innovation Challenge 2026**")
st.caption(f"🐍 Python: {sys.version[:20]}")
st.caption(f"🔗 API: {os.environ['NFCC_API_URL']}")

st.divider()

try:
    # Try enhanced dashboard first
    from hackathon.app.pages_disabled.dashboard_enhanced import main
    st.success("✅ Enhanced dashboard loaded!")
    main()
except ImportError as e:
    # If enhanced fails, try simple dashboard
    st.error(f"⚠️ Enhanced dashboard unavailable: {e}")
    st.info("📱 Loading simple dashboard...")
    
    try:
        from hackathon.app.pages_disabled.dashboard import main
        st.success("✅ Simple dashboard loaded!")
        main()
    except Exception as e2:
        st.error(f"❌ Both dashboards failed: {e2}")
        st.markdown("---")
        st.markdown("### 🔧 Debug Information")
        st.code(str(e2), language="python")
