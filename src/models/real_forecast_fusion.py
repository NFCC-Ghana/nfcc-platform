"""Real per-district inputs for src/models/forecast_fusion.py's fusion
math - built 2026-09-27 to actually activate it. Before this,
forecast_fusion.py + confidence_scoring.py were real, tested code with
no real caller: GET /forecast/confidence (src/api/routes/forecast.py)
only ever took caller-supplied chirps_risk/glofas_risk/flood_hub_risk
numbers, and nothing in this codebase computed real ones to feed it -
src/models/multi_source_confidence.py's own docstring already documented
this as "a disconnected chirps/glofas/flood_hub demo with its own tests."

This module computes all three real inputs and calls the same
fuse_forecasts()/forecast_confidence() functions GET /forecast/confidence
already uses, in-process - the same "call the real function directly,
not over HTTP" pattern every other endpoint in this API already follows
(e.g. GET /v1/districts/{d}/resources calling _build_situation_response()
directly). GET /forecast/confidence itself is left as a separate,
still-useful generic "fuse whatever numbers you give me" utility for
manual what-if analysis - this module is the real, per-district path
alongside it, not a replacement for it.

- chirps_risk: real 3-day antecedent CHIRPS rainfall accumulation
  (src/hydrology/antecedent_rainfall.py) through the same
  calculate_score() curve every other real risk figure in this platform
  uses. Distinct from the platform's main score (fed by Open-Meteo
  forecast rainfall via /situation's precipitation input) - this is what
  CHIRPS specifically says about rain that has already fallen.
- glofas_risk: real Open-Meteo Flood API (GloFAS-based) river discharge,
  today's value relative to its own long-term seasonal mean, normalized
  against the same _ELEVATED_DISCHARGE_RATIO=1.5 threshold already
  established and used by GET /national/summary's "active flood zone"
  flag (src/api/routes/situation.py) - not a second, independently-
  invented threshold. 0 at ratio<=1.0 (at or below seasonal mean), 60 at
  the real 1.5x "elevated" threshold, 100 at 2.5x or beyond.
- flood_hub_risk: src/hydrology/flood_hub_forecast.py - honestly
  unavailable in production until real Flood Forecasting API pilot
  access exists (see that module's docstring).
"""

from __future__ import annotations

from typing import Dict, Optional

from src.alerts.formatter import calculate_score
from src.exposure.districts import get_district
from src.hydrology.antecedent_rainfall import get_antecedent_rainfall
from src.hydrology.flood_hub_forecast import get_flood_hub_forecast_for_district
from src.hydrology.glofas_discharge import (
    ELEVATED_DISCHARGE_RATIO,
    fetch_glofas_discharge_ratio,
)
from src.models.confidence_scoring import forecast_confidence
from src.models.forecast_fusion import ForecastFusionInput, fuse_forecasts

# Beyond this multiple of the seasonal mean, glofas_risk is treated as
# maximal - no real Ghana-specific flood-stage discharge threshold exists
# publicly (see glofas_discharge.py's own comment on
# ELEVATED_DISCHARGE_RATIO), so this extends that same illustrative
# anchor rather than inventing an unrelated second one.
_MAX_DISCHARGE_RATIO = 2.5


def _normalize_glofas_ratio(ratio: float) -> float:
    if ratio <= 1.0:
        return 0.0
    if ratio < ELEVATED_DISCHARGE_RATIO:
        return round(60.0 * (ratio - 1.0) / (ELEVATED_DISCHARGE_RATIO - 1.0), 1)
    if ratio < _MAX_DISCHARGE_RATIO:
        return round(
            60.0
            + 40.0
            * (ratio - ELEVATED_DISCHARGE_RATIO)
            / (_MAX_DISCHARGE_RATIO - ELEVATED_DISCHARGE_RATIO),
            1,
        )
    return 100.0


def get_chirps_risk(district: str) -> Dict:
    """Real chirps_risk (0-100) from real 3-day antecedent CHIRPS
    rainfall, or an honest available=False when that's unavailable OR
    stale. get_antecedent_rainfall's own "stale" flag (beyond
    _STALE_AFTER_DAYS=10) explicitly means the found accumulation "no
    longer represents current ground conditions" - feeding a stale value
    into the fusion as if it were current would misrepresent it exactly
    the way this platform's disclosure discipline exists to prevent, so
    stale is treated as unavailable here rather than degraded-but-used."""
    antecedent = get_antecedent_rainfall(district)
    if not antecedent.get("available"):
        return {"available": False, "reason": antecedent.get("reason")}
    if antecedent["stale"]:
        return {
            "available": False,
            "reason": (
                f"Most recent real CHIRPS data is {antecedent['data_age_days']} "
                "days old - too stale to represent current ground conditions"
            ),
            "data_age_days": antecedent["data_age_days"],
        }
    risk = calculate_score(antecedent["rolling_3d_mm"])
    return {
        "available": True,
        "risk": risk,
        "rolling_3d_mm": antecedent["rolling_3d_mm"],
        "data_age_days": antecedent["data_age_days"],
    }


def get_glofas_risk(lat: float, lon: float) -> Dict:
    """Real glofas_risk (0-100) from real Open-Meteo Flood API discharge,
    or an honest available=False when no river is resolved at this point
    or the API call failed."""
    ratio = fetch_glofas_discharge_ratio(lat, lon)
    if ratio is None:
        return {
            "available": False,
            "reason": "No river resolved at this location or Flood API unreachable",
        }
    return {
        "available": True,
        "risk": _normalize_glofas_ratio(ratio),
        "discharge_ratio": round(ratio, 2),
    }


def get_real_forecast_fusion(district: str) -> Dict:
    """Real chirps_risk + glofas_risk + flood_hub_risk for one district,
    fused through the exact same fuse_forecasts()/forecast_confidence()
    GET /forecast/confidence already uses - the real, per-district
    activation of that previously-disconnected math. Each source's own
    real availability/value is included alongside the fused result so a
    caller can see exactly what did and didn't contribute, never a
    number presented as more complete than it is."""
    district_info = get_district(district)
    if district_info is None:
        return {
            "available": False,
            "reason": f"'{district}' is not one of the 9 tracked districts",
        }

    chirps = get_chirps_risk(district)
    glofas = get_glofas_risk(district_info.lat, district_info.lon)
    flood_hub = get_flood_hub_forecast_for_district(district_info.lat, district_info.lon)

    inp = ForecastFusionInput(
        chirps_risk=chirps["risk"] if chirps.get("available") else None,
        glofas_risk=glofas["risk"] if glofas.get("available") else None,
        flood_hub_risk=flood_hub.get("flood_hub_risk") if flood_hub.get("available") else None,
    )
    fusion = fuse_forecasts(inp)
    confidence = forecast_confidence(inp, fusion.unified_risk)

    return {
        "available": True,
        "district": district,
        "unified_risk": round(fusion.unified_risk, 1),
        "confidence": round(confidence.confidence, 1),
        "present_sources": fusion.present_sources,
        "missing_sources": fusion.missing_sources,
        "sources": {
            "chirps": chirps,
            "glofas": glofas,
            "flood_hub": flood_hub,
        },
    }
