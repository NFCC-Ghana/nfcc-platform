"""
National Command Center - Real-time national flood intelligence.
"""

import streamlit as st
import pandas as pd
import plotly.express as px

def get_national_data():
    """Get national flood intelligence data."""
    
    # In production, this would come from the NFCC API
    districts = [
        {"name": "Accra Central", "risk": 90.6, "status": "CRITICAL", "population_exposed": 102157},
        {"name": "Tema", "risk": 85.2, "status": "HIGH", "population_exposed": 85200},
        {"name": "Keta", "risk": 81.4, "status": "HIGH", "population_exposed": 45000},
        {"name": "Ho", "risk": 74.0, "status": "HIGH", "population_exposed": 38000},
        {"name": "Cape Coast", "risk": 68.2, "status": "MODERATE", "population_exposed": 32000},
        {"name": "Kumasi", "risk": 55.0, "status": "MODERATE", "population_exposed": 25000},
        {"name": "Sekondi-Takoradi", "risk": 48.5, "status": "MODERATE", "population_exposed": 18000},
        {"name": "Tamale", "risk": 35.2, "status": "LOW", "population_exposed": 8000},
        {"name": "Sunyani", "risk": 28.5, "status": "LOW", "population_exposed": 5000},
        {"name": "Accra East", "risk": 22.0, "status": "LOW", "population_exposed": 3000}
    ]
    
    return pd.DataFrame(districts)


def render_national_center() -> None:
    """Render national command center dashboard."""
    
    st.markdown("### 🏛️ National Command Center")
    st.caption("Real-time flood intelligence across Ghana")
    
    df = get_national_data()
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Districts Monitored", len(df))
    st.caption("📊 Data Source: Simulated for demonstration - connect to NFCC API for live data")
    with col2:
        high_risk = len(df[df["risk"] >= 60])
        st.metric("High Risk Districts", high_risk, delta="🔴 Critical")
    with col3:
        total_exposed = df["population_exposed"].sum()
        st.metric("Total Exposed", f"{total_exposed:,}")
    with col4:
        critical = len(df[df["risk"] >= 80])
        st.metric("Critical Districts", critical, delta="🚨 Emergency")
    
    # National ranking map (bar chart)
    fig = px.bar(
        df,
        x="name",
        y="risk",
        title="National Flood Risk Ranking",
        color="risk",
        color_continuous_scale="RdYlGn_r",
        range_color=[0, 100],
        text=df["risk"].apply(lambda x: f"{x:.1f}%")
    )
    
    fig.update_traces(textposition="outside")
    fig.update_layout(
        height=400,
        yaxis_title="Risk Score (%)",
        yaxis_range=[0, 105],
        xaxis_title=""
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Risk distribution
    col1, col2 = st.columns(2)
    
    with col1:
        risk_counts = df["status"].value_counts()
        fig2 = px.pie(
            values=risk_counts.values,
            names=risk_counts.index,
            title="Risk Distribution"
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    with col2:
        # Top 5 districts
        st.markdown("#### 🔴 Top 5 Critical Districts")
        top5 = df.nlargest(5, "risk")
        for _, row in top5.iterrows():
            color = "🔴" if row["risk"] >= 80 else "🟠" if row["risk"] >= 60 else "🟡"
            st.markdown(f"{color} **{row['name']}**: {row['risk']:.1f}% ({row['status']})")
    
    # Alert
    if critical > 0:
        st.error(f"🚨 **{critical} DISTRICTS IN CRITICAL STATE** - Immediate action required!")
    elif high_risk > 0:
        st.warning(f"⚠️ **{high_risk} DISTRICTS IN HIGH RISK** - Prepare for possible escalation")
    else:
        st.success("✅ All districts at moderate or low risk")
