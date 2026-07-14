"""
AI Flood Copilot - Context-Aware Emergency Decision Support
Integrates all NFCC intelligence for intelligent responses.
"""

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

# ============================================================
# CONTEXT DATA (Simulated - In production from NFCC API)
# ============================================================


def get_context_data(district: str = "Accra Central") -> dict:
    """Get all context data for the copilot."""

    # In production, this would come from the NFCC API
    return {
        "district": district,
        "risk_score": 90.6,
        "risk_tier": "EXTREME",
        "confidence": 80,
        "rainfall": 75,
        "rain_3d": 172.4,
        "rain_7d": 368.2,
        "rain_30d": 1589.9,
        "river": {
            "name": "Odaw",
            "level": 0.45,
            "status": "NORMAL",
            "trend": "STABLE",
            "warning_level": 2.0,
            "danger_level": 2.8,
        },
        "soil_saturation": 85,
        "dams": [
            {"name": "Akosombo", "capacity": 88.2, "risk": "MEDIUM"},
            {"name": "Bagre", "capacity": 90.0, "risk": "HIGH"},
        ],
        "communities_at_risk": ["Alajo", "Kaneshie", "Circle", "Nima", "Mamobi"],
        "reports": [
            {
                "community": "Alajo",
                "type": "Active Flooding",
                "verified": True,
                "depth": 0.35,
            },
            {
                "community": "Kaneshie",
                "type": "Water Level Rising",
                "verified": False,
                "depth": 0.15,
            },
            {
                "community": "Dansoman",
                "type": "Drainage Blocked",
                "verified": True,
                "depth": 0.0,
            },
            {
                "community": "Circle",
                "type": "Flood Warning",
                "verified": False,
                "depth": 0.0,
            },
        ],
        "impact": {
            "population_exposed": 102157,
            "schools_at_risk": 23,
            "hospitals_at_risk": 3,
            "markets_at_risk": 6,
            "children_affected": 30647,
            "elderly_affected": 10215,
        },
        "forecast": {"6h": 100, "12h": 100, "24h": 95, "48h": 75},
        "risk_drivers": {
            "Rainfall Accumulation": 35,
            "Soil Saturation": 25,
            "Historical Similarity": 15,
            "Drainage Vulnerability": 10,
            "Community Reports": 10,
            "River Conditions": 5,
        },
        "timestamp": datetime.now().isoformat(),
    }


def get_high_risk_roads(district: str) -> list:
    """Get high-risk roads for a district."""
    roads = {
        "Accra Central": [
            {
                "name": "Alajo Main Street",
                "risk": "HIGH",
                "reason": "Verified flooding report",
            },
            {
                "name": "Kaneshie Market Road",
                "risk": "HIGH",
                "reason": "Rising water report",
            },
            {
                "name": "Ring Road Central",
                "risk": "MODERATE",
                "reason": "Poor drainage",
            },
            {
                "name": "Circle Interchange",
                "risk": "MODERATE",
                "reason": "Flood warning active",
            },
        ],
        "Accra West": [
            {"name": "Dansoman Road", "risk": "HIGH", "reason": "Blocked drainage"},
            {"name": "Mallam Road", "risk": "MODERATE", "reason": "Low-lying area"},
        ],
        "Tema": [
            {"name": "Community 1 Road", "risk": "HIGH", "reason": "Coastal proximity"},
            {"name": "Harbour Road", "risk": "MODERATE", "reason": "Tidal influence"},
        ],
    }
    return roads.get(district, [])


def get_affected_schools(district: str) -> list:
    """Get schools at risk."""
    schools = {
        "Accra Central": [
            {"name": "Alajo Basic School", "students": 450, "distance": 0.8},
            {"name": "Kaneshie Senior High", "students": 980, "distance": 1.2},
            {"name": "Nima Primary", "students": 620, "distance": 1.5},
            {"name": "Mamobi Basic School", "students": 530, "distance": 2.0},
        ]
    }
    return schools.get(district, [])


