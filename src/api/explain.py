"""Explainability endpoint for the real, live risk score.

Previously hand-rolled its own second copy of the precipitation-to-score
curve and tier boundaries (different breakpoints/multipliers than
src/alerts/formatter.py's calculate_score()/get_risk_tier() - the ones
every other endpoint actually scores with), so this endpoint could
"explain" a score that /situation or /score would never actually
produce for the same input. Found during a codebase-wide audit for
exactly the drift this file's own history (see git log) had already
fixed once for get_risk_tier() reading from settings instead of a
second hardcoded 30/50/70/85. Now calls the same canonical function
everything else does - there is exactly one place this platform
computes a risk score, not two."""

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any

from src.alerts.formatter import calculate_score, get_risk_tier

# Ghana's real rainy-season months (same list already used for the
# Sentinel-1 simulated-detection fallback's seasonal likelihood in
# src/hydrology/sentinel_processor.py) - used below for an honestly
# computed seasonal_factor instead of a flat "normal" regardless of date.
_GHANA_RAINY_SEASON_MONTHS = {5, 6, 7, 9, 10}

router = APIRouter(prefix="/explain", tags=["Explainability"])


class ExplainRequest(BaseModel):
    """Request model for explainability."""

    location: str
    precipitation: float


@router.post("/")
async def explain_prediction(request: ExplainRequest) -> Dict[str, Any]:
    """Explain the real risk score for (location, precipitation) - the
    exact number /situation and /score would also compute, not a
    separate approximation of it. district is deliberately not passed
    to calculate_score() here (no urban-drainage adjustment) - this
    endpoint takes only location/precipitation, unlike /situation's
    fuller request model, so it explains the plain precipitation curve
    a caller with just those two fields would expect."""
    rainfall = max(0.0, request.precipitation)
    score = calculate_score(rainfall)
    tier = get_risk_tier(score)

    if rainfall < 10:
        explanation = "Low rainfall, minimal flood risk"
    elif rainfall < 30:
        explanation = "Moderate rainfall, some flood risk"
    elif rainfall < 50:
        explanation = "Heavy rainfall, significant flood risk"
    else:
        explanation = "Extreme rainfall, critical flood risk"

    # Real, from the current calendar month against Ghana's actual rainy
    # season - this used to be a flat "normal" regardless of when the
    # request was made. location_factor was dropped rather than left as a
    # fake "standard" for every input: this endpoint deliberately doesn't
    # take a district (see this function's docstring), so there is no real
    # per-location adjustment to report here - src/hydrology/urban_
    # drainage.py's real per-district factor only applies via /situation.
    seasonal_factor = (
        "rainy season" if datetime.now().month in _GHANA_RAINY_SEASON_MONTHS else "dry season"
    )

    return {
        "location": request.location,
        "precipitation": rainfall,
        "risk_score": round(score, 1),
        "risk_tier": tier,
        "explanation": explanation,
        "factors": {
            "precipitation_contribution": round(score, 1),
            "seasonal_factor": seasonal_factor,
        },
    }


@router.get("/features")
async def get_feature_importance() -> Dict[str, Any]:
    """Honestly describes how the real score is computed - there is no
    trained model to report feature importance for. A real XGBoost
    model was built and backtested against real historical flood events
    this session (src/models/historical_backtest.py) and found to show
    no reliable improvement over the rule-based calculate_score() it was
    compared against, so it was removed rather than kept for its own
    sake; this endpoint used to still claim its now-deleted feature
    importances as if that model were live."""
    return {
        "method": "rule-based",
        "description": (
            "Risk score is a deterministic piecewise-linear function of "
            "precipitation (src/alerts/formatter.py:calculate_score), "
            "optionally adjusted by a real urban-drainage factor for "
            "districts with known drainage data. No trained ML model is "
            "in production - one was built and backtested against real "
            "historical flood events and did not reliably outperform "
            "this rule-based curve (see src/models/historical_backtest.py)."
        ),
        "inputs": [
            "precipitation_mm",
            "district (optional, urban-drainage adjustment only)",
        ],
    }
