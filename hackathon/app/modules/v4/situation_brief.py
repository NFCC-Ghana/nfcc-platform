"""AI Situation Brief module."""

import streamlit as st


def render_situation_brief(state):
    """Render the AI situation brief."""
    st.markdown("## 🤖 AI Situation Brief")
    
    if state.risk_score >= 80:
        brief = f"""
        🔴 **EMERGENCY LEVEL: HIGH**
        
        Persistent rainfall has saturated catchments in {state.district}, 
        increasing flash flood risk. Verified flooding is already occurring 
        in Alajo while Volta Basin conditions continue deteriorating. 
        Immediate priority is evacuation readiness and deployment of 
        drainage response teams.
        """
    elif state.risk_score >= 60:
        brief = f"""
        🟠 **ALERT LEVEL: ELEVATED**
        
        Rainfall continues to impact {state.district} with rising water levels. 
        Soil saturation is increasing rapidly. Monitor low-lying areas and 
        prepare for potential evacuation orders.
        """
    else:
        brief = f"""
        🟢 **MONITORING LEVEL: NORMAL**
        
        Conditions in {state.district} remain stable. Continue monitoring 
        rainfall and river levels. No immediate action required.
        """
    
    st.info(brief)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Analysis", "✅ Complete")
    with col2:
        st.metric("Data Sources", f"{state.active_sources_count}")
    with col3:
        st.metric("Confidence", f"{state.confidence*100:.0f}%")
