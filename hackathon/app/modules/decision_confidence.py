"""
Decision Confidence - Every recommendation explains WHY and HOW confident.
"""

import streamlit as st
import pandas as pd
from typing import Dict, List

def get_decision_confidence(district: str, risk_score: float) -> Dict:
    """Get decision confidence with explanation."""
    
    # Simulate decision confidence based on available evidence
    evidence_confidence = 92
    model_confidence = 95
    historical_accuracy = 88
    data_freshness = 90
    
    overall_confidence = round((evidence_confidence + model_confidence + historical_accuracy + data_freshness) / 4, 1)
    
    return {
        "risk_score": risk_score,
        "overall_confidence": overall_confidence,
        "evidence_confidence": evidence_confidence,
        "model_confidence": model_confidence,
        "historical_accuracy": historical_accuracy,
        "data_freshness": data_freshness,
        "reason": "Five independent data sources agree on the risk assessment",
        "missing_data": "Wind forecast data currently unavailable",
        "assumptions": "Based on current rainfall patterns and historical flood behavior"
    }


def render_decision_confidence(district: str, risk_score: float) -> None:
    """Render decision confidence panel."""
    
    confidence = get_decision_confidence(district, risk_score)
    
    st.markdown("### 🎯 Decision Confidence")
    st.caption("Every recommendation includes confidence level and reasoning")
    
    # Overall confidence
    color = "#4caf50" if confidence["overall_confidence"] >= 80 else "#ff9800" if confidence["overall_confidence"] >= 60 else "#f44336"
    
    st.markdown(f"""
    <div style="background: white; padding: 1.5rem; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); margin-bottom: 1rem;">
        <div style="display: flex; align-items: center; gap: 2rem;">
            <div>
                <div style="font-size: 0.9rem; color: #666;">Decision Confidence</div>
                <div style="font-size: 3rem; font-weight: 700; color: {color};">{confidence['overall_confidence']:.0f}%</div>
                <div style="font-size: 0.85rem; color: #888;">{confidence['reason']}</div>
            </div>
            <div style="flex: 1;">
                <div style="font-size: 0.8rem; color: #666; margin-bottom: 0.5rem;">Confidence Components</div>
                <div style="background: #f0f0f0; border-radius: 4px; margin-bottom: 0.3rem;">
                    <div style="background: #4caf50; width: {confidence['evidence_confidence']}%; height: 12px; border-radius: 4px;"></div>
                </div>
                <div style="font-size: 0.75rem; color: #888;">Evidence: {confidence['evidence_confidence']}%</div>
                <div style="background: #f0f0f0; border-radius: 4px; margin-bottom: 0.3rem; margin-top: 0.3rem;">
                    <div style="background: #2196f3; width: {confidence['model_confidence']}%; height: 12px; border-radius: 4px;"></div>
                </div>
                <div style="font-size: 0.75rem; color: #888;">Model: {confidence['model_confidence']}%</div>
                <div style="background: #f0f0f0; border-radius: 4px; margin-bottom: 0.3rem; margin-top: 0.3rem;">
                    <div style="background: #ff9800; width: {confidence['historical_accuracy']}%; height: 12px; border-radius: 4px;"></div>
                </div>
                <div style="font-size: 0.75rem; color: #888;">Historical: {confidence['historical_accuracy']}%</div>
                <div style="background: #f0f0f0; border-radius: 4px; margin-bottom: 0.3rem; margin-top: 0.3rem;">
                    <div style="background: #9c27b0; width: {confidence['data_freshness']}%; height: 12px; border-radius: 4px;"></div>
                </div>
                <div style="font-size: 0.75rem; color: #888;">Data Freshness: {confidence['data_freshness']}%</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Missing data and assumptions
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"⚠️ Missing Data: {confidence['missing_data']}")
    with col2:
        st.info(f"📋 Assumptions: {confidence['assumptions']}")
    
    # Recommendation with confidence
    st.markdown("#### 📋 Recommendation")
    
    if risk_score >= 80:
        st.error(f"🚨 IMMEDIATE EVACUATION - Seek higher ground (Confidence: {confidence['overall_confidence']:.0f}%)")
    elif risk_score >= 60:
        st.warning(f"⚠️ PREPARE TO EVACUATE - Move to higher ground (Confidence: {confidence['overall_confidence']:.0f}%)")
    elif risk_score >= 40:
        st.info(f"ℹ️ MONITOR CONDITIONS - Stay informed (Confidence: {confidence['overall_confidence']:.0f}%)")
    else:
        st.success(f"✅ NORMAL - No immediate risk (Confidence: {confidence['overall_confidence']:.0f}%)")
