"""Alert formatting utilities."""

from datetime import datetime
from typing import Optional


def get_risk_tier(score: float) -> str:
    """
    Get risk tier from score.

    Args:
        score: Risk score (0-100)

    Returns:
        Risk tier string (LOW, MODERATE, HIGH, EXTREME)
    """
    if score >= 80:
        return "EXTREME"
    if score >= 60:
        return "HIGH"
    if score >= 40:
        return "MODERATE"
    return "LOW"


def get_instruction(tier: str) -> str:
    """
    Get instruction based on risk tier.

    Args:
        tier: Risk tier

    Returns:
        Action instruction
    """
    instructions = {
        "EXTREME": "IMMEDIATE EVACUATION REQUIRED. Move to higher ground now.",
        "HIGH": "Prepare for flooding. Move valuables to higher ground.",
        "MODERATE": "Stay alert. Monitor water levels and weather updates.",
        "LOW": "No immediate action needed. Continue normal monitoring.",
    }
    return instructions.get(tier, "Monitor local conditions for updates.")


def format_alert(
    location: str,
    risk_score: float,
    risk_tier: Optional[str] = None,
    timestamp: Optional[datetime] = None,
    include_instruction: bool = True,
) -> str:
    """
    Format alert message.

    Args:
        location: Location name
        risk_score: Risk score (0-100)
        risk_tier: Risk tier (auto-inferred if not provided)
        timestamp: Alert timestamp (defaults to now)
        include_instruction: Whether to include action instruction

    Returns:
        Formatted alert string
    """
    if risk_tier is None:
        risk_tier = get_risk_tier(risk_score)

    if timestamp is None:
        timestamp = datetime.now()

    emoji_map = {
        "EXTREME": "🔴🔥",
        "HIGH": "🟠",
        "MODERATE": "🟡",
        "LOW": "🟢",
    }
    emoji = emoji_map.get(risk_tier, "⚠️")

    lines = [
        "=" * 60,
        f"{emoji} NFCC FLOOD ALERT {emoji}",
        "=" * 60,
        f"Location    : {location}",
        f"Risk Score  : {risk_score:.1f} / 100",
        f"Risk Tier   : {risk_tier}",
        f"Time        : {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
    ]

    if include_instruction:
        lines.append("-" * 60)
        lines.append(f"INSTRUCTION : {get_instruction(risk_tier)}")

    lines.append("=" * 60)

    return "\n".join(lines)
