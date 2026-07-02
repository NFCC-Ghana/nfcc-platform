"""
AI Decision Support - Actionable recommendations with expected benefits.
"""

import streamlit as st

def render_decision_support(district: str, risk_score: float) -> None:
    """Render AI Decision Support panel."""
    
    st.markdown("### 🎯 AI Decision Support")
    st.caption("Prioritized actions with expected impact")
    
    if risk_score >= 80:
        actions = [
            {
                "priority": "🔴 Priority 1",
                "action": "Issue Evacuation Order",
                "benefit": "8,000 residents protected",
                "timeframe": "Immediate"
            },
            {
                "priority": "🟠 Priority 2",
                "action": "Deploy Pumps to Alajo",
                "benefit": "18cm water reduction",
                "timeframe": "Next 2 hours"
            },
            {
                "priority": "🟡 Priority 3",
                "action": "Close Ring Road",
                "benefit": "42% traffic reduction",
                "timeframe": "Next 4 hours"
            },
            {
                "priority": "🟢 Priority 4",
                "action": "Open Shelters",
                "benefit": "2,000 shelter capacity",
                "timeframe": "Next 6 hours"
            }
        ]
    elif risk_score >= 60:
        actions = [
            {
                "priority": "🟠 Priority 1",
                "action": "Prepare Evacuation",
                "benefit": "15,000 residents ready",
                "timeframe": "Next 4 hours"
            },
            {
                "priority": "🟡 Priority 2",
                "action": "Monitor Rivers",
                "benefit": "24/7 river monitoring",
                "timeframe": "Ongoing"
            }
        ]
    else:
        actions = [
            {
                "priority": "🟢 Priority 1",
                "action": "Continue Monitoring",
                "benefit": "Normal operations",
                "timeframe": "Ongoing"
            }
        ]
    
    for action in actions:
        st.markdown(f"""
        <div style="background: {'#ffebee' if 'Priority 1' in action['priority'] else '#fff3e0' if 'Priority 2' in action['priority'] else '#e8f5e9'}; padding: 0.8rem 1rem; border-radius: 8px; margin-bottom: 0.5rem; border-left: 4px solid {'#ff0000' if 'Priority 1' in action['priority'] else '#ff9800' if 'Priority 2' in action['priority'] else '#4caf50'};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <b>{action['priority']}: {action['action']}</b><br>
                    <span style="font-size: 0.85rem; color: #555;">✓ {action['benefit']}</span>
                </div>
                <div style="font-size: 0.8rem; color: #888;">
                    ⏱️ {action['timeframe']}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
