"""
CivicFlood AI - Enhanced Dashboard v3
Full NFCC intelligence with enhanced AI Copilot
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import original dashboard
from hackathon.app.pages_disabled.dashboard_enhanced import main as original_main

# Import enhanced modules
from hackathon.app.modules.timeline import render_timeline
from hackathon.app.modules.copilot import render_copilot, render_situation_report
from hackathon.app.modules.evacuation import render_evacuation_info
from hackathon.app.modules.ranking import render_district_ranking

def main():
    # Call original dashboard first
    original_main()
    
    # Add enhanced features
    st.divider()
    st.markdown("## 🆕 Enhanced Features")
    
    # Get current risk score from session state or use default
    # In production, this would come from the API
    current_risk = st.session_state.get("current_risk", 90.6)
    current_district = st.session_state.get("current_district", "Accra Central")
    
    # Timeline
    render_timeline(current_risk)
    
    st.divider()
    
    # Enhanced AI Copilot
    render_copilot(current_district, current_risk)
    
    st.divider()
    
    # Situation Report
    render_situation_report(current_district, current_risk)
    
    st.divider()
    
    # Evacuation Intelligence
    render_evacuation_info(current_district)
    
    st.divider()
    
    # National Ranking
    render_district_ranking()

if __name__ == "__main__":
    main()