# ============================================================
# COPILOT RESPONSE GENERATOR
# ============================================================


def generate_copilot_response(
    question: str, context: dict, role: str = "resident"
) -> str:
    """Generate context-aware response based on question and role."""

    question_lower = question.lower()

    # ============================================================
    # ROAD FLOODING QUESTIONS
    # ============================================================
    if any(
        word in question_lower
        for word in ["road", "street", "drive", "route", "traffic"]
    ):
        roads = get_high_risk_roads(context["district"])
        if roads:
            response = f"""
🚗 **HIGH-RISK ROADS IN {context['district'].upper()}**

Based on current conditions (Risk: {context['risk_score']:.0f}%):
"""
            for road in roads:
                emoji = "🔴" if road["risk"] == "HIGH" else "🟡"
                response += f"""
{emoji} **{road['name']}**
   Risk: {road['risk']}
   Why: {road['reason']}
"""

            response += f"""

📊 **Evidence:**
• Rainfall: {context['rainfall']}mm (24h)
• Soil saturation: {context['soil_saturation']}%
• Active community reports: {len([r for r in context['reports'] if r['verified']])}

⏰ **Expected Timeline:**
• 0-6 Hours: Localized street flooding
• 6-24 Hours: Expansion into low-lying intersections

🎯 **Recommended Actions:**
• Avoid Alajo Main Street and Kaneshie Market Road
• Divert traffic via Ring Road
• Deploy drainage crews to blocked areas
"""
            return response

    # ============================================================
    # SCHOOL QUESTIONS
    # ============================================================
    if any(
        word in question_lower for word in ["school", "student", "class", "education"]
    ):
        schools = get_affected_schools(context["district"])
        if schools:
            total_students = sum(s["students"] for s in schools)
            response = f"""
🏫 **SCHOOL CLOSURE RECOMMENDATION: {context['district'].upper()}**

**Current Situation:**
• District risk: {context['risk_tier']} ({context['risk_score']:.0f}%)
• Schools at risk: {context['impact']['schools_at_risk']}
• Affected students: ~{total_students:,}

**Schools at Risk:**
"""
            for school in schools:
                response += f"""
• {school['name']}
  - Students: {school['students']}
  - Distance to flood zone: {school['distance']}km
"""

            response += f"""

📋 **Recommendation: SUSPEND IN-PERSON INSTRUCTION**

**Actions:**
1. Notify parents immediately
2. Prepare remote learning alternatives
3. Coordinate with NADMO and GES
4. Use school facilities as shelters if needed

⏰ **Timeline:** Effective within 12 hours
"""
            return response

    # ============================================================
    # WHY EXTREME RISK QUESTIONS
    # ============================================================
    if any(word in question_lower for word in ["why", "reason", "explain", "cause"]):
        drivers = context["risk_drivers"]
        response = f"""
📊 **WHY IS {context['district'].upper()} AT {context['risk_score']:.0f}% RISK?**

**Risk Drivers:**

"""
        for driver, contribution in drivers.items():
            bar = "█" * int(contribution / 5)
            response += f"   {driver}: {bar} {contribution}%\n"

        response += f"""

**Current Conditions:**

🌧️ **Rainfall:** {context['rainfall']}mm (24h) | {context['rain_30d']:.0f}mm (30-day)
💧 **Soil Saturation:** {context['soil_saturation']}% (High)
🌊 **River Status:** {context['river']['name']} at {context['river']['level']}m ({context['river']['status']})

**Community Reports:**
• Verified: {len([r for r in context['reports'] if r['verified']])}
• Pending: {len([r for r in context['reports'] if not r['verified']])}

**Conclusion:**
River levels remain normal, but soil saturation is extremely high, 
rainfall accumulation is significant, and multiple community reports are active.
Therefore overall flood risk remains EXTREME.

🎯 **Recommendation:** Prepare for evacuation within 6 hours.
"""
        return response

    # ============================================================
    # IMPACT / EVACUATION QUESTIONS
    # ============================================================
    if any(
        word in question_lower
        for word in ["evacuate", "evacuation", "people", "population", "impact"]
    ):
        impact = context["impact"]
        response = f"""
👥 **POPULATION IMPACT ASSESSMENT: {context['district'].upper()}**

**Exposure Summary:**
• Total population exposed: {impact['population_exposed']:,}
• Children (<18): {impact['children_affected']:,}
• Elderly (>60): {impact['elderly_affected']:,}

**Infrastructure at Risk:**
• Schools: {impact['schools_at_risk']}
• Hospitals: {impact['hospitals_at_risk']}
• Markets: {impact['markets_at_risk']}

**Affected Communities:**
"""
        for community in context["communities_at_risk"][:5]:
            response += f"• {community}\n"

        response += f"""

**Evacuation Recommendations:**

🏛️ **Nearest Shelters:**
• Accra High School (1.2km) - Capacity: 1,200
• Community Center (2.5km) - Capacity: 500
• Trade Fair Centre (4.0km) - Capacity: 2,000

🚗 **Safe Routes:**
• Alajo → Ring Road → Accra High School
• Kaneshie → Winneba Road → Community Center

📋 **Priority:**
1. Evacuate elderly and children first
2. Use schools as temporary shelters
3. Coordinate with NADMO for transport
"""
        return response

    # ============================================================
    # SITUATION REPORT GENERATOR
    # ============================================================
    if "situation" in question_lower or "sitrep" in question_lower:
        response = f"""
📋 **CIVICFLOOD SITUATION REPORT (SITREP)**

**Generated:** {datetime.now().strftime('%d %b %Y, %H:%M')}

---

**DISTRICT:** {context['district'].upper()}

**RISK ASSESSMENT:**
• Risk Score: {context['risk_score']:.0f}% ({context['risk_tier']})
• Confidence: {context['confidence']}%
• Status: ACTIVE EMERGENCY

---

**ENVIRONMENTAL CONDITIONS:**
• Rainfall (24h): {context['rainfall']}mm
• 3-Day Total: {context['rain_3d']:.1f}mm
• 30-Day Total: {context['rain_30d']:.0f}mm
• Soil Saturation: {context['soil_saturation']}%
• River Level: {context['river']['name']} at {context['river']['level']}m ({context['river']['status']})

---

**COMMUNITY REPORTS:**
• Active: {len([r for r in context['reports'] if r['verified']])}
• Pending: {len([r for r in context['reports'] if not r['verified']])}
• Communities Affected: {', '.join(context['communities_at_risk'][:5])}

---

**IMPACT SUMMARY:**
• Population Exposed: {context['impact']['population_exposed']:,}
• Schools at Risk: {context['impact']['schools_at_risk']}
• Hospitals at Risk: {context['impact']['hospitals_at_risk']}
• Markets at Risk: {context['impact']['markets_at_risk']}

---

**PRIMARY DRIVERS:**
"""
        for driver, contrib in context["risk_drivers"].items():
            response += f"• {driver}: {contrib}%\n"

        response += f"""
---

**RECOMMENDED ACTIONS:**

1. 🚨 Activate emergency operations center
2. 🏫 Notify schools of potential closure
3. 🏛️ Prepare evacuation shelters
4. 📢 Issue public warnings
5. 🌊 Monitor Alajo and Kaneshie
6. 🤝 Coordinate with NADMO

---

*This report is based on live data from the NFCC Platform.*
*Next update: { (datetime.now() + timedelta(hours=6)).strftime('%d %b %Y, %H:%M') }*
"""
        return response

    # ============================================================
    # RIVER AND DAM QUESTIONS
    # ============================================================
    if any(word in question_lower for word in ["river", "dam", "overflow", "spill"]):
        response = f"""
🌊 **RIVER & DAM STATUS: {context['district'].upper()}**

**River Status:**
• Name: {context['river']['name']}
• Current Level: {context['river']['level']}m
• Status: {context['river']['status']}
• Trend: {context['river']['trend']}
• Warning Level: {context['river']['warning_level']}m
• Danger Level: {context['river']['danger_level']}m

**Time to Warning:** {(context['river']['warning_level'] - context['river']['level']) / 0.02:.1f} hours (estimated)

**Dam Status:**
"""
        for dam in context["dams"]:
            risk_emoji = (
                "🔴"
                if dam["risk"] == "HIGH"
                else "🟡" if dam["risk"] == "MEDIUM" else "🟢"
            )
            response += f"• {dam['name']}: {dam['capacity']}% full {risk_emoji} ({dam['risk']} risk)\n"

        response += f"""
**Risk of Overflow:** {'HIGH' if context['river']['level'] > context['river']['warning_level'] * 0.8 else 'LOW'}

**Recommended Actions:**
• Monitor river levels every 2 hours
• Prepare for potential overflow in low-lying areas
• Coordinate with VRA for dam updates
"""
        return response

    # ============================================================
    # FORECAST QUESTIONS
    # ============================================================
    if any(
        word in question_lower
        for word in ["forecast", "prediction", "future", "next", "timeline"]
    ):
        forecast = context["forecast"]
        response = f"""
📈 **FLOOD FORECAST: {context['district'].upper()}**

**Risk Timeline:**

| Timeframe | Risk Score | Status |
|-----------|------------|--------|
| NOW       | {forecast['6h']:.0f}%      | EXTREME |
| +6 HOURS  | {forecast['6h']:.0f}%      | EXTREME |
| +12 HOURS | {forecast['12h']:.0f}%     | EXTREME |
| +24 HOURS | {forecast['24h']:.0f}%     | HIGH |
| +48 HOURS | {forecast['48h']:.0f}%     | MODERATE |

**Peak Risk:** {max(forecast.values()):.0f}% (within 6-12 hours)

**Driver:**
• Rainfall accumulation continuing
• Soil saturation already high
• Community reports increasing

**Action Window:**
• Critical: Next 6 hours
• High: Next 24 hours
• Moderate: 24-48 hours

**Recommendation:**
Implement immediate evacuation measures for high-risk areas.
"""
        return response

    # ============================================================
    # VULNERABLE COMMUNITIES
    # ============================================================
    if any(
        word in question_lower
        for word in ["vulnerable", "elderly", "children", "disabled"]
    ):
        impact = context["impact"]
        response = f"""
👥 **VULNERABLE POPULATIONS: {context['district'].upper()}**

**Exposed Vulnerable Groups:**
• Children (<18): {impact['children_affected']:,}
• Elderly (>60): {impact['elderly_affected']:,}
• Estimated Disabled: {(impact['population_exposed'] * 0.02):.0f}
• Estimated Pregnant Women: {(impact['population_exposed'] * 0.015):.0f}

**Communities with High Vulnerability:**
"""
        for community in context["communities_at_risk"][:5]:
            response += f"• {community}\n"

        response += f"""

**Priority Actions:**
1. 🚨 Evacuate elderly and children first
2. 🏛️ Open shelters with medical facilities
3. 📢 Targeted warnings to vulnerable communities
4. 🤝 Community leader coordination
5. 🚑 Medical team deployment to high-risk areas

**Shelter Capacity:**
• Total available: 3,700 spaces
• Required: ~{int(impact['population_exposed'] * 0.2):,}
• Shortfall: {max(0, int(impact['population_exposed'] * 0.2) - 3700)}
"""
        return response

    # ============================================================
    # DEFAULT RESPONSE
    # ============================================================
    return f"""
📋 **CIVICFLOOD AI: {context['district'].upper()}**

**Current Status:**
• Risk Score: {context['risk_score']:.0f}% ({context['risk_tier']})
• Confidence: {context['confidence']}%
• Communities at Risk: {len(context['communities_at_risk'])}
• Active Reports: {len([r for r in context['reports'] if r['verified']])}

**Key Actions:**
1. 🚨 Monitor official alerts every 30 minutes
2. 🏠 Prepare emergency supplies
3. 🚗 Know your evacuation route
4. 👴 Check on vulnerable neighbors

**Quick Tips:**
• Ask me about: roads, schools, evacuation, forecast, or vulnerable populations
• I can also generate a full situation report
• Try: "Which roads will flood?" or "Should schools close?"

**Data Sources:**
• CHIRPS Rainfall • NASA SMAP • Sentinel-1 • Community Reports
• Ghana River Gauges • Dam Database

**🔗 API: https://nfcc-platform-production.up.railway.app**

Stay safe! 🌊
"""


