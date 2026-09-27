"""Hydrology module for flood prediction.

Deleted 2026-09-27: rainfall_history.py, reservoir_intelligence.py,
river_gauge_api.py, river_intelligence.py, soil_moisture.py,
unified_intelligence.py, vra_telemetry.py - ~2,059 lines of fabricated
data (np.random.seed(hash(...))-based), confirmed to have zero real
callers anywhere outside each other and their own now-also-removed test
file. Each was already superseded by a real, satellite-data-backed
replacement genuinely wired into the live request path: river_intelligence
-> river_level_intelligence.py (real DAHITI altimetry), soil_moisture ->
smap_soil_moisture.py (real NASA SMAP), reservoir_intelligence/
vra_telemetry -> dam_intelligence.py (real DAHITI-based Akosombo/Bagre
disclosure). Kept as dead-but-disclosed code for a while so nothing that
might still reference them broke silently; removed outright once an
audit confirmed nothing does - loading ~2,000 lines of inert fabricated
logic into memory on every hydrology-touching request served no purpose
and was a standing risk of accidental reactivation.
"""

from .flood_polygons import flood_polygons
from .sentinel_processor import sentinel_processor
from .urban_drainage import urban_drainage
from .weather_forecast import weather_forecast

__all__ = [
    "flood_polygons",
    "weather_forecast",
    "sentinel_processor",
    "urban_drainage",
]
