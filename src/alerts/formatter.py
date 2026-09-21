"""Alert formatting utilities."""

from typing import Dict, Any, Optional

# Canonical tier ordering - used to compare a real alert's tier against a
# subscriber's chosen minimum (src/database/channel_subscriptions_db.py),
# so "notify me for HIGH+" doesn't fire on a MODERATE alert.
TIER_RANK: Dict[str, int] = {"LOW": 0, "MODERATE": 1, "HIGH": 2, "CRITICAL": 3, "EXTREME": 4}


def tier_at_least(candidate_tier: str, minimum_tier: str) -> bool:
    """True if candidate_tier is at or above minimum_tier in severity.
    Unknown tier strings rank below everything (never spuriously alert
    on a typo'd/unrecognized tier)."""
    return TIER_RANK.get(candidate_tier, -1) >= TIER_RANK.get(minimum_tier, 0)


def calculate_score(precipitation: float, temperature: float = None) -> float:
    """Convert precipitation (mm) to a 0-100 flood risk score."""
    if precipitation <= 0:
        return 0.0
    elif precipitation < 10:
        return min(100, precipitation * 3)
    elif precipitation < 30:
        return min(100, 30 + (precipitation - 10) * 2)
    elif precipitation < 50:
        return min(100, 70 + (precipitation - 30) * 1.5)
    else:
        return min(100, 95 + (precipitation - 50) * 0.2)


def get_risk_tier(score: float) -> str:
    """Get risk tier from score."""
    if score < 30:
        return "LOW"
    elif score < 50:
        return "MODERATE"
    elif score < 70:
        return "HIGH"
    elif score < 85:
        return "CRITICAL"
    else:
        return "EXTREME"


def get_instruction(risk_tier: str) -> str:
    """Get safety instructions based on risk tier."""
    instructions = {
        "LOW": "No immediate action required. Stay informed.",
        "MODERATE": "Monitor local conditions. Stay aware.",
        "HIGH": "Take precautions. Avoid low-lying areas.",
        "CRITICAL": "Prepare for flooding. Follow evacuation orders.",
        "EXTREME": "EMERGENCY! Seek higher ground immediately.",
    }
    return instructions.get(risk_tier, "Stay alert. Monitor conditions.")


def format_alert(
    location: str, score: float, risk_tier: Optional[str] = None
) -> Dict[str, Any]:
    """Format alert for display."""
    if risk_tier is None:
        risk_tier = get_risk_tier(score)

    return {
        "location": location,
        "score": round(score, 1),
        "risk_tier": risk_tier,
        "instruction": get_instruction(risk_tier),
    }
