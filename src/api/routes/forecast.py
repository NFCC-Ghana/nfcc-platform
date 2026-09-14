"""Forecast fusion HTTP routes (separate from /score)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.models.confidence_scoring import forecast_confidence
from src.models.forecast_fusion import ForecastFusionInput, fuse_forecasts

router = APIRouter(prefix="/forecast", tags=["Forecast"])


class ForecastConfidenceRequest(BaseModel):
    """Normalized 0–100 risks per source; omit or null when unavailable."""

    location: str = Field(..., description="District or place label")
    chirps_risk: Optional[float] = Field(None, ge=0.0, le=100.0)
    glofas_risk: Optional[float] = Field(None, ge=0.0, le=100.0)
    flood_hub_risk: Optional[float] = Field(None, ge=0.0, le=100.0)


@router.post("/confidence")
async def forecast_confidence_endpoint(
    body: ForecastConfidenceRequest,
) -> Dict[str, Any]:
    """Fuse CHIRPS + GloFAS + Flood Hub style inputs into unified risk and confidence."""
    inp = ForecastFusionInput(
        chirps_risk=body.chirps_risk,
        glofas_risk=body.glofas_risk,
        flood_hub_risk=body.flood_hub_risk,
    )
    fusion = fuse_forecasts(inp)
    conf = forecast_confidence(inp, fusion.unified_risk)

    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "status": "success",
        "location": body.location,
        "timestamp": ts,
        "unified_risk": round(fusion.unified_risk, 2),
        "confidence": round(conf.confidence, 2),
        "confidence_breakdown": {
            "coverage_factor": round(conf.coverage_factor, 2),
            "agreement_factor": round(conf.agreement_factor, 2),
            "num_sources": conf.num_sources,
        },
        "sources": {
            "chirps_risk": body.chirps_risk,
            "glofas_risk": body.glofas_risk,
            "flood_hub_risk": body.flood_hub_risk,
            "present": fusion.present_sources,
            "missing": fusion.missing_sources,
        },
        "fusion_weights": fusion.weights,
    }
