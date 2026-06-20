"""
CivicFlood AI - Streamlit Cloud Entry Point
This file is used by Streamlit Cloud to launch the dashboard.
"""

import streamlit as st
import sys
from pathlib import Path
import os

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure API URL from environment
os.environ["NFCC_API_URL"] = os.getenv(
    "NFCC_API_URL", 
    "https://nfcc-platform-production.up.railway.app"
)

# Import and run the main dashboard
try:
    from hackathon.app.pages.dashboard_enhanced import main
except ImportError:
    # Fallback to original dashboard
    from hackathon.app.pages.dashboard import main

if __name__ == "__main__":
    main()
