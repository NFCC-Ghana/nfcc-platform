"""CivicFlood AI Dashboard - Enhanced with hydrological intelligence."""

import sys
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd
import plotly.express as px

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.hydrology.unified_intelligence import unified_intelligence

st.set_page_config(
    page_title="CivicFlood AI - National Flood Intelligence",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Define districts
DISTRICTS = {
    "Accra Central": {"region": "Greater Accra", "population": 187928, "lat": 5.560, "lon": -0.210},
    "Accra West": {"region": "Greater Accra", "population": 203461, "lat": 5.550, "lon": -0.230},
    "Accra East": {"region": "Greater Accra", "population": 142587, "lat": 5.565, "lon": -0.190},
    "Tema": {"region": "Greater Accra", "population": 198742, "lat": 5.650, "lon": -0.020},
    "Kumasi": {"region": "Ashanti", "population": 443981, "lat": 6.670, "lon": -1.620},
    "Tamale": {"region": "Northern", "population": 371578, "lat": 9.400, "lon": -0.840},
    "Sekondi-Takoradi": {"region": "Western", "population": 245567, "lat": 4.920, "lon": -1.710},
    "Cape Coast": {"region": "Central", "population": 169894, "lat": 5.105, "lon": -1.250},
    "Ho": {"region": "Volta", "population": 153705, "lat": 6.600, "lon": 0.470},
    "Sunyani": {"region": "Bono", "population": 138256, "lat": 7.336, "lon": -2.348}
}

def main():
    """Main dashboard function."""
    # Header
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown("# 🌊 CivicFlood AI")
        st.markdown("*National Flood Intelligence Platform • Ghana AI Innovation Challenge 2026*")
    with col2:
        st.markdown("🟢 SYSTEM ACTIVE")
        st.caption(f"Last Updated: {datetime.now().strftime('%d %b %Y, %H:%M')}")
    with col3:
        st.markdown("**v3.0.0**")
        st.caption("Hackathon Submission")
    st.divider()

    # Sidebar
    with st.sidebar:
        st.markdown("## 🎛️ Controls")
        district = st.selectbox("📍 Select District", list(DISTRICTS.keys()), index=0)
        st.markdown("### 🌧️ Rainfall (mm)")
        rainfall_mm = st.slider("Rainfall amount (mm)", 0, 200, 75)
        st.divider()
        st.markdown("### 📊 Data Sources")
        for src in ["CHIRPS Rainfall", "Open-Meteo Forecast", "NASA SMAP", "Sentinel-1 SAR", "Ghana River Gauges", "Dam Database"]:
            st.markdown(f"✅ {src}")
        st.divider()
        st.markdown("### 📱 Community")
        st.caption("v3.0.0 • Hackathon Submission")

    # Get assessment
    with st.spinner(f"🔄 Analyzing {district}..."):
        assessment = unified_intelligence.get_complete_risk_assessment(district, rainfall_mm)

    # District header
    info = DISTRICTS[district]
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"### 📍 {district}")
        st.caption(f"Region: {info['region']}")
    with c2:
        st.metric("Population", f"{info['population']:,}")
    with c3:
        st.metric("Coordinates", f"{info['lat']:.2f}, {info['lon']:.2f}")
    with c4:
        st.metric("Rainfall", f"{rainfall_mm} mm")
    st.divider()

    # Risk Score
    risk = assessment.get('composite_risk', {})
    risk_score = risk.get('score', 50)
    risk_category = risk.get('category', 'LOW')
    confidence = risk.get('confidence', 0.7)

    if risk_score >= 80:
        color, emoji = "#ff0000", "🔴"
    elif risk_score >= 60:
        color, emoji = "#ff6600", "🟠"
    elif risk_score >= 40:
        color, emoji = "#ffaa00", "🟡"
    else:
        color, emoji = "#00cc00", "🟢"

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        st.markdown(f"## {emoji} Risk Score")
        st.markdown(f"<h1 style='color:{color};'>{risk_score:.1f}%</h1>", unsafe_allow_html=True)
        st.caption(f"Category: {risk_category}")
    with c2:
        st.markdown("## 📊 Confidence")
        st.progress(confidence, text=f"{confidence*100:.0f}%")
    with c3:
        river = assessment.get('river', {})
        river_status = river.get('status', 'NORMAL')
        river_emoji = "🟢" if river_status == 'NORMAL' else "🟡" if river_status == 'WARNING' else "🔴"
        st.markdown(f"## {river_emoji} River Status")
        st.markdown(f"**{river.get('river', 'Unknown')}**")
        st.caption(f"Level: {river.get('current_level_m', 0):.2f}m • {river_status}")
    st.divider()

    # Rainfall Details
    st.markdown("## 🌧️ Rainfall Details")
    rd = assessment.get('rainfall', {})
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Current", f"{rd.get('current_mm', 0)} mm")
    with c2:
        st.metric("3-Day Total", f"{rd.get('rain_3d_mm', 0):.1f} mm")
    with c3:
        st.metric("7-Day Total", f"{rd.get('rain_7d_mm', 0):.1f} mm")
    with c4:
        st.metric("30-Day Total", f"{rd.get('rain_30d_mm', 0):.1f} mm")

    if rd.get('rain_3d_mm', 0) > 100:
        st.warning("⚠️ 3-day accumulation critical for flood risk assessment")
    elif rd.get('rain_3d_mm', 0) > 50:
        st.info("ℹ️ 3-day accumulation significant - monitor conditions")
    st.divider()

    # Hydrological Intelligence
    st.markdown("## 🌊 Hydrological Intelligence")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        river = assessment.get('river', {})
        status = river.get('status', 'NORMAL')
        emoji = "🟢" if status == 'NORMAL' else "🟡" if status == 'WARNING' else "🔴"
        st.markdown(f"### {emoji} River")
        st.metric("Level", f"{river.get('current_level_m', 0):.2f}m")
        st.caption(f"Status: {status}")

    with c2:
        dam = assessment.get('dam_risk', {})
        risk_level = dam.get('total_risk', 'LOW')
        emoji = "🟢" if risk_level == 'LOW' else "🟡" if risk_level == 'MEDIUM' else "🔴"
        st.markdown(f"### {emoji} Dams")
        st.metric("Risk", risk_level)
        st.caption(f"{dam.get('dams_at_risk', 0)} dams at risk")

    with c3:
        soil = assessment.get('soil', {})
        saturation = soil.get('saturation_percent', 50)
        emoji = "🟢" if saturation < 60 else "🟡" if saturation < 80 else "🔴"
        st.markdown(f"### {emoji} Soil")
        st.metric("Saturation", f"{saturation:.0f}%")
        st.caption(f"Runoff: {soil.get('runoff_potential', 'LOW')}")

    with c4:
        history = assessment.get('history', {})
        events = history.get('total_events', 0)
        risk_level = history.get('risk_level', 'LOW')
        emoji = "🟢" if risk_level == 'LOW' else "🟡" if risk_level == 'MODERATE' else "🔴"
        st.markdown(f"### {emoji} History")
        st.metric("Past Events", events)
        st.caption(f"Risk: {risk_level}")
    st.divider()

    # Risk Factor Breakdown
    st.markdown("### 📊 Risk Factor Breakdown")
    factors = assessment.get('details', {}).get('risk_factors', {}).get('factors', {})
    if factors:
        names = {'rainfall': 'Rainfall', 'river': 'River Level', 'dam': 'Dam Risk',
                 'soil': 'Soil Saturation', 'history': 'Historical Risk'}
        chart_data = pd.DataFrame({
            'Factor': [names.get(k, k) for k in factors.keys()],
            'Score': list(factors.values())
        })
        fig = px.bar(
            chart_data,
            x='Factor',
            y='Score',
            title='Risk Factor Contributions',
            color='Score',
            color_continuous_scale='RdYlGn_r',
            range_color=[0, 100],
            text=chart_data['Score'].apply(lambda x: f'{x:.0f}')
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(
            height=350,
            showlegend=False,
            xaxis_title="",
            yaxis_title="Risk Score",
            yaxis_range=[0, 105]
        )
        st.plotly_chart(fig, use_container_width=True)
    st.divider()

    # Recommendations
    st.markdown("### 🚨 Actionable Recommendations")
    recs = assessment.get('recommendations', [])
    if recs:
        for rec in recs[:5]:
            priority = rec.get('priority', 'LOW')
            if priority == 'CRITICAL':
                st.error(f"🚨 {rec['action']}")
            elif priority == 'HIGH':
                st.warning(f"⚠️ {rec['action']}")
            elif priority == 'MEDIUM':
                st.info(f"ℹ️ {rec['action']}")
            else:
                st.success(f"✅ {rec['action']}")
            st.caption(f"🎯 {rec.get('target', 'All residents')} | ⏱️ {rec.get('timeframe', 'Monitor')}")
            st.divider()
    else:
        st.success("✅ No immediate recommendations. Monitor conditions.")

    st.divider()
    st.caption("Made with ❤️ for Ghana AI Innovation Challenge 2026")

if __name__ == "__main__":
    main()
