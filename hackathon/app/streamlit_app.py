"""
CivicFlood AI - Streamlit Cloud Entry Point (Simplified)
"""

import streamlit as st
import sys
from pathlib import Path
import os

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure API URL
os.environ["NFCC_API_URL"] = os.getenv(
    "NFCC_API_URL", 
    "https://nfcc-platform-production.up.railway.app"
)

# Set page config FIRST - before any other Streamlit commands
st.set_page_config(
    page_title="CivicFlood AI - National Flood Intelligence",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import and run the main dashboard
try:
    from hackathon.app.pages.dashboard_enhanced import main
    main()
except ImportError:
    # Fallback to original dashboard
    try:
        from hackathon.app.pages.dashboard import main
        main()
    except ImportError:
        # Ultimate fallback - display a simple page
        st.title("🌊 CivicFlood AI")
        st.markdown("### National Flood Intelligence Platform")
        st.markdown("**Ghana AI Innovation Challenge 2026**")
        st.info("📱 Dashboard loading... Please check your deployment configuration.")
        st.markdown("---")
        st.markdown("🔗 Backend API: https://nfcc-platform-production.up.railway.app")
