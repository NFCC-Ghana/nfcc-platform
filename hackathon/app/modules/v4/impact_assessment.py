"""
Impact Assessment Module - Full Implementation
Population exposure, infrastructure risk, and economic impact.
"""

import streamlit as st
import plotly.express as px
import pandas as pd


def render_impact_assessment(state):
    """Render the complete impact assessment section."""
    
    st.markdown("## 👥 Impact Assessment")
    st.caption("Lives affected, critical infrastructure, and economic impact")
    
    # Population Impact
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Lives Affected",
            f"{state.population_exposed:,}",
            delta=f"{state.exposure_percentage:.1f}% of population"
        )
    with col2:
        st.metric("Schools at Risk", state.schools_exposed)
    with col3:
        st.metric("Hospitals at Risk", state.hospitals_exposed)
    with col4:
        st.metric("Markets at Risk", state.markets_exposed)
    
    # Vulnerable Populations
    st.markdown("### 👶 Vulnerable Populations")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Children (<18)", state.children_exposed)
    with col2:
        st.metric("Elderly (>60)", state.elderly_exposed)
    with col3:
        st.metric("Disabled", state.disabled_exposed)
    with col4:
        st.metric("Pregnant Women", state.pregnant_exposed)
    
    # Economic Impact
    st.markdown("### 💰 Economic Impact")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Residential Losses", f"GH₵ {state.residential_loss_ghs:,.0f}")
        st.metric("Infrastructure Losses", f"GH₵ {state.infrastructure_loss_ghs:,.0f}")
    with col2:
        st.metric("Total Estimated Loss", f"GH₵ {state.total_loss_ghs:,.0f}")
        st.metric("Estimated Recovery", f"{state.recovery_weeks:.0f} weeks")
    
    # Infrastructure at Risk - Chart
    st.markdown("### 🏗️ Infrastructure at Risk")
    
    infra_data = pd.DataFrame({
        'Infrastructure': ['Schools', 'Hospitals', 'Markets', 'Roads', 'Power Substations'],
        'Affected': [
            state.schools_exposed,
            state.hospitals_exposed,
            state.markets_exposed,
            state.roads_affected,
            state.power_substations_affected
        ]
    })
    
    fig = px.bar(
        infra_data,
        x='Infrastructure',
        y='Affected',
        title='Infrastructure at Risk',
        color='Affected',
        color_continuous_scale='RdYlGn_r',
        text='Affected'
    )
    
    fig.update_traces(textposition='outside')
    fig.update_layout(height=300, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    
    # Communities Affected
    st.markdown("### 🏘️ Communities Affected")
    
    communities = ["Alajo", "Kaneshie", "Circle", "Nima", "Mamobi"]
    st.markdown("• " + " • ".join(communities))
    st.caption(f"📊 {len(communities)} communities potentially affected")
