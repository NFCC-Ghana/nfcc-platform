"""CivicFlood AI Dashboard - Original Design with Hydrological Intelligence."""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import sys
from pathlib import Path

# Fix path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.hydrology.unified_intelligence import unified_intelligence

st.set_page_config(
    page_title="CivicFlood AI - National Flood Intelligence",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# ORIGINAL DATA - PRESERVED
# ============================================================

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

# ============================================================
# MAIN DASHBOARD - ORIGINAL DESIGN PRESERVED
# ============================================================

def main():
    # Header - ORIGINAL
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
    
    # Sidebar - ORIGINAL
    with st.sidebar:
        st.markdown("## 🎛️ Controls")
        district = st.selectbox("📍 Select District", list(DISTRICTS.keys()), index=0)
        
        st.markdown("### 🌧️ Rainfall (mm)")
        rainfall_mm = st.slider(
            "Rainfall amount (mm)",
            min_value=0,
            max_value=200,
            value=75,
            help="Current 24-hour rainfall"
        )
        
        st.divider()
        
        st.markdown("### 📊 Data Sources")
        sources = [
            "CHIRPS Rainfall",
            "Open-Meteo Forecast",
            "NASA SMAP",
            "Sentinel-1 SAR",
            "Ghana River Gauges",
            "Dam Database"
        ]
        for source in sources:
            st.markdown(f"✅ {source}")
        
        st.divider()
        st.markdown("### 📱 Community")
        st.caption("v3.0.0 • Hackathon Submission")
    
    # ============================================================
    # GET ASSESSMENT DATA
    # ============================================================
    
    with st.spinner(f"🔄 Analyzing {district}..."):
        try:
            assessment = unified_intelligence.get_complete_risk_assessment(district, rainfall_mm)
        except Exception as e:
            st.warning(f"Using fallback data: {e}")
            assessment = {
                'composite_risk': {'score': 50, 'category': 'MODERATE', 'confidence': 0.7},
                'rainfall': {'current_mm': rainfall_mm, 'rain_3d_mm': rainfall_mm * 2.3, 
                            'rain_7d_mm': rainfall_mm * 4.9, 'rain_30d_mm': rainfall_mm * 21.2},
                'river': {'river': 'Odaw', 'current_level_m': 0.49, 'status': 'NORMAL'},
                'dam_risk': {'total_risk': 'LOW', 'dams_at_risk': 0},
                'soil': {'saturation_percent': 65, 'runoff_potential': 'MODERATE', 
                        'flash_flood_risk': 'LOW', 'saturation_index': 0.65},
                'history': {'total_events': 1, 'risk_level': 'LOW'},
                'recommendations': [],
                'details': {'risk_factors': {'factors': {'rainfall': 50, 'river': 30, 
                                                         'dam': 20, 'soil': 60, 'history': 20}}}
            }
    
    # ============================================================
    # DISTRICT HEADER - ORIGINAL
    # ============================================================
    
    info = DISTRICTS[district]
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"### 📍 {district}")
        st.caption(f"Region: {info['region']}")
    with col2:
        st.metric("Population", f"{info['population']:,}")
    with col3:
        st.metric("Coordinates", f"{info['lat']:.2f}, {info['lon']:.2f}")
    with col4:
        st.metric("Rainfall", f"{rainfall_mm} mm")
    
    st.divider()
    
    # ============================================================
    # RISK SCORE - ORIGINAL LAYOUT
    # ============================================================
    
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
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.markdown(f"## {emoji} Risk Score")
        st.markdown(f"<h1 style='color: {color};'>{risk_score:.1f}%</h1>", unsafe_allow_html=True)
        st.caption(f"Category: {risk_category}")
    with col2:
        st.markdown("## 📊 Confidence")
        st.progress(confidence, text=f"{confidence*100:.0f}%")
    with col3:
        river = assessment.get('river', {})
        river_status = river.get('status', 'NORMAL')
        river_emoji = "🟢" if river_status == 'NORMAL' else "🟡" if river_status == 'WARNING' else "🔴"
        st.markdown(f"## {river_emoji} River Status")
        st.markdown(f"**{river.get('river', 'Unknown')}**")
        st.caption(f"Level: {river.get('current_level_m', 0):.2f}m • {river_status}")
    
    st.divider()
    
    # ============================================================
    # RAINFALL DETAILS - ORIGINAL
    # ============================================================
    
    st.markdown("## 🌧️ Rainfall Details")
    
    rd = assessment.get('rainfall', {})
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Current", f"{rd.get('current_mm', 0)} mm")
    with col2:
        st.metric("3-Day Total", f"{rd.get('rain_3d_mm', 0):.1f} mm")
    with col3:
        st.metric("7-Day Total", f"{rd.get('rain_7d_mm', 0):.1f} mm")
    with col4:
        st.metric("30-Day Total", f"{rd.get('rain_30d_mm', 0):.1f} mm")
    
    if rd.get('rain_3d_mm', 0) > 100:
        st.warning("⚠️ 3-day accumulation critical for flood risk assessment")
    elif rd.get('rain_3d_mm', 0) > 50:
        st.info("ℹ️ 3-day accumulation significant - monitor conditions")
    
    st.divider()
    
    # ============================================================
    # HYDROLOGICAL INTELLIGENCE - NEW SECTION (ADDED, NOT REPLACING)
    # ============================================================
    
    st.markdown("## 🌊 Hydrological Intelligence")
    
    # Row 1: River, Dams, Soil, History
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        river = assessment.get('river', {})
        status = river.get('status', 'NORMAL')
        emoji = "🟢" if status == 'NORMAL' else "🟡" if status == 'WARNING' else "🔴"
        st.markdown(f"### {emoji} River")
        st.metric("Level", f"{river.get('current_level_m', 0):.2f}m")
        st.caption(f"Status: {status}")
    
    with col2:
        dam = assessment.get('dam_risk', {})
        risk_level = dam.get('total_risk', 'LOW')
        emoji = "🟢" if risk_level == 'LOW' else "🟡" if risk_level == 'MEDIUM' else "🔴"
        st.markdown(f"### {emoji} Dams")
        st.metric("Risk", risk_level)
        st.caption(f"{dam.get('dams_at_risk', 0)} dams at risk")
    
    with col3:
        soil = assessment.get('soil', {})
        saturation = soil.get('saturation_percent', 50)
        # Fix: Properly calculate saturation based on rainfall
        # If rainfall is high, saturation should be higher
        if rainfall_mm > 80:
            saturation = min(95, saturation + 20)
        elif rainfall_mm > 50:
            saturation = min(85, saturation + 10)
        
        emoji = "🟢" if saturation < 60 else "🟡" if saturation < 80 else "🔴"
        st.markdown(f"### {emoji} Soil")
        st.metric("Saturation", f"{saturation:.0f}%")
        st.caption(f"Runoff: {soil.get('runoff_potential', 'LOW')}")
    
    with col4:
        history = assessment.get('history', {})
        events = history.get('total_events', 0)
        risk_level = history.get('risk_level', 'LOW')
        emoji = "🟢" if risk_level == 'LOW' else "🟡" if risk_level == 'MODERATE' else "🔴"
        st.markdown(f"### {emoji} History")
        st.metric("Past Events", events)
        st.caption(f"Risk: {risk_level}")
    
    st.divider()
    
    # ============================================================
    # RISK FACTOR BREAKDOWN - NEW CHART
    # ============================================================
    
    st.markdown("### 📊 Risk Factor Breakdown")
    
    factors = assessment.get('details', {}).get('risk_factors', {}).get('factors', {})
    
    if factors:
        names = {
            'rainfall': 'Rainfall',
            'river': 'River Level',
            'dam': 'Dam Risk',
            'soil': 'Soil Saturation',
            'history': 'Historical Risk'
        }
        
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
            height=300,
            showlegend=False,
            xaxis_title="",
            yaxis_title="Risk Score",
            yaxis_range=[0, 105]
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No risk factors available for this district")
    
    st.divider()
    
    # ============================================================
    # RECOMMENDATIONS - ORIGINAL STYLE
    # ============================================================
    
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
    
    # ============================================================
    # FOOTER - ORIGINAL
    # ============================================================
    
    st.divider()
    st.caption("Made with ❤️ for Ghana AI Innovation Challenge 2026")

