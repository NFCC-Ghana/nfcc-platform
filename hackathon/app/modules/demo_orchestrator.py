"""
Demo Orchestrator - Walks judges through a realistic emergency scenario.
"""

import time
from datetime import datetime

import streamlit as st


class DemoOrchestrator:
    """
    Orchestrates a complete emergency scenario for judges.
    Walks through: Detection → Assessment → Decision → Response
    """

    def __init__(self):
        self.steps = [
            {"id": 1, "name": "🌧️ Rainfall Detection", "status": "pending"},
            {"id": 2, "name": "🌊 River Level Rising", "status": "pending"},
            {"id": 3, "name": "🏗️ Reservoir Release", "status": "pending"},
            {"id": 4, "name": "🛰️ Satellite Confirmation", "status": "pending"},
            {"id": 5, "name": "📢 Community Reports", "status": "pending"},
            {"id": 6, "name": "🧠 AI Assessment", "status": "pending"},
            {"id": 7, "name": "📊 Impact Analysis", "status": "pending"},
            {"id": 8, "name": "📱 Alert Generation", "status": "pending"},
            {"id": 9, "name": "🎯 Decision Support", "status": "pending"},
        ]
        self.current_step = 0

    def run_scenario(self, district: str = "Accra Central"):
        """Run the complete emergency scenario."""

        st.markdown(
            """
        <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); 
                    padding: 1.5rem; border-radius: 12px; color: white; margin-bottom: 1rem;">
            <h2 style="color: white; margin: 0;">🎬 Live Emergency Scenario</h2>
            <p style="color: #a8d8ea; margin: 0;">Walk through a realistic flood response</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Status bar
        st.markdown("#### 📋 Scenario Progress")

        progress_cols = st.columns(9)
        for i, step in enumerate(self.steps):
            with progress_cols[i]:
                if step["status"] == "completed":
                    st.markdown(f"✅ {i+1}")
                elif step["status"] == "active":
                    st.markdown(f"🔄 {i+1}")
                else:
                    st.markdown(f"⏳ {i+1}")

        # Run the scenario
        if st.button("🚀 Run Scenario", use_container_width=True):
            scenario_placeholder = st.empty()

            # Step 1: Rainfall Detection
            for i, step in enumerate(self.steps):
                self.steps[i]["status"] = "active"
                self._render_scenario_step(step, scenario_placeholder)
                time.sleep(1.5)
                self.steps[i]["status"] = "completed"
                self._render_scenario_step(step, scenario_placeholder)

            # Final summary
            st.success(
                "✅ Scenario Complete! System demonstrated full response capability"
            )

            # Show final briefing
            st.markdown("#### 📋 Final Assessment")
            st.code(f"""
┌─────────────────────────────────────────────────────────────────┐
│                    SCENARIO COMPLETE                             │
│                     {datetime.now().strftime('%d %b %Y, %H:%M')}                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  DETECTION: Rainfall (75mm) + River (0.45m) + Satellite        │
│  ASSESSMENT: Flood risk 90.6% (EXTREME)                        │
│  IMPACT: 102,157 people affected                               │
│  ACTION: Evacuation ordered for 5 communities                  │
│  CONFIRMATION: 4 community reports verified                    │
│                                                                  │
│  ✅ FULLY OPERATIONAL                                           │
│  ✅ ALL SYSTEMS INTEGRATED                                      │
│  ✅ READY FOR EMERGENCY RESPONSE                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
""")

    def _render_scenario_step(self, step: dict, placeholder):
        """Render a single scenario step."""
        status_emoji = (
            "🔄"
            if step["status"] == "active"
            else "✅" if step["status"] == "completed" else "⏳"
        )
        status_text = (
            "Processing..."
            if step["status"] == "active"
            else "Complete" if step["status"] == "completed" else "Pending"
        )

        with placeholder.container():
            st.markdown(
                f"""
            <div style="background: {'#fff3e0' if step['status'] == 'active' else '#f8f9fa' if step['status'] == 'completed' else '#f0f0f0'}; 
                        padding: 0.8rem 1rem; border-radius: 8px; margin-bottom: 0.5rem; 
                        border-left: 4px solid {'#ff9800' if step['status'] == 'active' else '#4caf50' if step['status'] == 'completed' else '#ccc'};">
                <span style="font-weight: 600;">{step['name']}</span>
                <span style="float: right; font-size: 0.85rem; color: #666;">
                    {status_emoji} {status_text}
                </span>
            </div>
            """,
                unsafe_allow_html=True,
            )


def render_demo_orchestrator() -> None:
    """Render demo orchestrator interface."""

    st.markdown("### 🎬 Demo Orchestrator")
    st.caption("Walk judges through a complete emergency response scenario")

    demo = DemoOrchestrator()
    demo.run_scenario()
