"""
Enhanced AI Copilot - With suggested prompts.
"""

import streamlit as st

def render_ai_copilot() -> None:
    """Render enhanced AI Copilot with suggested prompts."""
    
    st.markdown("### 🤖 AI Flood Copilot")
    st.caption("Ask questions or use suggested prompts")
    
    # Example buttons
    st.markdown("#### 💡 Suggested Questions")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏠 Should Accra evacuate?", use_container_width=True):
            st.session_state.copilot_query = "Should Accra evacuate?"
        if st.button("🛣️ Which roads close first?", use_container_width=True):
            st.session_state.copilot_query = "Which roads close first?"
        if st.button("📊 Why is confidence 92%?", use_container_width=True):
            st.session_state.copilot_query = "Why is confidence 92%?"
    
    with col2:
        if st.button("📅 Compare to 2022 flood", use_container_width=True):
            st.session_state.copilot_query = "Compare today's flood to 2022"
        if st.button("📄 Generate SITREP", use_container_width=True):
            st.session_state.copilot_query = "Generate SITREP"
        if st.button("🆘 What should schools do?", use_container_width=True):
            st.session_state.copilot_query = "What should schools do?"
    
    # Chat input
    query = st.text_input(
        "Ask CivicFlood AI:",
        placeholder="e.g., Will Odaw River overflow today?",
        key="copilot_input"
    )
    
    if query or st.session_state.get("copilot_query"):
        question = query or st.session_state.get("copilot_query", "")
        
        with st.spinner("🧠 Analyzing..."):
            # Simple response simulation
            responses = {
                "Should Accra evacuate?": "⚠️ **Partial evacuation recommended.**\n\nAlajo and Kaneshie have been confirmed flooded. Residents in these areas should move to higher ground immediately. Other areas should prepare for possible evacuation within 6 hours.",
                "Which roads close first?": "🛣️ **Priority road closures:**\n\n1. Alajo Main Street (flooding confirmed)\n2. Ring Road near Circle (water rising)\n3. Kaneshie Market Road (blocked drainage)\n\n**Alternate routes:** Independence Avenue, Liberation Road.",
                "Why is confidence 92%?": "📊 **Confidence breakdown:**\n\n- CHIRPS rainfall: HIGH (95%)\n- SMAP soil moisture: HIGH (90%)\n- Community reports: MEDIUM (85%)\n- River gauges: HIGH (88%)\n\n**Overall confidence:** 92% based on 5 data sources.",
                "Compare today's flood to 2022": "📅 **Comparison to 2022 flood:**\n\n**Similarities:**\n- Both events had 75mm+ rainfall\n- Odaw River reached similar levels\n\n**Differences:**\n- 2026 has better drainage (40% improvement)\n- 2026 soil saturation is higher (85% vs 65%)\n\n**Verdict:** 2026 flood is expected to be less severe than 2022.",
                "Generate SITREP": "📋 **SITUATION REPORT**\n\n**District:** Accra Central\n**Risk:** EXTREME (90.6%)\n**Population at Risk:** 102,157\n**Schools:** 23 at risk\n**Hospitals:** 3 at risk\n\n**Recommended Actions:**\n1. Evacuate Alajo and Kaneshie\n2. Deploy pumps to low-lying areas\n3. Issue public warnings\n4. Open shelters",
                "What should schools do?": "🏫 **School Recommendations:**\n\n1. **Immediate:** Suspend in-person instruction\n2. **Notify parents** via WhatsApp/SMS\n3. **Prepare remote learning** materials\n4. **Open facilities** as shelters if needed\n5. **Coordinate** with NADMO\n\n**Affected Schools:** 23 schools, ~30,000 students"
            }
            
            response = responses.get(question, "I'm processing your question about flood risk. Based on current data, here's what I can tell you...")
            st.markdown(f"### 📋 Response\n{response}")
    
    st.caption("💡 Try: 'Should Accra evacuate?' or 'Which roads close first?'")