if __name__ == "__main__":
    main()

# ============================================================
# ADD THESE SECTIONS TO THE DASHBOARD
# ============================================================

# Add after the existing imports:
from src.community.community_memory import community_memory
from src.exposure.impact_estimator import impact_estimator

# Add Community Reports Section (after Hydrological Intelligence)
def render_community_reports(district: str):
    """Render community reports section."""
    st.markdown("## 📢 Community Reports")
    
    # Get reports for this district
    reports = community_memory.get_reports(district, limit=10)
    
    if reports:
        for report in reports[:5]:
            with st.container():
                st.markdown(f"**📍 {report.get('community', 'Unknown')}**")
                st.markdown(f"📝 {report.get('description', 'No description')}")
                if report.get('flood_depth_m', 0) > 0:
                    st.metric("Flood Depth", f"{report['flood_depth_m']:.1f}m")
                st.caption(f"📅 {report.get('report_time', 'Unknown')}")
                if report.get('validated'):
                    st.success("✅ Validated")
                st.divider()
    else:
        st.info("No community reports for this district")
    
    # Submit report form
    with st.expander("📝 Submit Community Report"):
        with st.form("community_report"):
            community = st.text_input("Community name")
            report_type = st.selectbox("Report type", ["flood", "water_level", "weather"])
            description = st.text_area("Description")
            flood_depth = st.number_input("Flood depth (m)", 0.0, 5.0, 0.0)
            reporter_name = st.text_input("Your name (optional)")
            reporter_phone = st.text_input("Phone number (optional)")
            
            if st.form_submit_button("Submit Report"):
                report_data = {
                    'district': district,
                    'community': community,
                    'report_type': report_type,
                    'description': description,
                    'flood_depth_m': flood_depth,
                    'reporter_name': reporter_name,
                    'reporter_phone': reporter_phone
                }
                result = community_memory.submit_report(report_data)
                if result:
                    st.success("✅ Report submitted successfully! Thank you for helping your community.")
                else:
                    st.error("❌ Failed to submit report. Please try again.")

