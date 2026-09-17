"""GET /v1/backtest - "what would CivicFlood have predicted before this
real historical flood event?" (src/models/historical_backtest.py).

Read-only and has no side effects (never calls AlertEngine, never
writes to any table) - it fetches real historical CHIRPS rainfall for
each documented event in src/hydrology/flood_polygons.py and runs it
through the exact calculate_score() every live endpoint already uses.
Can take a while to respond (one real Earth Engine query per historical
event) - this is an analysis/reporting endpoint, not a per-request path
anything else depends on.
"""

from fastapi import APIRouter

from src.models.historical_backtest import run_full_backtest

router = APIRouter(prefix="/backtest", tags=["v1"])


@router.get("")
async def get_historical_backtest() -> dict:
    return run_full_backtest()
