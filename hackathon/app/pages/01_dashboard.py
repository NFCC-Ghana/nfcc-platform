"""CivicFlood AI - Professional Dashboard with Hydrological Intelligence."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Import hydrological intelligence
try:
    from hackathon.ai.hydrological_intelligence import civicflood_hydrological

    HYDRO_AVAILABLE = True
except ImportError:
    HYDRO_AVAILABLE = False

# Page config
st.set_page_config(
    page_title="CivicFlood AI - National Flood Intelligence",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for professional look
st.markdown(
    """
<style>
    /* Global styling */
    .main {
        background: #f0f2f6;
    }

    /* Header styling */
    .header-container {
        background: linear-gradient(135deg, #0a1628 0%, #1a3a5c 50%, #0f3460 100%);
        padding: 2rem 2rem 1.5rem 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    .header-container h1 {
        color: white;
        font-size: 2.5rem;
        margin: 0;
        font-weight: 700;
    }
    .header-container .subtitle {
        color: #8ecae6;
        font-size: 1.1rem;
        margin: 0.3rem 0 0 0;
    }
    .header-container .status-badge {
        display: inline-block;
        background: #00ff87;
        color: #0a1628;
        padding: 0.3rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.8rem;
        margin-top: 0.5rem;
    }

    /* Metric cards */
    .metric-card {
        background: white;
        padding: 1.2rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        text-align: center;
        border-top: 4px solid #0f3460;
    }
    .metric-card .value {
        font-size: 2rem;
        font-weight: bold;
        color: #0f3460;
    }
    .metric-card .label {
        color: #666;
        font-size: 0.85rem;
        margin-top: 0.2rem;
    }

    /* Risk gauge */
    .risk-gauge-container {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        text-align: center;
    }

    /* Info boxes */
    .info-box {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #0f3460;
        margin: 0.5rem 0;
    }

    /* Custom sidebar */
    .sidebar-section {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }

    /* Divider */
    .custom-divider {
        border: none;
        height: 2px;
        background: linear-gradient(to right, transparent, #0f3460, transparent);
        margin: 2rem 0;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Districts data
DISTRICTS = {
    "Accra Central": {
        "lat": 5.560,
        "lon": -0.210,
        "region": "Greater Accra",
        "population": 187928,
    },
    "Accra West": {
        "lat": 5.550,
        "lon": -0.230,
        "region": "Greater Accra",
        "population": 203461,
    },
    "Accra East": {
        "lat": 5.565,
        "lon": -0.190,
        "region": "Greater Accra",
        "population": 142587,
    },
    "Tema": {
        "lat": 5.650,
        "lon": -0.020,
        "region": "Greater Accra",
        "population": 198742,
    },
    "Kumasi": {"lat": 6.670, "lon": -1.620, "region": "Ashanti", "population": 443981},
    "Tamale": {"lat": 9.400, "lon": -0.840, "region": "Northern", "population": 371578},
    "Sekondi-Takoradi": {
        "lat": 4.920,
        "lon": -1.710,
        "region": "Western",
        "population": 245567,
    },
    "Cape Coast": {
        "lat": 5.105,
        "lon": -1.250,
        "region": "Central",
        "population": 169894,
    },
    "Ho": {"lat": 6.600, "lon": 0.470, "region": "Volta", "population": 153705},
    "Sunyani": {"lat": 7.336, "lon": -2.348, "region": "Bono", "population": 138256},
}


def safe_metric_value(value):
    """Convert value to int/float/str/None for Streamlit metrics."""
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        return len(value)
    if value is None:
        return 0
    return value


def create_risk_gauge(score: float):
    """Create a professional risk gauge chart."""
    # Determine color based on score
    if score >= 80:
        color = "#ff4444"
        label = "EXTREME"
    elif score >= 65:
        color = "#ff8c00"
        label = "HIGH"
    elif score >= 45:
        color = "#ffd93d"
        label = "MODERATE"
    elif score >= 25:
        color = "#6bcf7f"
        label = "LOW"
    else:
        color = "#00ff87"
        label = "VERY LOW"

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=score,
            title={"text": f"<b>{label}</b>", "font": {"size": 20}},
            domain={"x": [0, 1], "y": [0, 1]},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "darkblue"},
                "bar": {"color": color},
                "steps": [
                    {"range": [0, 25], "color": "#00ff87"},
                    {"range": [25, 45], "color": "#6bcf7f"},
                    {"range": [45, 65], "color": "#ffd93d"},
                    {"range": [65, 80], "color": "#ff8c00"},
                    {"range": [80, 100], "color": "#ff4444"},
                ],
                "threshold": {
                    "line": {"color": "white", "width": 4},
                    "thickness": 0.75,
                    "value": score,
                },
                "bgcolor": "white",
                "bordercolor": "#ddd",
                "borderwidth": 2,
            },
            number={"font": {"size": 40, "color": color}, "suffix": "%"},
        )
    )

    fig.update_layout(
        height=280,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    return fig


def render_hydrological_panel(data: dict):
    """Render the hydrological intelligence panel."""

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
    st.markdown("### 🌊 Hydrological Intelligence")

    # Four columns for hydrological components
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        with st.container():
            st.markdown(
                """
            <div style="background:white;padding:1rem;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,0.06);border-top:4px solid #0f3460;height:100%;">
            """,
                unsafe_allow_html=True,
            )
            st.markdown("#### 🌊 River")
            river = data.get("river", {})
            status = river.get("status", "NORMAL")
            status_color = (
                "🟢" if status == "NORMAL" else "🟡" if status == "WARNING" else "🔴"
            )
            st.markdown(f"{status_color} **{river.get('river', 'Unknown')}**")
            st.metric("Level", f"{river.get('current_level_m', 0):.2f}m")
            st.metric("Status", status)
            st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        with st.container():
            st.markdown(
                """
            <div style="background:white;padding:1rem;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,0.06);border-top:4px solid #ff8c00;height:100%;">
            """,
                unsafe_allow_html=True,
            )
            st.markdown("#### 🏗️ Dams")
            dam = data.get("dam", {})
            risk = dam.get("total_risk", "LOW")
            risk_color = "🟢" if risk == "LOW" else "🟡" if risk == "MEDIUM" else "🔴"
            st.markdown(f"{risk_color} **{risk} Risk**")
            dams_at_risk = safe_metric_value(dam.get("dams_at_risk", 0))
            st.metric("Dams at Risk", dams_at_risk)
            st.markdown("</div>", unsafe_allow_html=True)

    with col3:
        with st.container():
            st.markdown(
                """
            <div style="background:white;padding:1rem;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,0.06);border-top:4px solid #6bcf7f;height:100%;">
            """,
                unsafe_allow_html=True,
            )
            st.markdown("#### 💧 Soil")
            soil = data.get("soil", {})
            saturation = soil.get("saturation_index", 0.5)
            st.progress(saturation, text=f"Saturation: {saturation*100:.0f}%")
            st.metric("Runoff", soil.get("runoff_potential", "LOW"))
            st.metric("Flash Flood", soil.get("flash_flood_risk", "LOW"))
            st.markdown("</div>", unsafe_allow_html=True)

    with col4:
        with st.container():
            st.markdown(
                """
            <div style="background:white;padding:1rem;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,0.06);border-top:4px solid #ffd93d;height:100%;">
            """,
                unsafe_allow_html=True,
            )
            st.markdown("#### 📜 History")
            history = data.get("history", {})
            st.metric("Past Events", history.get("total_events", 0))
            st.metric("Risk Level", history.get("risk_level", "LOW"))
            st.markdown("</div>", unsafe_allow_html=True)


def render_risk_factors(data: dict):
    """Render risk factor breakdown chart."""

    risk_factors = data.get("risk_factors", {}).get("factors", {})

    if risk_factors:
        st.markdown("### 📊 Risk Factor Breakdown")

        factor_names = {
            "rainfall": "Rainfall",
            "river": "River Level",
            "dam": "Dam Risk",
            "soil": "Soil Saturation",
            "history": "Historical Risk",
        }

        colors = {
            "rainfall": "#0f3460",
            "river": "#1a5a8c",
            "dam": "#ff8c00",
            "soil": "#6bcf7f",
            "history": "#ffd93d",
        }

        chart_data = pd.DataFrame(
            {
                "Factor": [factor_names.get(k, k) for k in risk_factors.keys()],
                "Score": list(risk_factors.values()),
                "Color": [colors.get(k, "#888") for k in risk_factors.keys()],
            }
        )

        fig = px.bar(
            chart_data,
            x="Factor",
            y="Score",
            title="",
            color="Factor",
            color_discrete_sequence=[
                "#0f3460",
                "#1a5a8c",
                "#ff8c00",
                "#6bcf7f",
                "#ffd93d",
            ],
            text="Score",
        )

        fig.update_traces(
            textposition="outside", texttemplate="%{text:.0f}%", marker_line_width=0
        )

        fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=20, b=20),
            showlegend=False,
            yaxis_title="Risk Contribution (%)",
            yaxis_range=[0, 100],
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )

        st.plotly_chart(fig, use_container_width=True)


