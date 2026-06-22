"""AI Flood Copilot - Chat-based flood intelligence."""

import streamlit as st

def render_copilot(district: str, risk_score: float) -> None:
    """Render AI Flood Copilot."""
    
    st.markdown("### 🤖 AI Flood Copilot")
    st.caption("Ask any question about flood risk in your community")
    
    questions = [
        f"Why is {district} at {risk_score:.0f}% risk?",
        "What should I do to prepare?",
        "When will the flood peak?",
        "Are schools in my area at risk?"
    ]
    
    cols = st.columns(4)
    for i, q in enumerate(questions):
        with cols[i]:
            if st.button(q, key=f"q_{i}"):
                st.session_state.copilot_query = q
    
    query = st.text_input("Ask CivicFlood AI:", placeholder="e.g., Will Odaw River overflow today?")
    
    if query or st.session_state.get("copilot_query"):
        question = query or st.session_state.get("copilot_query", "")
        
        with st.spinner("🤔 Analyzing your question..."):
            response = generate_response(question, district, risk_score)
            st.success(response)
    
    st.caption("💡 Try asking: 'What should schools do?' or 'Which roads will flood?'")

def generate_response(question: str, district: str, risk_score: float) -> str:
    """Generate AI response (simulated)."""
    
    if "why" in question.lower() and "risk" in question.lower():
        return f"""
        📊 **Why is {district} at {risk_score:.0f}% risk?**
        
        1. **Rainfall Intensity**: 35% contribution (30-day accumulation)
        2. **Soil Saturation**: 25% contribution (NASA SMAP data)
        3. **River Level**: 15% contribution (Odaw at 0.45m)
        4. **Historical Flooding**: 10% contribution (similar to 2023 event)
        5. **Urban Drainage**: 5% contribution (poor drainage capacity)
        6. **Forecast Rain**: 10% contribution (Open-Meteo 72h forecast)
        
        **Recommendation**: Prepare for evacuation within 6 hours.
        """
    
    if "prepare" in question.lower() or "do" in question.lower():
        return f"""
        🚨 **Recommended Actions for {district}:**
        
        1. **Immediate**: Move valuables to upper floors
        2. **Within 1 Hour**: Prepare emergency kit (water, food, meds)
        3. **Within 3 Hours**: Evacuate to designated shelters
        4. **Monitor**: Check alerts every 30 minutes
        
        **Nearby Shelters:**
        • Accra High School - 1.2km
        • Community Center - 2.5km
        • Trade Fair Centre - 4.0km
        """
    
    if "school" in question.lower():
        return f"""
        🏫 **Schools in {district}:**
        
        **At Risk:**
        • Alajo Basic School - 0.8km from flood zone
        • Kaneshie Senior High - 1.2km from flood zone
        
        **Recommendations:**
        1. Notify parents immediately
        2. Prepare for early dismissal
        3. Move students to upper floors
        4. Contact NADMO for evacuation support
        """
    
    return f"""
    📋 **CivicFlood AI Response:**
    
    Based on current data for {district} ({risk_score:.0f}% risk):
    
    1. Monitor official alerts every 30 minutes
    2. Prepare emergency supplies
    3. Know your evacuation route
    4. Check on vulnerable neighbors
    
    Stay safe! 🌊
    """
