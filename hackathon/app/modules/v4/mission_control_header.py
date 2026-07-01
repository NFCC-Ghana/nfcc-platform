"""
Mission Control Header - National Emergency Operations Center
"""

import streamlit as st
from datetime import datetime

def render_mission_control_header(api_status: str = "healthy") -> None:
    """Render the National Emergency Operations Center header."""
    
    st.markdown("""
    <style>
    .eoc-header {
        background: linear-gradient(135deg, #0a0e17 0%, #1a1a2e 40%, #16213e 100%);
        padding: 1.2rem 2rem;
        border-radius: 12px;
        border-bottom: 3px solid #00ff88;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px rgba(0,255,136,0.1);
    }
    .eoc-title {
        color: #00ff88;
        font-size: 1.8rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: 1px;
    }
    .eoc-subtitle {
        color: #8ecae6;
        font-size: 0.9rem;
        margin: 0;
        opacity: 0.8;
    }
    .eoc-status {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        background: rgba(0,255,136,0.1);
        padding: 0.3rem 1rem;
        border-radius: 20px;
        border: 1px solid rgba(0,255,136,0.2);
    }
    .eoc-status-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #00ff88;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(0.8); }
        100% { opacity: 1; transform: scale(1); }
    }
    .eoc-time {
        color: #8ecae6;
        font-size: 0.8rem;
        opacity: 0.7;
    }
    </style>
    """, unsafe_allow_html=True)
    
    status_color = "#00ff88" if api_status == "healthy" else "#ffaa00"
    status_text = "SYSTEM ACTIVE" if api_status == "healthy" else "DEGRADED"
    
    st.markdown(f"""
    <div class="eoc-header">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
            <div>
                <div class="eoc-title">🇬🇭 NATIONAL EMERGENCY OPERATIONS CENTER</div>
                <div class="eoc-subtitle">CivicFlood AI • National Flood Intelligence Platform</div>
            </div>
            <div style="display: flex; align-items: center; gap: 1.5rem; flex-wrap: wrap;">
                <div class="eoc-status">
                    <span class="eoc-status-dot"></span>
                    <span style="color: #00ff88; font-weight: 600;">{status_text}</span>
                </div>
                <div class="eoc-time">🕐 {datetime.now().strftime('%d %b %Y, %H:%M UTC')}</div>
                <div style="color: #8ecae6; font-size: 0.8rem; border: 1px solid rgba(255,255,255,0.1); padding: 0.2rem 0.8rem; border-radius: 12px;">
                    v3.0.0
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
