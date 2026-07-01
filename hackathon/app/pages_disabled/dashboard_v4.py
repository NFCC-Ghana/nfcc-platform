"""
CivicFlood AI v4 - National Emergency Operations Center
Single screen, Mission Control layout
NO set_page_config() - handled by streamlit_app.py
"""

import streamlit as st
import sys
from pathlib import Path
import os
import requests

# ============================================================
# PATH SETUP
# ============================================================
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# ============================================================
# IMPORT v4 MODULES
# ============================================================
from hackathon.app.modules.v4.mission_control_header import render_mission_control_header
from hackathon.app.modules.v4.national_briefing import render_national_briefing
from hackathon.app.modules.v4.situation_map import render_situation_map
from hackathon.app.modules.v4.evidence_panel import render_evidence_panel
from hackathon.app.modules.v4.impact_panel import render_impact_panel
from hackathon.app.modules.v4.operations_panel import render_operations_panel
from hackathon.app.modules.v4.community_intelligence import render_community_intelligence
from hackathon.app.modules.v4.ai_copilot_v4 import render_ai_copilot_v4

# ============================================================
# API HELPER
# ============================================================
API_URL = os.getenv("NFCC_API_URL", "https://nfcc-platform-production.up.railway.app")

def call_api(endpoint, method="GET", data=None):
    url = f"{API_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        else:
            response = requests.post(url, json=data, timeout=10)
        return response.json() if response.status_code == 200 else {}
    except:
        return {}

# ============================================================
# DISTRICTS
# ============================================================
DISTRICTS = {
    "Accra Central": {"region": "Greater Accra", "population": 187928},
    "Accra West": {"region": "Greater Accra", "population": 203461},
    "Accra East": {"region": "Greater Accra", "population": 142587},
    "Tema": {"region": "Greater Accra", "population": 198742},
    "Kumasi": {"region": "Ashanti", "population": 443981},
    "Tamale": {"region": "Northern", "population": 371578}
}

# ============================================================
# SIDEBAR (Minimal - Just controls)
# ============================================================
def render_sidebar():
    with st.sidebar:
        st.markdown("### 🎛️ Controls")
        district = st.selectbox("📍 Select District", list(DISTRICTS.keys()), index=0)
        rainfall_mm = st.slider("🌧️ Rainfall (mm)", 0, 200, 75)
        
        st.divider()
        st.markdown("### 📊 Data Status")
        
        health = call_api("/health")
        if health.get("status") == "healthy":
            st.success("✅ API Connected")
        else:
            st.warning("⚠️ API Unavailable")
        
        st.caption(f"🌐 {API_URL}")
        st.divider()
        st.caption("v3.0.0 • Ghana AI Challenge 2026")
        
        return district, rainfall_mm

# ============================================================
# MAIN FUNCTION
# ============================================================
def main():
    """Main dashboard function - called by streamlit_app.py"""
    
    # Render sidebar and get inputs
    district, rainfall_mm = render_sidebar()
    
    # Get risk score
    with st.spinner("🔄 Analyzing..."):
        score_data = call_api("/score", "POST", {
            "location": district,
            "precipitation": rainfall_mm
        })
    score = score_data.get("score", 50)
    
    # 1. HEADER
    render_mission_control_header()
    
    # 2. AI NATIONAL BRIEFING (Hero section)
    render_national_briefing(district, score)
    
    st.divider()
    
    # 3. MAP + RECOMMENDATIONS (Two columns)
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        render_situation_map(district, score)
    
    with col_right:
        # Show recommendations based on risk
        st.markdown("### 🚨 Recommended Actions")
        
        if score >= 80:
            st.error("🚨 **IMMEDIATE EVACUATION**")
            st.markdown("• Seek higher ground")
            st.markdown("• Notify neighbors")
            st.markdown("• Call emergency services")
        elif score >= 60:
            st.warning("⚠️ **PREPARE TO EVACUATE**")
            st.markdown("• Move to higher ground")
            st.markdown("• Prepare emergency kit")
            st.markdown("• Monitor alerts")
        elif score >= 40:
            st.info("ℹ️ **MONITOR CONDITIONS**")
            st.markdown("• Stay informed")
            st.markdown("• Check community reports")
        else:
            st.success("✅ **NORMAL**")
            st.markdown("• Continue monitoring")
    
    st.divider()
    
    # 4. EVIDENCE + IMPACT (Two columns)
    col1, col2 = st.columns(2)
    
    with col1:
        render_evidence_panel(score)
    
    with col2:
        render_impact_panel(district, score)
    
    st.divider()
    
    # 5. OPERATIONS + COMMUNITY (Two columns)
    col1, col2 = st.columns(2)
    
    with col1:
        render_operations_panel(district)
    
    with col2:
        render_community_intelligence()
    
    st.divider()
    
    # 6. AI COPILOT (Full width, prominent)
    render_ai_copilot_v4(district, score)
    
    # ============================================================
    # FOOTER
    # ============================================================
    st.divider()
    st.caption("🌊 CivicFlood AI • Powered by NFCC Platform • Ghana AI Innovation Challenge 2026")
    st.caption(f"🔗 API: {API_URL}")

if __name__ == "__main__":
    main()