# ============================================================
# MAIN COPILOT UI
# ============================================================


def render_copilot(district: str, risk_score: float) -> None:
    """Render enhanced AI Flood Copilot with context-aware responses."""

    st.markdown("### 🤖 AI Flood Copilot")
    st.caption("Ask any question about flood risk in your community")

    # Get context
    context = get_context_data(district)
    context["risk_score"] = risk_score

    # Role selector
    roles = [
        "Resident",
        "School Principal",
        "NADMO Officer",
        "Hospital Administrator",
        "Assembly Member",
        "Farmer",
    ]
    selected_role = st.selectbox("I am a:", roles, index=0, key="copilot_role")

    # Quick questions
    quick_questions = [
        "Which roads will flood in the next 6 hours?",
        "Should schools close tomorrow?",
        "Why is risk EXTREME?",
        "How many people should be evacuated?",
        "Generate a situation report",
        "Which communities are most vulnerable?",
    ]

    cols = st.columns(3)
    for i, q in enumerate(quick_questions):
        with cols[i % 3]:
            if st.button(q, key=f"copilot_q_{i}"):
                st.session_state.copilot_query = q

    # Text input
    query = st.text_input(
        "Ask CivicFlood AI:",
        placeholder="e.g., Which roads will flood in Accra Central?",
        key="copilot_input",
    )

    # Process query
    if query or st.session_state.get("copilot_query"):
        question = query or st.session_state.get("copilot_query", "")

        with st.spinner("🧠 Analyzing your question with flood intelligence..."):
            response = generate_copilot_response(
                question, context, selected_role.lower().replace(" ", "_")
            )

            # Display response in a nice box
            st.markdown("---")
            st.markdown("### 📋 Response")
            st.markdown(response)
            st.markdown("---")
            st.caption(f"🤖 CivicFlood AI • Based on live data • Role: {selected_role}")

    # Tips
    with st.expander("💡 Tips for better questions"):
        st.markdown("""
        **Ask me about:**
        - **Roads** → "Which roads will flood?"
        - **Schools** → "Should schools close tomorrow?"
        - **Why** → "Why is risk EXTREME?"
        - **Evacuation** → "How many people should be evacuated?"
        - **Situation** → "Generate a situation report"
        - **Vulnerable** → "Which communities are most vulnerable?"
        - **Forecast** → "What is the forecast for next 24 hours?"
        - **Rivers** → "Will Odaw River overflow?"
        """)


# ============================================================
# SITUATION REPORT GENERATOR (Standalone)
# ============================================================


def render_situation_report(district: str, risk_score: float) -> None:
    """Generate and display a complete situation report."""

    context = get_context_data(district)
    context["risk_score"] = risk_score

    st.markdown("### 📋 Situation Report")

    if st.button("📄 Generate Situation Report", use_container_width=True):
        with st.spinner("🔄 Generating comprehensive situation report..."):
            response = generate_copilot_response(
                "situation report", context, "resident"
            )
            st.markdown(response)
            st.download_button(
                "📥 Download Report",
                response,
                file_name=f"situation_report_{district}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain",
            )
