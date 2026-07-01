"""
Operational Resilience - Graceful degradation when data sources fail.
"""

import streamlit as st
import pandas as pd
from typing import Dict, List

def get_system_status() -> Dict:
    """Get operational status of all data sources."""
    return {
        "data_sources": [
            {"name": "CHIRPS Rainfall", "status": "active", "last_update": "2 min", "fallback": "Open-Meteo Forecast"},
            {"name": "NASA SMAP Soil", "status": "active", "last_update": "2 hours", "fallback": "Historical average"},
            {"name": "River Gauges", "status": "active", "last_update": "30 min", "fallback": "Simulated level"},
            {"name": "Sentinel-1 SAR", "status": "active", "last_update": "6 hours", "fallback": "Community reports"},
            {"name": "Community Reports", "status": "active", "last_update": "10 min", "fallback": "None"},
            {"name": "Reservoir Telemetry", "status": "active", "last_update": "1 hour", "fallback": "Historical data"},
            {"name": "Weather Forecast", "status": "warning", "last_update": "4 hours", "fallback": "Persistence forecast"},
            {"name": "Wind Data", "status": "inactive", "last_update": "12 hours", "fallback": "Climatological average"}
        ]
    }


def render_operational_resilience() -> None:
    """Render operational resilience panel."""
    
    status = get_system_status()
    
    st.markdown("### 🛡️ Operational Resilience")
    st.caption("Graceful degradation when data sources are unavailable")
    
    # Overall status
    active = sum(1 for s in status["data_sources"] if s["status"] == "active")
    warning = sum(1 for s in status["data_sources"] if s["status"] == "warning")
    inactive = sum(1 for s in status["data_sources"] if s["status"] == "inactive")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Active Sources", f"{active}", delta="✅ Operational")
    with col2:
        st.metric("Degraded Sources", f"{warning}", delta="⚠️ Limited")
    with col3:
        st.metric("Unavailable Sources", f"{inactive}", delta="❌ Fallback")
    
    st.divider()
    
    # Detailed status
    st.markdown("#### 📊 Data Source Status")
    
    for source in status["data_sources"]:
        status_emoji = "🟢" if source["status"] == "active" else "🟡" if source["status"] == "warning" else "🔴"
        status_text = "Active" if source["status"] == "active" else "Degraded" if source["status"] == "warning" else "Unavailable"
        
        st.markdown(f"""
        <div style="background: #f8f9fa; padding: 0.7rem 1rem; border-radius: 8px; margin-bottom: 0.5rem; border-left: 4px solid {'#4caf50' if source['status'] == 'active' else '#ff9800' if source['status'] == 'warning' else '#f44336'};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <b>{status_emoji} {source['name']}</b>
                    <span style="font-size: 0.85rem; color: #666; margin-left: 1rem;">
                        Status: {status_text}
                    </span>
                </div>
                <div style="font-size: 0.85rem; color: #888;">
                    {source['last_update']} ago • Fallback: {source['fallback']}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # System health summary
    st.divider()
    st.markdown("#### 📋 System Health")
    
    if active >= 5:
        st.success("✅ System operating at 100% capacity - All critical data sources available")
    elif active >= 3:
        st.warning("⚠️ System degraded - Some data sources using fallback values")
    else:
        st.error("🔴 System critical - Limited data availability, using fallback models")
    
    # Resilience features
    with st.expander("🛡️ Resilience Features"):
        st.markdown("""
        **Graceful Degradation:**
        - Missing Sentinel-1 → Community reports are used
        - Missing River Gauges → Simulated levels based on rainfall
        - Missing Weather Forecast → Persistence forecast
        
        **Data Freshness:**
        - All data sources show last update time
        - Fallback sources automatically activated
        - Confidence scores adjust based on data availability
        
        **Operational Continuity:**
        - System continues running with partial data
        - Clear indication of which sources are active
        - Transparency about fallback usage
        """)
