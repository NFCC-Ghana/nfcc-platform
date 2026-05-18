"""Alert message formatting."""

from datetime import datetime


def get_risk_tier(risk_score: float) -> str:
    """Convert risk score to tier."""
    if risk_score >= 80:
        return "EXTREME"
    elif risk_score >= 60:
        return "HIGH"
    elif risk_score >= 40:
        return "MODERATE"
    else:
        return "LOW"


def get_instruction(tier: str) -> str:
    """Get action instruction based on risk tier."""
    instructions = {
        "EXTREME": "Immediate evacuation advised. Seek higher ground.",
        "HIGH": "Prepare for flooding. Move valuables to safe areas.",
        "MODERATE": "Stay alert. Monitor water levels.",
        "LOW": "No action needed at this time.",
    }
    return instructions.get(tier, "Monitor local conditions.")


def format_alert(
    location: str,
    risk_score: float,
    risk_tier: str = None,
    timestamp: datetime = None,
    include_instruction: bool = True,
) -> str:
    """Format alert message for sending."""
    if risk_tier is None:
        risk_tier = get_risk_tier(risk_score)
    if timestamp is None:
        timestamp = datetime.now()

    emoji = {"EXTREME": "🔴", "HIGH": "🟠", "MODERATE": "🟡", "LOW": "🟢"}.get(
        risk_tier, "⚠️"
    )

    message = (
        f"{emoji} NFCC FLOOD ALERT {emoji}\n\n"
        f"📍 Location: {location}\n"
        f"📊 Risk Score: {risk_score:.1f} / 100\n"
        f"⚠️ Risk Tier: {risk_tier}\n"
        f"🕐 Time: {timestamp.strftime('%Y-%m-%d %H:%M')} UTC"
    )

    if include_instruction:
        message += f"\n\n{get_instruction(risk_tier)}"

    return message
