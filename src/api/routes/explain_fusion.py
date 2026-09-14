"""SHAP-based explanation for forecast fusion (separate from /explain/)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.models.forecast_fusion import ForecastFusionInput, fuse_forecasts
from src.models.fusion_explain import explain_fusion_shap

router = APIRouter(prefix="/explain", tags=["Explainability", "Forecast"])


class ExplainFusionRequest(BaseModel):
    location: str = Field(..., description="District or place label")
    chirps_risk: Optional[float] = Field(None, ge=0.0, le=100.0)
    glofas_risk: Optional[float] = Field(None, ge=0.0, le=100.0)
    flood_hub_risk: Optional[float] = Field(None, ge=0.0, le=100.0)
    nsamples: int = Field(
        64, ge=8, le=400, description="KernelExplainer samples (latency vs fidelity)"
    )


@router.post("/forecast")
async def explain_forecast_endpoint(body: ExplainFusionRequest) -> Dict[str, Any]:
    """Return SHAP values for each active source relative to baseline risk."""
    inp = ForecastFusionInput(
        chirps_risk=body.chirps_risk,
        glofas_risk=body.glofas_risk,
        flood_hub_risk=body.flood_hub_risk,
    )
    fusion = fuse_forecasts(inp)
    expl = explain_fusion_shap(inp, nsamples=body.nsamples)

    ranked = sorted(expl.shap_values.items(), key=lambda kv: abs(kv[1]), reverse=True)
    summary_parts = [
        f"{k} ({v:+.2f})"
        for k, v in ranked
        if expl.shap_values.get(k, 0.0) != 0.0 or k in fusion.present_sources
    ]
    summary = (
        "Contribution ranking: " + ", ".join(summary_parts)
        if summary_parts
        else "No active sources."
    )

    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "status": "success",
        "location": body.location,
        "timestamp": ts,
        "unified_risk": round(fusion.unified_risk, 2),
        "expected_value": round(expl.expected_value, 4),
        "shap_values": {k: round(float(v), 4) for k, v in expl.shap_values.items()},
        "baseline": expl.baseline,
        "summary": summary,
        "present_sources": fusion.present_sources,
        "missing_sources": fusion.missing_sources,
    }
