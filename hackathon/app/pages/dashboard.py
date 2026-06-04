"""CivicFlood AI - Main Dashboard Page."""

import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# Page config
st.set_page_config(
    page_title="CivicFlood AI - Ghana Flood Intelligence",
    page_icon="🌊",
    layout="wide",
)

# Custom CSS
st.markdown(
    """
<style>
    .main-header {
        background: linear-gradient(135deg, #1a237e, #0d47a1);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .risk-extreme { background-color: #b71c1c; color: white; padding: 1rem; border-radius: 10px; }
    .risk-high { background-color: #e65100; color: white; padding: 1rem; border-radius: 10px; }
    .risk-moderate { background-color: #f9a825; color: black; padding: 1rem; border-radius: 10px; }
    .risk-low { background-color: #2e7d32; color: white; padding: 1rem; border-radius: 10px; }
    .metric-card {
        background-color: #f5f5f5;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
    }
    .community-report {
        background-color: #e3f2fd;
        padding: 0.75rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid #1a237e;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Header
st.markdown(
    """
<div class="main-header">
    <h1>🌊 CivicFlood AI</h1>
    <p>AI-Powered Community Flood Intelligence Platform for Ghana</p>
    <p style="font-size: 0.9rem;">Powered by NFCC | Public Services Innovation</p>
</div>
""",
    unsafe_allow_html=True,
)

# API connection
API_URL = "http://localhost:8000"


def calculate_fallback_score(rainfall):
    """Calculate risk score when API is unavailable."""
    if rainfall < 10:
        score = rainfall * 3
    elif rainfall < 30:
        score = 30 + (rainfall - 10) * 1.5
    elif rainfall < 60:
        score = 60 + (rainfall - 30) * 0.83
    else:
        score = min(100, 85 + (rainfall - 60) * 0.375)

    if score < 30:
        tier = "LOW"
    elif score < 50:
        tier = "MODERATE"
    elif score < 70:
        tier = "HIGH"
    elif score < 85:
        tier = "CRITICAL"
    else:
        tier = "EXTREME"

    return score, tier


# Sidebar
with st.sidebar:
    st.markdown("## 🎯 Control Panel")

    # Check API status
    try:
        response = requests.get(f"{API_URL}/health", timeout=3)
        if response.status_code == 200:
            st.success("✅ NFCC API Connected")
        else:
            st.warning("⚠️ API Connection Issue")
    except Exception:
        st.error("❌ API Not Reachable - Start with: ./scripts/start_production.sh")

    st.markdown("---")

    # District selection
    districts = [
        "Accra Central",
        "Accra East",
        "Accra West",
        "Tema",
        "Kumasi",
        "Takoradi",
        "Tamale",
        "Cape Coast",
    ]
    selected_district = st.selectbox("📍 Select District", districts)

    # Rainfall input
    rainfall = st.slider(
        "🌧️ Rainfall (mm)", min_value=0.0, max_value=150.0, value=45.5, step=5.0
    )

    # Simulate button
    simulate = st.button(
        "🚀 Run Flood Assessment", type="primary", use_container_width=True
    )

    st.markdown("---")
    st.markdown("### ℹ️ About")
    st.caption("CivicFlood AI v1.0")
    st.caption("Built for Ghana AI Challenge 2026")
    st.caption("Powered by NFCC Platform")

# Main content
if simulate:
    # Call NFCC API for risk score
    try:
        response = requests.post(
            f"{API_URL}/score",
            json={"location": selected_district, "precipitation": rainfall},
            timeout=10,
        )
        if response.status_code == 200:
            result = response.json()
            risk_score = result.get("score", 0)
            risk_tier = result.get("risk_tier", "LOW")
        else:
            risk_score, risk_tier = calculate_fallback_score(rainfall)
    except Exception:
        risk_score, risk_tier = calculate_fallback_score(rainfall)

    # Import hackathon AI modules
    from hackathon.ai.flood_explainer import explainer
    from hackathon.ai.impact_estimator import impact_estimator
    from hackathon.ai.timeline_predictor import timeline_predictor

    # Generate explanation
    features = {
        "precipitation": min(1.0, rainfall / 100),
        "roll_3d": 0.6 if rainfall > 30 else 0.3,
        "cumulative": 0.7 if rainfall > 50 else 0.4,
    }
    explanation = explainer.explain(risk_score, features)

    # Estimate impact
    impact = impact_estimator.estimate(risk_score, selected_district)

    # Predict timeline
    timeline = timeline_predictor.predict(risk_score)
    trend = timeline_predictor.get_trend(timeline)

    # Display results
    col1, col2 = st.columns([1, 1])

    with col1:
        risk_color_class = {
            "EXTREME": "risk-extreme",
            "CRITICAL": "risk-critical",
            "HIGH": "risk-high",
            "MODERATE": "risk-moderate",
            "LOW": "risk-low",
        }.get(risk_tier, "risk-low")

        st.markdown(
            f"""
        <div class="{risk_color_class}" style="text-align: center; padding: 2rem;">
            <h1 style="font-size: 3rem;">{risk_score:.1f}</h1>
            <h2>Flood Risk Score</h2>
            <h3>{risk_tier}</h3>
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.markdown("### 📊 Risk Timeline")
        timeline_data = timeline_predictor.format_for_dashboard(timeline, trend)
        df_timeline = pd.DataFrame(timeline_data)

        fig = px.line(
            df_timeline,
            x="date",
            y="risk",
            title="7-Day Risk Forecast",
            labels={"risk": "Risk Score", "date": "Date"},
        )
        fig.update_traces(line=dict(color="red", width=3))
        fig.add_hline(
            y=50,
            line_dash="dash",
            line_color="orange",
            annotation_text="Alert Threshold",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 🧠 Why This Risk?")
        st.markdown(f"**{explanation.detailed_explanation}**")
        st.markdown(f"**Confidence:** {int(explanation.confidence * 100)}%")

        st.markdown("### 👥 Impact Estimate")
        impact_display = impact_estimator.format_for_dashboard(impact)
        st.metric("👥 Population at Risk", impact_display["population_exposed"])
        st.metric("🏫 Schools Affected", impact_display["schools_affected"])
        st.metric("🛣️ Roads Affected (km)", impact_display["roads_affected_km"])
        st.metric("🏥 Health Facilities", impact_display["health_facilities_affected"])

    # Community Reports Section
    st.markdown("---")
    st.markdown("## 📱 Community Intelligence")
    st.markdown("*Citizen reports help validate and improve flood predictions*")

    col3, col4 = st.columns([1, 1])

    with col3:
        st.markdown("### 📝 Submit a Report")
        report_text = st.text_area(
            "Describe what you're seeing:",
            placeholder="Example: Water is entering homes on Abeka Road...",
            height=100,
        )
        if st.button("📤 Submit Report", type="secondary"):
            if report_text:
                from hackathon.ai.community_classifier import classifier

                classified = classifier.classify(report_text, selected_district)
                st.success(f"✅ Report submitted! Severity: {classified.severity}")
                st.info(
                    f"Confidence: {int(classified.confidence * 100)}% | "
                    f"Category: {classified.category}"
                )
            else:
                st.warning("Please enter a report description")

    with col4:
        st.markdown("### 📋 Recent Reports")
        # Sample reports
        sample_reports = [
            {
                "text": "Flooding on the main road near the market",
                "severity": "HIGH",
                "time": "2 hours ago",
            },
            {
                "text": "Water levels rising in the river",
                "severity": "MODERATE",
                "time": "5 hours ago",
            },
            {
                "text": "Drain blocked on Liberation Road",
                "severity": "LOW",
                "time": "1 day ago",
            },
        ]
        for report in sample_reports:
            color = {"HIGH": "🔴", "MODERATE": "🟡", "LOW": "🟢"}.get(
                report["severity"], "⚪"
            )
            st.markdown(
                f"""
            <div class="community-report">
                <b>{color} {report['severity']}</b> - {report['text']}<br>
                <small>{report['time']}</small>
            </div>
            """,
                unsafe_allow_html=True,
            )

else:
    # Landing state - show instructions
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.info("""
        ### 🌊 CivicFlood AI

        **How it works:**
        1. Select a district from the sidebar
        2. Adjust rainfall amount using the slider
        3. Click "Run Flood Assessment"

        The AI will show you:
        - Flood risk score (0-100)
        - Why the risk exists (explainable AI)
        - Impact on population, schools, and roads
        - 7-day risk forecast
        - Community reports
        """)

        st.markdown("""
        ### 🏆 Ghana AI Innovation Challenge 2026

        **Category:** Public Services - Disaster Management

        **Innovation:** AI-powered community flood intelligence

        **Key Differentiators:**
        - ✅ Explainable AI (SHAP)
        - ✅ Community-validated forecasts
        - ✅ Ghana-specific dam spillage monitoring
        - ✅ Impact estimation for vulnerable populations
        """)

# Footer
st.markdown("---")
st.markdown(
    """
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>🇬🇭 CivicFlood AI | Powered by NFCC | Built for Ghana AI Challenge 2026</p>
    <p>Data sources: CHIRPS, GloFAS, Google Flood Hub, OpenStreetMap Ghana</p>
</div>
""",
    unsafe_allow_html=True,
)
