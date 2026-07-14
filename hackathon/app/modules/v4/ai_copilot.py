"""
AI Flood Copilot Module - Full Implementation
Interactive Q&A with AI-powered responses.
"""

import random
from datetime import datetime

import streamlit as st


def render_ai_copilot(state):
    """Render the complete AI flood copilot."""

    st.markdown("## 🤖 AI Flood Copilot")
    st.caption("Ask questions or use suggested prompts for instant insights")

    # Suggested questions
    suggestions = [
        "💡 Will Odaw River overflow today?",
        "💡 Should Accra evacuate?",
        "💡 Which roads close first?",
        "💡 When will the rain stop?",
        "💡 What areas are most at risk?",
        "💡 How many shelters are available?",
    ]

    st.markdown("### 💡 Suggested Questions")
    cols = st.columns(3)
    for i, suggestion in enumerate(suggestions):
        with cols[i % 3]:
            if st.button(suggestion, key=f"suggestion_{i}", use_container_width=True):
                st.session_state["copilot_query"] = suggestion

    # Chat interface
    st.markdown("### 💬 Ask CivicFlood AI")

    # Initialize chat history
    if "copilot_messages" not in st.session_state:
        st.session_state["copilot_messages"] = [
            {
                "role": "assistant",
                "content": "Hello! I'm CivicFlood AI. I can help you understand flood risks, evacuation routes, and emergency response. What would you like to know?",
            }
        ]

    # Display chat history
    for message in st.session_state["copilot_messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Handle query
    query = st.chat_input(
        "Ask CivicFlood AI about flood risks, evacuation, or safety..."
    )

    if query:
        # Add user message
        st.session_state["copilot_messages"].append({"role": "user", "content": query})

        # Generate response
        response = generate_copilot_response(query, state)

        # Add assistant response
        st.session_state["copilot_messages"].append(
            {"role": "assistant", "content": response}
        )

        # Rerun to update chat
        st.rerun()


def generate_copilot_response(query: str, state) -> str:
    """Generate AI response based on query and state."""

    query_lower = query.lower()

    # River related questions
    if any(word in query_lower for word in ["river", "odaw", "overflow", "level"]):
        return f"""
        **🌊 Odaw River Status**
        
        Current level: **{state.river_level_m:.2f}m**
        Status: **{state.river_status}**
        
        - Warning level: 2.0m
        - Danger level: 2.8m
        - Flood stage: 3.2m
        
        The river is currently {state.river_status.lower()}. 
        Based on current rainfall of {state.rainfall_mm}mm, 
        the river is expected to { "rise" if state.risk_score > 50 else "remain stable" }.
        """

    # Evacuation questions
    elif any(
        word in query_lower for word in ["evacuate", "evacuation", "shelter", "safe"]
    ):
        return f"""
        **🚨 Evacuation Information**
        
        Current Risk Level: **{state.risk_category}**
        Lead Time: **{state.lead_time_hours} hours**
        
        **Nearest Shelters:**
        1. Accra High School (1.2 km) - {850} spaces available
        2. Community Center (2.5 km) - {320} spaces available
        3. Trade Fair Centre (4.0 km) - {2000} spaces available
        
        **Evacuation Routes:**
        - Alajo → Accra High School (15 min)
        - Kaneshie → Community Center (20 min)
        - Circle → Trade Fair Centre (25 min)
        """

    # Impact questions
    elif any(
        word in query_lower for word in ["impact", "affected", "people", "population"]
    ):
        return f"""
        **👥 Impact Assessment for {state.district}**
        
        **Population at Risk:** {state.population_exposed:,} people
        - Children under 18: {state.children_exposed:,}
        - Elderly over 60: {state.elderly_exposed:,}
        - Disabled: {state.disabled_exposed:,}
        
        **Infrastructure at Risk:**
        - {state.schools_exposed} schools
        - {state.hospitals_exposed} hospitals
        - {state.markets_exposed} markets
        
        **Estimated Economic Impact:** GH₵ {state.total_loss_ghs:,.0f}
        Estimated Recovery Time: {state.recovery_weeks:.0f} weeks
        """

    # Forecast questions
    elif any(
        word in query_lower for word in ["forecast", "rain", "weather", "tomorrow"]
    ):
        return f"""
        **🌤️ Weather Forecast**
        
        Current rainfall: **{state.rainfall_mm}mm**
        
        **Forecast:**
        - 6 hours: {min(100, state.risk_score + 10):.0f}% risk
        - 12 hours: {min(100, state.risk_score + 15):.0f}% risk
        - 24 hours: {min(100, state.risk_score + 5):.0f}% risk
        
        **Risk Trend:** {"Increasing" if state.risk_score > 50 else "Stable"}
        Peak risk expected in {6} hours.
        """

    # General questions
    else:
        return f"""
        **🤖 CivicFlood AI Assistant**
        
        I can help you with:
        - 🌊 **River conditions** (levels, overflow risk)
        - 🚨 **Evacuation** (routes, shelters, timing)
        - 👥 **Impact** (people affected, infrastructure risk)
        - 🌤️ **Forecast** (rainfall, risk trends)
        
        Current Status: **{state.risk_category}** ({state.risk_score:.1f}% risk)
        
        What would you like to know more about?
        """
