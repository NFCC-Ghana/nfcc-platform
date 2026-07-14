"""Alert formatting utilities."""

from typing import Any, Dict, Optional


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
