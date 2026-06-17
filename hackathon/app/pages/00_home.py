"""CivicFlood AI - Home Page."""

import streamlit as st

st.set_page_config(page_title="CivicFlood AI - Home", page_icon="🌊", layout="wide")

st.markdown(
    """
<style>
    .hero {
        background: linear-gradient(135deg, #0a1628 0%, #1a3a5c 50%, #0f3460 100%);
        padding: 4rem 2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .hero h1 {
        font-size: 4rem;
        color: white;
        margin: 0;
    }
    .hero p {
        font-size: 1.5rem;
        color: #8ecae6;
        margin: 0.5rem 0;
    }
    .feature-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        text-align: center;
        height: 100%;
        border-top: 4px solid #0f3460;
    }
    .feature-card h3 {
        color: #0f3460;
        margin: 0.5rem 0;
    }
    .feature-card p {
        color: #666;
        font-size: 0.9rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="hero">
    <h1>🌊 CivicFlood AI</h1>
    <p>AI-Powered Community Flood Intelligence for Ghana</p>
    <p style="font-size:1rem;color:#a8d8ea;margin-top:1rem;">
        🇬🇭 Ghana AI Innovation Challenge 2026 • Public Services AI
    </p>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown("### 🚀 Key Features")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        """
    <div class="feature-card">
        <div style="font-size:3rem;">🧠</div>
        <h3>AI-Powered Intelligence</h3>
        <p>XGBoost model with R² = 0.993 predicting flood risk with 80%+ confidence</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        """
    <div class="feature-card">
        <div style="font-size:3rem;">🌊</div>
        <h3>Multi-Source Data</h3>
        <p>CHIRPS rainfall, river gauges, dam levels, soil moisture, and historical floods</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        """
    <div class="feature-card">
        <div style="font-size:3rem;">📢</div>
        <h3>Community Engagement</h3>
        <p>Real-time flood reporting, WhatsApp alerts, and community intelligence</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

st.divider()

st.markdown("### 📊 Quick Start")

col_start1, col_start2, col_start3 = st.columns(3)

with col_start1:
    if st.button("🌊 View Dashboard", use_container_width=True):
        st.switch_page("pages/01_dashboard.py")

with col_start2:
    if st.button("📢 Report Flood", use_container_width=True):
        st.switch_page("pages/04_community_report.py")

with col_start3:
    st.markdown(
        """
    <div style="text-align:center;padding:0.7rem;background:#f0f2f6;border-radius:8px;">
        <span style="color:#888;">📖 Documentation</span>
    </div>
    """,
        unsafe_allow_html=True,
    )
