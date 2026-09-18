"""Regression tests for src/hydrology/smap_soil_moisture.py - real NASA
SMAP soil moisture replacing soil_moisture.py's
random.seed(hash(district))-fabricated saturation_percent."""

from unittest.mock import MagicMock, patch

from src.hydrology.smap_soil_moisture import get_soil_moisture_for_district


def test_unknown_district_honestly_reported():
    result = get_soil_moisture_for_district("Not A Real District")
    assert result["available"] is False
    assert "not one of the 9 districts" in result["reason"]


def test_graceful_when_ee_unavailable():
    with patch(
        "src.hydrology.smap_soil_moisture.initialize_earth_engine", return_value=False
    ):
        result = get_soil_moisture_for_district("Tamale")
    assert result["available"] is False
    assert "Earth Engine unavailable" in result["reason"]


def _mock_ee_image(surface, rootzone, timestamp_ms):
    image = MagicMock()
    image.reduceRegion.return_value.getInfo.return_value = {
        "sm_surface": surface,
        "sm_rootzone": rootzone,
    }
    image.get.return_value.getInfo.return_value = timestamp_ms
    return image


def test_real_reading_computes_saturation_estimate_from_sensor_range():
    import time

    now_ms = int(time.time() * 1000)
    image = _mock_ee_image(surface=0.25, rootzone=0.36, timestamp_ms=now_ms)

    collection = MagicMock()
    collection.filterDate.return_value = collection
    collection.select.return_value = collection
    collection.sort.return_value = collection
    collection.first.return_value = image

    with patch(
        "src.hydrology.smap_soil_moisture.initialize_earth_engine", return_value=True
    ), patch("ee.ImageCollection", return_value=collection), patch(
        "ee.Geometry.Point"
    ), patch("ee.Reducer.first"):
        result = get_soil_moisture_for_district("Tamale")

    assert result["available"] is True
    assert result["root_zone_vwc_m3m3"] == 0.36
    assert result["surface_vwc_m3m3"] == 0.25
    # 0.36 / 0.9 * 100 = 40.0
    assert result["saturation_percent_estimate"] == 40.0
    assert result["stale"] is False


def test_no_image_in_window_honestly_reported():
    collection = MagicMock()
    collection.filterDate.return_value = collection
    collection.select.return_value = collection
    collection.sort.return_value = collection
    collection.first.return_value = None

    with patch(
        "src.hydrology.smap_soil_moisture.initialize_earth_engine", return_value=True
    ), patch("ee.ImageCollection", return_value=collection), patch("ee.Geometry.Point"):
        result = get_soil_moisture_for_district("Tamale")

    assert result["available"] is False
    assert "No real SMAP image" in result["reason"]


def test_stale_reading_flagged():
    import time

    old_ms = int((time.time() - 100 * 3600) * 1000)  # 100 hours old
    image = _mock_ee_image(surface=0.2, rootzone=0.3, timestamp_ms=old_ms)

    collection = MagicMock()
    collection.filterDate.return_value = collection
    collection.select.return_value = collection
    collection.sort.return_value = collection
    collection.first.return_value = image

    with patch(
        "src.hydrology.smap_soil_moisture.initialize_earth_engine", return_value=True
    ), patch("ee.ImageCollection", return_value=collection), patch(
        "ee.Geometry.Point"
    ), patch("ee.Reducer.first"):
        result = get_soil_moisture_for_district("Tamale")

    assert result["available"] is True
    assert result["stale"] is True
