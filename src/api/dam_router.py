"""API endpoints for dam spillage prediction."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.config.dams import DAM_CONFIG
from src.models.dam_spillage import get_spillage_forecast, validate_historical_events

router = APIRouter(prefix="/api/dam", tags=["Dam Spillage"])


@router.get("/spillage")
async def dam_spillage(
    dam: str = Query(..., description="Dam name: 'akosombo' or 'bagre'"),
    rainfall: Optional[float] = Query(None, description="Rainfall in mm"),
    reservoir_level: Optional[float] = Query(None, description="Reservoir level in %"),
    inflow: Optional[float] = Query(None, description="Inflow rate in m³/s"),
):
    dam = dam.lower()
    if dam not in DAM_CONFIG:
        raise HTTPException(400, "Invalid dam. Supported: akosombo, bagre")

    if dam == "akosombo":
        defaults = (180, 95, 450)
    else:
        defaults = (150, 90, 350)

    final_rainfall = rainfall if rainfall is not None else defaults[0]
    final_reservoir_level = (
        reservoir_level if reservoir_level is not None else defaults[1]
    )
    final_inflow = inflow if inflow is not None else defaults[2]

    if final_rainfall < 0:
        raise HTTPException(400, "Rainfall cannot be negative")
    if final_reservoir_level < 0 or final_reservoir_level > 100:
        raise HTTPException(400, "Reservoir level must be between 0 and 100")
    if final_inflow < 0:
        raise HTTPException(400, "Inflow cannot be negative")

    forecast = get_spillage_forecast(
        dam, final_rainfall, final_reservoir_level, final_inflow
    )
    forecast["timestamp"] = datetime.utcnow().isoformat() + "Z"
    forecast["note"] = "Based on simulated data pending VRA partnership"
    return forecast


@router.get("/spillage/all")
async def get_all_dams_spillage():
    results = {}
    for dam_name in DAM_CONFIG.keys():
        if dam_name == "akosombo":
            rainfall, reservoir_level, inflow = 180, 95, 450
        else:
            rainfall, reservoir_level, inflow = 150, 90, 350
        forecast = get_spillage_forecast(dam_name, rainfall, reservoir_level, inflow)
        forecast["timestamp"] = datetime.utcnow().isoformat() + "Z"
        forecast["note"] = "Based on simulated data pending VRA partnership"
        results[dam_name] = forecast
    return {"dams": results, "timestamp": datetime.utcnow().isoformat() + "Z"}


@router.get("/spillage/validate")
async def validate_model():
    return validate_historical_events()
