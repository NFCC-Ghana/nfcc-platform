"""Mission Control Header - Professional EOC header."""

import streamlit as st
from datetime import datetime

def render_mission_control_header() -> None:
    """Render professional mission control header."""
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #0a0e1a 0%, #16213e 100%); padding: 1.5rem 2rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
            <div>
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <span style="font-size: 2.5rem;">🌊</span>
                    <div>
                        <div style="color: #ffffff; font-size: 1.8rem; font-weight: 700; letter-spacing: -0.5px;">CivicFlood AI</div>
                        <div style="color: #8ecae6; font-size: 0.85rem; letter-spacing: 1px;">National Emergency Operations Center</div>
                    </div>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 1.5rem; flex-wrap: wrap;">
                <span style="background: rgba(0, 255, 135, 0.15); color: #00ff87; padding: 0.3rem 1rem; border-radius: 20px; font-size: 0.7rem; font-weight: 600; border: 1px solid rgba(0, 255, 135, 0.2);">🟢 SYSTEM ACTIVE</span>
                <span style="color: #8ecae6; font-size: 0.7rem; opacity: 0.7;">🕐 {datetime.now().strftime('%d %b %Y, %H:%M')} UTC</span>
                <span style="color: rgba(255,255,255,0.2); font-size: 0.7rem;">v3.0.0</span>
            </div>
        </div>
        <div style="margin-top: 0.8rem; display: flex; gap: 0.8rem; flex-wrap: wrap;">
            <span style="background: rgba(255,255,255,0.05); padding: 0.2rem 0.8rem; border-radius: 12px; font-size: 0.7rem; color: #8ecae6;">🏆 Ghana AI Innovation Challenge 2026</span>
            <span style="background: rgba(255,255,255,0.05); padding: 0.2rem 0.8rem; border-radius: 12px; font-size: 0.7rem; color: #8ecae6;">🇬🇭 Public Services AI</span>
            <span style="background: rgba(255,255,255,0.05); padding: 0.2rem 0.8rem; border-radius: 12px; font-size: 0.7rem; color: #8ecae6;">📊 5 Data Sources Active</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