# Add Impact Assessment Section (after Community Reports)
def render_impact_assessment(district: str, risk_score: float):
    """Render impact assessment section."""
    st.markdown("## 👥 Impact Assessment")
    
    impact = impact_estimator.estimate_impact(district, risk_score)
    
    if impact.get('error'):
        st.warning(impact['error'])
        return
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Population Exposed", f"{impact['population_exposed']:,}")
    with col2:
        st.metric("Children Exposed", f"{impact['children_exposed']:,}")
    with col3:
        st.metric("Schools at Risk", impact['schools_exposed'])
    with col4:
        st.metric("Hospitals at Risk", impact['hospitals_exposed'])
    
    st.caption(f"Exposure Percentage: {impact['exposure_percentage']:.1f}% of district area")

# Add Forecast Weather Section (after Impact Assessment)
def render_weather_forecast(district: str):
    """Render weather forecast section."""
    st.markdown("## 🌤️ Weather Forecast")
    
    # Get forecast from rainfall history
    forecast = rainfall_history.get_forecast(district, hours=72)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("24h Forecast", f"{forecast.get('24h', 0)} mm")
        st.caption("Today")
    with col2:
        st.metric("48h Forecast", f"{forecast.get('48h', 0)} mm")
        st.caption("Tomorrow")
    with col3:
        st.metric("72h Forecast", f"{forecast.get('72h', 0)} mm")
        st.caption("Day 3")
    
    # Risk escalation warning
    max_forecast = max(forecast.values()) if forecast else 0
    if max_forecast > 30:
        st.warning("⚠️ Significant rainfall expected in the next 72 hours. Monitor conditions closely.")
    elif max_forecast > 15:
        st.info("ℹ️ Moderate rainfall expected. Stay informed.")

# Add these sections in the main() function after Hydrological Intelligence:
# render_weather_forecast(district)
# render_impact_assessment(district, risk_score)
# render_community_reports(district)

# ================================================================
# NEW SECTION: WEATHER FORECAST PANEL (Added without removing existing)
# ================================================================

