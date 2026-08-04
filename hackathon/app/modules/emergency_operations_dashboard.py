"""
Emergency Operations Dashboard - NASA Mission Control style.
"""

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st


def render_emergency_operations_dashboard(district: str, risk_score: float) -> None:
    """Render Emergency Operations Center dashboard."""

    st.markdown(
        """
    <div style="background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #16213e 100%); 
                padding: 1.5rem; border-radius: 12px; margin-bottom: 1rem; border: 1px solid #2a2a4e;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1 style="color: #00ff88; margin: 0; font-size: 1.8rem;">🚨 EMERGENCY OPERATIONS CENTER</h1>
                <p style="color: #8ecae6; margin: 0; font-size: 0.9rem;">
                    {district} • {datetime.now().strftime('%d %b %Y, %H:%M UTC')}
                </p>
            </div>
            <div style="display: flex; gap: 1rem;">
                <span style="background: #00ff88; color: #0a0a0f; padding: 0.3rem 1rem; border-radius: 20px; font-weight: 700;">
                    🟢 SYSTEM ACTIVE
                </span>
                <span style="border: 1px solid #2a2a4e; padding: 0.3rem 1rem; border-radius: 20px; color: #8ecae6;">
                    v3.0.0
                </span>
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Top row: Situation Overview
    col1, col2, col3, col4 = st.columns(4)

    risk_color = (
        "🔴"
        if risk_score >= 80
        else "🟠" if risk_score >= 60 else "🟡" if risk_score >= 40 else "🟢"
    )
    risk_category = (
        "EXTREME"
        if risk_score >= 80
        else "HIGH" if risk_score >= 60 else "MODERATE" if risk_score >= 40 else "LOW"
    )

    with col1:
        st.markdown(
            f"""
        <div style="background: white; padding: 1rem; border-radius: 8px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
            <div style="font-size: 0.8rem; color: #666;">CURRENT RISK</div>
            <div style="font-size: 1.8rem; font-weight: 700;">{risk_color} {risk_score:.0f}%</div>
            <div style="font-size: 0.8rem; color: #888;">{risk_category}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
        <div style="background: white; padding: 1rem; border-radius: 8px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
            <div style="font-size: 0.8rem; color: #666;">CONFIDENCE</div>
            <div style="font-size: 1.8rem; font-weight: 700;">92%</div>
            <div style="font-size: 0.8rem; color: #888;">High Evidence Quality</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
        <div style="background: white; padding: 1rem; border-radius: 8px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
            <div style="font-size: 0.8rem; color: #666;">POPULATION AT RISK</div>
            <div style="font-size: 1.8rem; font-weight: 700;">102,157</div>
            <div style="font-size: 0.8rem; color: #888;">5 Communities Affected</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            f"""
        <div style="background: white; padding: 1rem; border-radius: 8px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
            <div style="font-size: 0.8rem; color: #666;">RESPONSE STATUS</div>
            <div style="font-size: 1.8rem; font-weight: 700;">🚨</div>
            <div style="font-size: 0.8rem; color: #888;">Immediate Action Required</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.divider()

    # Middle: Situation Timeline
    st.markdown("#### 📊 Situation Timeline")

    timeline_data = pd.DataFrame(
        {
            "Time": ["-12h", "-6h", "-3h", "-1h", "Now", "+3h", "+6h", "+12h", "+24h"],
            "Risk": [45, 62, 74, 85, 90.6, 95, 92, 82, 68],
        }
    )

    fig = px.line(
        timeline_data,
        x="Time",
        y="Risk",
        title="Risk Evolution (Last 12h → Next 24h)",
        markers=True,
    )
    fig.update_traces(line_color="#ff4444", line_width=3)
    fig.update_layout(height=200, yaxis_title="Risk Score (%)", yaxis_range=[0, 100])
    st.plotly_chart(fig, use_container_width=True)

    # Bottom: Action Grid
    st.divider()
    st.markdown("#### 🎯 Recommended Actions")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
        <div style="background: #ffebee; padding: 1rem; border-radius: 8px; border-left: 4px solid #ff0000;">
            <b>🚨 Immediate</b><br>
            • Evacuate Alajo<br>
            • Evacuate Kaneshie<br>
            • Evacuate Circle
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
        <div style="background: #fff3e0; padding: 1rem; border-radius: 8px; border-left: 4px solid #ff9800;">
            <b>⚠️ Prepare</b><br>
            • Open shelters<br>
            • Deploy rescue teams<br>
            • Close affected roads
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """
        <div style="background: #e8f5e9; padding: 1rem; border-radius: 8px; border-left: 4px solid #4caf50;">
            <b>ℹ️ Monitor</b><br>
            • Track rainfall<br>
            • Monitor river levels<br>
            • Update community
        </div>
        """,
            unsafe_allow_html=True,
        )
