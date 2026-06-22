"""
CivicFlood AI - Enhanced Dashboard v3
Adds new modules WITHOUT breaking existing dashboard
"""

import streamlit as st
from hackathon.app.pages_disabled.dashboard_enhanced import main as original_main
from hackathon.app.modules.timeline import render_timeline
from hackathon.app.modules.copilot import render_copilot
from hackathon.app.modules.evacuation import render_evacuation_info
from hackathon.app.modules.ranking import render_district_ranking

def main():
    # Call the original dashboard first (UNCHANGED)
    original_main()
    
    # Add new features AFTER the original dashboard
    st.divider()
    render_timeline(90.6)
    
    st.divider()
    render_copilot("Accra Central", 90.6)
    
    st.divider()
    render_evacuation_info("Accra Central")
    
    st.divider()
    render_district_ranking()

if __name__ == "__main__":
    main()
