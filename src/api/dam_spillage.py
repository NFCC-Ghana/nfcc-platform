


from fastapi import APIRouter, HTTPException
from src.config.dams import DAM_CONFIG
from src.models.dam_spillage import get_spillage_forecast


router = APIRouter()
@router.get("/dam-spillage")


def dam_spillage(dam: str):
    dam = dam.lower()
    if dam not in DAM_CONFIG:
        raise HTTPException(status_code = 400, detail = "invalid dam")
    
    
    # Simulated extreme conditions based on 2023 Akosombo spillage event
    if dam == "akosombo":
        rainfall = 180
        reservoir_level = 95
        inflow = 450
    else:
        rainfall = 100
    reservoir_level = 70
    inflow = 200
    
    
    return get_spillage_forecast(dam, rainfall, reservoir_level, inflow)

