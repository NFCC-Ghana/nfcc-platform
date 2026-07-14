"""Impact Assessment Module - Population, schools, hospitals."""

import streamlit as st
import pandas as pd

def render_impact_assessment(district: str, risk_score: float) -> None:
    """Render impact assessment panel."""
    
    st.markdown("### 👥 Impact Assessment")
    
    # Simulate impact data (in production: from NFCC exposure engine)
    impacts = {
        "Population Exposed": int(187928 * (risk_score / 100) * 0.6),
        "Children Under 18": int(187928 * (risk_score / 100) * 0.18),
        "Elderly Over 60": int(187928 * (risk_score / 100) * 0.06),
        "Schools at Risk": int(52 * (risk_score / 100) * 0.5),
        "Hospitals at Risk": int(8 * (risk_score / 100) * 0.5),
        "Markets at Risk": int(15 * (risk_score / 100) * 0.5)
    }
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Population Exposed", f"{impacts['Population Exposed']:,}")
        st.caption(f"Children: {impacts['Children Under 18']:,}")
    
    with col2:
        st.metric("Schools at Risk", impacts['Schools at Risk'])
        st.caption(f"Hospitals: {impacts['Hospitals at Risk']}")
    
    with col3:
        st.metric("Markets at Risk", impacts['Markets at Risk'])
        st.caption(f"Elderly: {impacts['Elderly Over 60']:,}")
    
    # Vulnerability breakdown
    st.markdown("#### Vulnerable Populations")
    
    vuln_data = {
        "Category": ["Children", "Elderly", "Disabled", "Pregnant Women"],
        "Exposed": [
            impacts['Children Under 18'],
            impacts['Elderly Over 60'],
            int(187928 * (risk_score / 100) * 0.02),
            int(187928 * (risk_score / 100) * 0.015)
        ]
    }
    
    vuln_df = pd.DataFrame(vuln_data)
    st.dataframe(vuln_df, use_container_width=True, hide_index=True)
    
    # Overall assessment
    exposure_pct = (impacts['Population Exposed'] / 187928) * 100
    st.info(f"📊 **{exposure_pct:.1f}%** of the district population is potentially affected.")
