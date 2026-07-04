"""AI Decision Support module."""

import streamlit as st


def render_decision_support(state):
    """Render the AI decision support section."""
    st.markdown("## 🎯 AI Decision Support")
    st.caption("Prioritized actions with expected impact")
    
    actions = [
        {"priority": "🔴", "title": "Priority 1: Issue Evacuation Order",
         "impact": "✓ 8,000 residents protected", "time": "⏱️ Immediate"},
        {"priority": "🟠", "title": "Priority 2: Deploy Pumps to Alajo",
         "impact": "✓ 18cm water reduction", "time": "⏱️ Next 2 hours"},
        {"priority": "🟡", "title": "Priority 3: Close Ring Road",
         "impact": "✓ 42% traffic reduction", "time": "⏱️ Next 4 hours"},
        {"priority": "🟢", "title": "Priority 4: Open Shelters",
         "impact": "✓ 2,000 shelter capacity", "time": "⏱️ Next 6 hours"},
    ]
    
    for action in actions:
        st.markdown(f"**{action['priority']} {action['title']}**")
        st.caption(f"{action['impact']} • {action['time']}")
        st.divider()