def render_weather_forecast_panel(district: str):
    """Render weather forecast panel."""
    st.markdown("## 🌤️ Weather Forecast")
    
    try:
        from src.hydrology.weather_forecast import weather_forecast
        
        with st.spinner("Fetching forecast..."):
            forecast = weather_forecast.get_forecast_for_district(district)
        
        col1, col2, col3 = st.columns(3)
        
        for i, key in enumerate(['24h', '48h', '72h']):
            value = forecast.get(key, 0)
            with [col1, col2, col3][i]:
                st.metric(f"{key} Forecast", f"{value} mm")
        
        if forecast.get('daily'):
            with st.expander("📊 Daily Breakdown"):
                for day in forecast['daily']:
                    st.caption(f"  Day {day['day']}: {day['rainfall_mm']} mm")
        
        st.caption(f"Source: {forecast.get('source', 'Open-Meteo')}")
        
        # Risk warning
        max_forecast = max([forecast.get('24h', 0), forecast.get('48h', 0), forecast.get('72h', 0)])
        if max_forecast > 30:
            st.warning("⚠️ Significant rainfall expected in the next 72 hours")
        elif max_forecast > 15:
            st.info("ℹ️ Moderate rainfall expected")
            
    except Exception as e:
        st.warning(f"⚠️ Forecast temporarily unavailable: {e}")

# ================================================================
# NEW SECTION: SUBSCRIPTION PANEL (Added without removing existing)
# ================================================================

def render_subscription_panel(district: str):
    """Render subscription panel."""
    st.markdown("## 🔔 Alert Subscriptions")
    
    try:
        from src.alerts.subscriptions import subscription_manager
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            phone = st.text_input("Phone Number (with country code)", 
                                 placeholder="+233 XX XXX XXXX",
                                 key="subscribe_phone")
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Subscribe", key="subscribe_btn"):
                    if phone and len(phone) > 8:
                        result = subscription_manager.subscribe(phone, district)
                        if result:
                            st.success(f"✅ Subscribed! You will receive alerts for {district}")
                        else:
                            st.error("❌ Failed to subscribe")
                    else:
                        st.warning("⚠️ Please enter a valid phone number")
            
            with col_b:
                if st.button("Unsubscribe", key="unsubscribe_btn"):
                    if phone:
                        result = subscription_manager.unsubscribe(phone)
                        if result:
                            st.success("✅ Unsubscribed")
        
        with col2:
            stats = subscription_manager.get_stats()
            st.metric("Total Subscribers", stats.get('total_subscribers', 0))
            st.metric("WhatsApp", stats.get('whatsapp_verified', 0))
            st.metric("SMS", stats.get('sms_verified', 0))
            
    except Exception as e:
        st.warning(f"⚠️ Subscription service temporarily unavailable: {e}")

# ================================================================
# NEW SECTION: FLOOD EVENT HISTORY PANEL (Added without removing existing)
# ================================================================

def render_flood_history_panel(district: str):
    """Render flood event history panel."""
    st.markdown("## 📜 Flood Event History")
    
    try:
        import json
        from pathlib import Path
        
        events_path = Path("data/events/flood_events.json")
        
        if events_path.exists():
            with open(events_path) as f:
                data = json.load(f)
            
            events = data.get('events', [])
            
            # Filter events for this district
            district_events = []
            for event in events:
                if district in event.get('districts', []):
                    district_events.append(event)
            
            if district_events:
                for event in district_events[:5]:
                    with st.container():
                        severity = event.get('severity', 'MODERATE')
                        emoji = "🔴" if severity == 'CRITICAL' else "🟠" if severity == 'HIGH' else "🟡"
                        st.markdown(f"{emoji} **{event['date']}** - {event['cause'].replace('_', ' ').title()}")
                        st.caption(f"Affected: {event.get('affected_population', 0):,} people")
                        st.caption(f"Description: {event.get('description', '')[:100]}...")
                        st.divider()
            else:
                st.info("No historical flood events recorded for this district")
        else:
            st.info("No flood event database found")
            
    except Exception as e:
        st.warning(f"⚠️ Event history temporarily unavailable: {e}")

# ================================================================
# MODIFIED MAIN - Add new sections (without removing existing)
# ================================================================

# To be added in the main() function after the "Actionable Recommendations" section:
# render_weather_forecast_panel(district)
# render_subscription_panel(district)
# render_flood_history_panel(district)
