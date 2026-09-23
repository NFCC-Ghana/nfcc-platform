"""Alert formatting utilities."""

from typing import Dict, Any, Optional

from src.config.settings import settings
from src.hydrology.urban_drainage import urban_drainage

# Canonical tier ordering - used to compare a real alert's tier against a
# subscriber's chosen minimum (src/database/channel_subscriptions_db.py),
# so "notify me for HIGH+" doesn't fire on a MODERATE alert.
TIER_RANK: Dict[str, int] = {
    "LOW": 0,
    "MODERATE": 1,
    "HIGH": 2,
    "CRITICAL": 3,
    "EXTREME": 4,
}


def tier_at_least(candidate_tier: str, minimum_tier: str) -> bool:
    """True if candidate_tier is at or above minimum_tier in severity.
    Unknown tier strings rank below everything (never spuriously alert
    on a typo'd/unrecognized tier)."""
    return TIER_RANK.get(candidate_tier, -1) >= TIER_RANK.get(minimum_tier, 0)


def calculate_score(precipitation: float, district: Optional[str] = None) -> float:
    """Convert precipitation (mm) to a 0-100 flood risk score.

    district is optional and, when given, applies a real urban-drainage
    adjustment (src/hydrology/urban_drainage.py, first wired in here
    after being imported-but-never-called since early development) on
    top of the base precipitation curve: a multiplier above 1.0 for a
    district with known poor/blocked drainage (currently real data only
    for Accra Central/West/East - see that module's docstring), and a
    neutral 1.0 (no change at all) for every other district, including
    ones this module has zero real data on.

    Every existing caller that doesn't pass district is completely
    unaffected - deliberately minimal blast radius, since this function
    is also called from historical backtesting/rare-event verification
    (src/models/historical_backtest.py, rare_event_verification.py),
    which need the pure precipitation-only curve to stay comparable
    against real past events.

    Previously also accepted a `temperature` parameter that this
    function silently never read - a real "wired but not connected" bug
    on the live /score endpoint (src/api/main.py's ScoreRequest let a
    caller supply temperature expecting it to affect the score). Removed
    rather than given a real effect: temperature isn't a meaningful
    direct driver of Ghana's rainfall-driven flooding, and inventing a
    formula just to make the parameter "do something" would trade one
    honesty problem for another.
    """
    if precipitation <= 0:
        base = 0.0
    elif precipitation < 10:
        base = min(100, precipitation * 3)
    elif precipitation < 30:
        base = min(100, 30 + (precipitation - 10) * 2)
    elif precipitation < 50:
        base = min(100, 70 + (precipitation - 30) * 1.5)
    else:
        base = min(100, 95 + (precipitation - 50) * 0.2)

    if district and base > 0:
        drainage_factor = urban_drainage.get_flood_risk_factor(district, precipitation)
        base = min(100, base * drainage_factor)

    return base


def get_risk_tier(score: float) -> str:
    """Get risk tier from score. Boundaries come from settings
    (ALERT_THRESHOLD_MODERATE/HIGH/CRITICAL/EXTREME) - found during a
    codebase audit that these were documented in .env.example as
    deployer-configurable since this file's earliest version, but this
    function (and, independently, AlertEngine.THRESHOLDS in
    src/alerts/engine.py) had the same boundaries hardcoded and never
    actually read them. Both now derive from the same settings values so
    the risk TIER a score maps to and the tier AlertEngine gates sending
    on can never silently diverge."""
    if score < settings.ALERT_THRESHOLD_MODERATE:
        return "LOW"
    elif score < settings.ALERT_THRESHOLD_HIGH:
        return "MODERATE"
    elif score < settings.ALERT_THRESHOLD_CRITICAL:
        return "HIGH"
    elif score < settings.ALERT_THRESHOLD_EXTREME:
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
