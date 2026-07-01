"""
CivicFlood AI - Streamlit Cloud Entry Point
Redirects to v4 National Emergency Operations Center
"""

import streamlit as st
import sys
from pathlib import Path
import os

st.set_page_config(
    page_title="CivicFlood AI - National EOC",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

os.environ["NFCC_API_URL"] = os.getenv(
    "NFCC_API_URL",
    "https://nfcc-platform-production.up.railway.app"
)

try:
    from hackathon.app.pages_disabled.dashboard_v4 import main
    main()
except Exception as e:
    st.error(f"❌ Error loading v4 dashboard: {e}")
    st.info("Falling back to enhanced dashboard...")
    try:
        from hackathon.app.pages_disabled.dashboard_enhanced import main
        main()
    except Exception as e2:
        st.error(f"❌ Both dashboards failed: {e2}")
