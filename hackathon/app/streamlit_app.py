"""
CivicFlood AI - Streamlit Cloud Entry Point
Uses Enhanced Dashboard v3 with all new features
"""

import streamlit as st
import sys
from pathlib import Path
import os

st.set_page_config(
    page_title="CivicFlood AI - National Flood Intelligence",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

os.environ["NFCC_API_URL"] = os.getenv(
    "NFCC_API_URL",
    "https://nfcc-platform-production.up.railway.app"
)

st.title("🌊 CivicFlood AI")
st.markdown("### National Flood Intelligence Platform")
st.markdown("**Ghana AI Innovation Challenge 2026**")
st.caption(f"🐍 Python: {sys.version[:20]}")
st.caption(f"🔗 API: {os.environ['NFCC_API_URL']}")

st.divider()
st.markdown("🔄 **Loading Enhanced Dashboard v3...**")

try:
    from hackathon.app.pages_disabled.dashboard_enhanced_v3 import main
    st.success("✅ Enhanced dashboard (v3) loaded successfully!")
    main()
except Exception as e:
    st.error(f"❌ Error: {e}")
    st.info("Falling back to original dashboard...")
    try:
        from hackathon.app.pages_disabled.dashboard_enhanced import main
        st.success("✅ Original dashboard loaded!")
        main()
    except Exception as e2:
        st.error(f"❌ Both dashboards failed: {e2}")
