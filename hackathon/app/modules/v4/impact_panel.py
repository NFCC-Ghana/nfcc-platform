"""
Impact Panel - Lives affected, infrastructure, economic impact
"""

import streamlit as st

def render_impact_panel(district: str, risk_score: float) -> None:
    """Render impact assessment panel."""
    
    st.markdown("### 👥 Impact Assessment")
    st.caption("Lives affected, critical infrastructure, and economic impact")
    
    # Calculate based on risk score
    population = 187928
    pop_exposed = int(population * (risk_score / 100) * 0.6)
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Lives Affected",
            f"{pop_exposed:,}",
            delta=f"{risk_score:.0f}% of population"
        )
    with col2:
        st.metric("Schools at Risk", "23")
    with col3:
        st.metric("Hospitals at Risk", "3")
    with col4:
        st.metric("Markets at Risk", "6")
    
    st.divider()
    
    # Economic impact
    st.markdown("#### 💰 Estimated Economic Impact")
    
    col1, col2 = st.columns(2)
    
    with col1:
        residential_loss = pop_exposed * 15000
        st.metric("Residential Losses", f"GH₵ {residential_loss:,.0f}")
        
        infrastructure_loss = 5000000 if risk_score >= 60 else 1000000
        st.metric("Infrastructure Losses", f"GH₵ {infrastructure_loss:,.0f}")
    
    with col2:
        total_loss = residential_loss + infrastructure_loss
        st.metric("Total Estimated Loss", f"GH₵ {total_loss:,.0f}", delta="High Impact")
        
        recovery_weeks = int((risk_score / 100) * 12) + 2
        st.metric("Estimated Recovery", f"{recovery_weeks} weeks")
    
    # Vulnerable populations
    st.markdown("#### 👶 Vulnerable Populations")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        children = int(pop_exposed * 0.3)
        st.metric("Children (<18)", f"{children:,}")
    with col2:
        elderly = int(pop_exposed * 0.1)
        st.metric("Elderly (>60)", f"{elderly:,}")
    with col3:
        disabled = int(pop_exposed * 0.02)
        st.metric("Persons with Disabilities", f"{disabled:,}")
    
    # Communities affected
    st.markdown("#### 🏘️ Communities Affected")
    
    communities = ["Alajo", "Kaneshie", "Circle", "Nima", "Mamobi"]
    affected = communities if risk_score >= 60 else communities[:2]
    
    for comm in affected:
        st.markdown(f"• {comm}")
    
    st.caption(f"📊 {len(affected)} communities potentially affected")
