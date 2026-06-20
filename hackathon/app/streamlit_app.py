"""
CivicFlood AI - Streamlit Cloud Entry Point
Using minimal test app for debugging
"""

import streamlit as st
import sys
from pathlib import Path

# ============================================================
# PAGE CONFIG - RIGHT HERE AT THE TOP
# ============================================================
st.set_page_config(
    page_title="CivicFlood AI - Test",
    page_icon="🌊",
    layout="wide"
)

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Run the minimal test app
try:
    from hackathon.app.minimal_app import main
    main()
except ImportError:
    # If minimal_app doesn't have main, just display directly
    st.title("🌊 CivicFlood AI - Test App")
    st.markdown("### If you can see this, Streamlit Cloud is working!")
    st.success("✅ Deployment successful!")
    st.info("📱 Now we can add the full dashboard.")
    st.markdown("---")
    st.markdown("🔗 Backend API: https://nfcc-platform-production.up.railway.app")

