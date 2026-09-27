"""Tests for src.hydrology's real, live modules.

Previously also tested rainfall_history.py, reservoir_intelligence.py,
river_intelligence.py, soil_moisture.py, and unified_intelligence.py -
all deleted 2026-09-27 as confirmed-dead fabricated code (see
src/hydrology/__init__.py's docstring). Only flood_polygons was ever a
real module in this file; its test is kept as-is.
"""

from src.hydrology.flood_polygons import flood_polygons


def test_flood_polygons():
    """Test flood polygon engine."""
    events = flood_polygons.get_flood_events("Accra Central")
    assert events is not None
    print("✅ Flood polygon test passed")
