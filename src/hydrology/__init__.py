"""Hydrology module for flood prediction."""

from .flood_polygons import flood_polygons
from .rainfall_history import rainfall_history
from .reservoir_intelligence import reservoir_intelligence
from .river_intelligence import river_intelligence
from .soil_moisture import soil_moisture
from .unified_intelligence import unified_intelligence

__all__ = [
    "unified_intelligence",
    "rainfall_history",
    "river_intelligence",
    "reservoir_intelligence",
    "soil_moisture",
    "flood_polygons",
]

# New modules
from .river_gauge_api import river_gauge_api
from .sentinel_processor import sentinel_processor
from .urban_drainage import urban_drainage
from .vra_telemetry import vra_telemetry

__all__ = [
    "unified_intelligence",
    "rainfall_history",
    "river_intelligence",
    "reservoir_intelligence",
    "soil_moisture",
    "flood_polygons",
    "weather_forecast",
    "river_gauge_api",
    "vra_telemetry",
    "sentinel_processor",
    "urban_drainage",
]
