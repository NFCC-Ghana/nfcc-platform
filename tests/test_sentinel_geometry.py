"""Sentinel-1 analysis area (src/hydrology/sentinel_processor.py)."""

from unittest.mock import MagicMock, patch

import importlib

sp = importlib.import_module("src.hydrology.sentinel_processor")


def test_analysis_area_is_a_degree_box_not_a_metre_buffer():
    """`point.buffer(0.05)` is 5 cm in Earth Engine (buffers are in metres),
    so no pixel was ever analysed. The area must be an explicit lat/lon box."""
    fake_ee = MagicMock()
    fake_ee.ImageCollection.return_value.filterBounds.return_value.filter.return_value.filter.return_value.filterDate.return_value.size.return_value.getInfo.return_value = (
        0
    )
    proc = sp.SentinelProcessor.__new__(sp.SentinelProcessor)
    proc.ee_initialized = True
    proc._live_cache = {}
    with patch.object(sp, "ee", fake_ee):
        result = proc.detect_flood_at("X", 9.4, -0.84, 0.08, "2026-10-01")
    fake_ee.Geometry.Rectangle.assert_called_once()
    (box,), _ = fake_ee.Geometry.Rectangle.call_args
    assert [round(v, 2) for v in box] == [-0.92, 9.32, -0.76, 9.48]
    fake_ee.Geometry.Point.return_value.buffer.assert_not_called()
    assert result["source"] == "Sentinel-1 (unavailable)"


def test_district_radius_is_used():
    proc = sp.sentinel_processor
    assert proc.districts["Tamale"]["radius"] == 0.08
    assert proc.districts["Ho"]["radius"] == 0.05
