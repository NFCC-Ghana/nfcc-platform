"""Explainability endpoints for model interpretability."""

from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/explain", tags=["Explainability"])


class ExplainRequest(BaseModel):
    """Request model for explainability."""

    location: str
    precipitation: float
    temperature: float = None


@router.post("/")
async def explain_prediction(request: ExplainRequest) -> Dict[str, Any]:
    """Explain a flood risk prediction."""
    # Calculate base score
    rainfall = max(0.0, request.precipitation)

    if rainfall < 10:
        base_score = rainfall * 3
        explanation = "Low rainfall, minimal flood risk"
    elif rainfall < 30:
        base_score = 30 + (rainfall - 10) * 1.5
        explanation = "Moderate rainfall, some flood risk"
    elif rainfall < 60:
        base_score = 60 + (rainfall - 30) * 0.83
        explanation = "Heavy rainfall, significant flood risk"
    else:
        base_score = min(100, 85 + (rainfall - 60) * 0.375)
        explanation = "Extreme rainfall, critical flood risk"

    # Get risk tier
    if base_score < 30:
        tier = "LOW"
    elif base_score < 50:
        tier = "MODERATE"
    elif base_score < 70:
        tier = "HIGH"
    elif base_score < 85:
        tier = "CRITICAL"
    else:
        tier = "EXTREME"

    return {
        "location": request.location,
        "precipitation": rainfall,
        "risk_score": round(base_score, 1),
        "risk_tier": tier,
        "explanation": explanation,
        "factors": {
            "precipitation_contribution": round(base_score, 1),
            "location_factor": "standard",
            "seasonal_factor": "normal",
        },
    }


@router.get("/features")
async def get_feature_importance() -> Dict[str, Any]:
    """Get feature importance for the flood risk model."""
    return {
        "feature_importance": {
            "precipitation": 0.65,
            "roll_3d": 0.15,
            "roll_7d": 0.08,
            "cumulative": 0.07,
            "z_score": 0.05,
        },
        "description": "Feature importance based on XGBoost model training",
    }
