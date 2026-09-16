"""
CivicFlood AI - Situation Brief
Provides a concise summary of the current flood situation.
"""

from datetime import datetime

from hackathon.app.modules.v4.state import tier_from_score


def generate_situation_brief(state) -> dict:
    """Generate a situation brief from the current state."""
    brief = {
        "timestamp": datetime.now().isoformat(),
        "risk_level": state.risk_category,
        "risk_score": state.risk_score,
        "summary": "",
        "key_actions": [],
        "affected_areas": (
            state.affected_communities[:5] if state.affected_communities else []
        ),
    }

    # Keyed off the real tier (matches state.risk_category /
    # src/alerts/formatter.py:get_risk_tier) instead of a separately
    # drifted 4-tier scale (80/60/40, no EXTREME).
    tier = tier_from_score(state.risk_score)

    if tier in ("EXTREME", "CRITICAL"):
        brief["summary"] = (
            f"{tier}: Immediate evacuation required. "
            "Multiple risk factors are at extreme levels."
        )
        brief["key_actions"] = [
            "Issue mandatory evacuation order",
            "Activate all emergency services",
            "Open all shelters",
            "Deploy rescue teams",
        ]
    elif tier == "HIGH":
        brief["summary"] = (
            "HIGH: Prepare for evacuation. " "Conditions are deteriorating rapidly."
        )
        brief["key_actions"] = [
            "Prepare evacuation routes",
            "Alert communities",
            "Position resources",
            "Monitor river levels",
        ]
    elif tier == "MODERATE":
        brief["summary"] = (
            "MODERATE: Monitor conditions closely. " "Risk is elevated but manageable."
        )
        brief["key_actions"] = [
            "Continue monitoring",
            "Update community alerts",
            "Prepare resources",
            "Review evacuation plans",
        ]
    else:
        brief["summary"] = "LOW: Normal monitoring. " "No immediate action required."
        brief["key_actions"] = [
            "Routine monitoring",
            "Maintain situational awareness",
            "Update weather forecasts",
            "Regular reporting",
        ]

    return brief
