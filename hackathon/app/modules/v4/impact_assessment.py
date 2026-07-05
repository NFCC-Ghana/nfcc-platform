"""Impact Assessment module."""

import streamlit as st


def render_impact_assessment(state):
    """Render the impact assessment section."""
    st.markdown("## 👥 Impact Assessment")
    st.caption("Lives affected, critical infrastructure, and economic impact")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Lives Affected", f"{state.population_exposed:,}", f"{state.exposure_percentage:.0f}% of population")
    with col2:
        st.metric("Schools at Risk", state.schools_exposed)
    with col3:
        st.metric("Hospitals at Risk", state.hospitals_exposed)
    with col4:
        st.metric("Markets at Risk", state.markets_exposed)
    
    st.markdown("### 💰 Estimated Economic Impact")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Residential Losses", f"GH₵ {state.residential_loss_ghs:,.0f}")
        st.metric("Infrastructure Losses", f"GH₵ {state.infrastructure_loss_ghs:,.0f}")
    with col2:
        st.metric("Total Estimated Loss", f"GH₵ {state.total_loss_ghs:,.0f}", "High Impact")
        st.metric("Estimated Recovery", f"{state.recovery_weeks:.0f} weeks")
    
    st.markdown("### 👶 Vulnerable Populations")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Children (<18)", f"{state.children_exposed:,}")
    with col2:
        st.metric("Elderly (>60)", f"{state.elderly_exposed:,}")
    with col3:
        st.metric("Persons with Disabilities", f"{state.disabled_exposed:,}")
    
    st.markdown("### 🏘️ Communities Affected")
    st.markdown("• Alajo • Kaneshie • Circle • Nima • Mamobi")
    st.caption("📊 5 communities potentially affected")