def render_recommendations(recommendations: list):
    """Render actionable recommendations."""

    if recommendations:
        st.markdown("### 🚨 Actionable Recommendations")

        for rec in recommendations[:5]:
            priority = rec.get("priority", "LOW")
            action = rec["action"]
            target = rec.get("target", "All residents")
            timeframe = rec.get("timeframe", "Immediate")

            if priority == "CRITICAL":
                st.error(f"🔴 {action}")
                st.caption(f"🎯 {target} | ⏱️ {timeframe}")
            elif priority == "HIGH":
                st.warning(f"🟠 {action}")
                st.caption(f"🎯 {target} | ⏱️ {timeframe}")
            elif priority == "MEDIUM":
                st.info(f"🟡 {action}")
                st.caption(f"🎯 {target} | ⏱️ {timeframe}")
            else:
                st.success(f"🟢 {action}")
                st.caption(f"🎯 {target} | ⏱️ {timeframe}")

            st.divider()


def main():
    # ============================================
    # HEADER
    # ============================================
    st.markdown(
        """
    <div class="header-container">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div>
                <h1>🌊 CivicFlood AI</h1>
                <p class="subtitle">National Flood Intelligence Platform • Ghana AI Innovation Challenge 2026</p>
                <span class="status-badge">🟢 SYSTEM ACTIVE</span>
            </div>
            <div style="text-align:right;">
                <div style="font-size:0.8rem;color:#8ecae6;">Last Updated</div>
                <div style="color:white;font-weight:bold;">"""
        + datetime.now().strftime("%d %b %Y, %H:%M")
        + """</div>
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ============================================
    # SIDEBAR
    # ============================================
    with st.sidebar:
        st.markdown("### 🎛️ Controls")

        district = st.selectbox("📍 Select District", list(DISTRICTS.keys()), index=0)

        rainfall_mm = st.slider(
            "🌧️ Rainfall (mm)",
            min_value=0,
            max_value=200,
            value=75,
            help="24-hour cumulative rainfall",
        )

        st.markdown("---")
        st.markdown("### 📊 Data Sources")
        st.markdown("""
        - CHIRPS Rainfall
        - Open-Meteo Forecast
        - NASA SMAP
        - Sentinel-1 SAR
        - Ghana River Gauges
        - Dam Database
        """)

        st.markdown("---")
        st.markdown("### 📱 Community")
        if st.button("📢 Report Flood", use_container_width=True):
            st.switch_page("pages/04_community_report.py")

        st.caption("v3.0.0 • Hackathon Submission")

    # ============================================
    # MAIN CONTENT
    # ============================================

    # Get hydrological data
    if HYDRO_AVAILABLE:
        try:
            data = civicflood_hydrological.get_complete_dashboard_data(
                district, rainfall_mm
            )
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            data = None
    else:
        data = None
        st.warning("Hydrological intelligence module not available")

    if data:
        # ============================================
        # DISTRICT INFO AND KEY METRICS
        # ============================================
        col_info, col_metrics = st.columns([1, 2])

        with col_info:
            district_info = DISTRICTS[district]
            st.markdown(f"### 📍 {district}")
            st.markdown(f"**Region:** {district_info['region']}")
            st.markdown(f"**Population:** {district_info['population']:,}")
            st.markdown(
                f"**Coordinates:** {district_info['lat']}, {district_info['lon']}"
            )
            st.markdown(f"**Rainfall:** {rainfall_mm} mm")

        with col_metrics:
            risk = data.get("risk", {})
            score = risk.get("score", 0)
            category = risk.get("category", "LOW")
            confidence = risk.get("confidence", 0.5)

            # Key metric cards
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.markdown(
                    f"""
                <div class="metric-card">
                    <div class="value" style="color:{'#ff4444' if score>=80 else '#ff8c00' if score>=65 else '#ffd93d' if score>=45 else '#6bcf7f'}">{score:.1f}%</div>
                    <div class="label">Risk Score</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            with m2:
                st.markdown(
                    f"""
                <div class="metric-card">
                    <div class="value">{category}</div>
                    <div class="label">Category</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            with m3:
                st.markdown(
                    f"""
                <div class="metric-card">
                    <div class="value">{confidence*100:.0f}%</div>
                    <div class="label">Confidence</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            with m4:
                river_status = data.get("river", {}).get("status", "NORMAL")
                st.markdown(
                    f"""
                <div class="metric-card">
                    <div class="value">{river_status}</div>
                    <div class="label">River Status</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

        # ============================================
        # RISK GAUGE AND RAINFALL DETAILS
        # ============================================
        col_gauge, col_details = st.columns([1, 1])

        with col_gauge:
            fig = create_risk_gauge(score)
            st.plotly_chart(fig, use_container_width=True)

        with col_details:
            rainfall = data.get("rainfall", {})
            st.markdown("### 🌧️ Rainfall Details")

            r1, r2 = st.columns(2)
            with r1:
                st.metric("Current", f"{rainfall.get('current_mm', 0)} mm")
                st.metric("3-Day Total", f"{rainfall.get('rain_3d', 0):.1f} mm")
            with r2:
                st.metric("7-Day Total", f"{rainfall.get('rain_7d', 0):.1f} mm")
                st.metric("30-Day Total", f"{rainfall.get('rain_30d', 0):.1f} mm")

            st.caption("⚠️ 3-day accumulation critical for flood risk assessment")

        # ============================================
        # HYDROLOGICAL INTELLIGENCE
        # ============================================
        render_hydrological_panel(data)

        # ============================================
        # RISK FACTORS
        # ============================================
        render_risk_factors(data)

        # ============================================
        # RECOMMENDATIONS
        # ============================================
        render_recommendations(data.get("recommendations", []))

    else:
        st.error("Unable to load hydrological data. Please check the system status.")


if __name__ == "__main__":
    main()
