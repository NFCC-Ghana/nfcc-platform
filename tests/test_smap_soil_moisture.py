"""Regression tests for src/hydrology/smap_soil_moisture.py - real NASA
SMAP soil moisture replacing soil_moisture.py's
random.seed(hash(district))-fabricated saturation_percent."""

from unittest.mock import MagicMock, patch

import pytest

from src.hydrology import smap_soil_moisture
from src.hydrology.smap_soil_moisture import get_soil_moisture_for_district


@pytest.fixture(autouse=True)
def _clear_smap_cache():
    """get_soil_moisture_for_district now caches successful readings per
    district for _CACHE_TTL_SECONDS (added to protect real Earth Engine
    quota/latency, see that module's comment) - without clearing this
    between tests, an earlier test's mocked "Tamale" reading would still
    be cached when a later test mocks a *different* EE response for the
    same district, making that later test's assertions fail against
    stale cached data instead of its own fresh mock."""
    smap_soil_moisture._cache.clear()
    yield
    smap_soil_moisture._cache.clear()


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


def test_second_call_within_ttl_uses_cache_not_earth_engine():
    """The real regression this caching was added for: a security/
    performance audit found every /situation call hitting Earth Engine
    live and uncached, a real quota/latency risk now that the kiosk view
    polls /situation every 90s. A second call for the same district
    within _CACHE_TTL_SECONDS must not touch Earth Engine again."""
    image = _mock_ee_image(surface=0.25, rootzone=0.36, timestamp_ms=int(__import__("time").time() * 1000))
    collection = MagicMock()
    collection.filterDate.return_value = collection
    collection.select.return_value = collection
    collection.sort.return_value = collection
    collection.first.return_value = image

    with patch(
        "src.hydrology.smap_soil_moisture.initialize_earth_engine", return_value=True
    ) as mock_init, patch("ee.ImageCollection", return_value=collection), patch(
        "ee.Geometry.Point"
    ), patch("ee.Reducer.first"):
        first = get_soil_moisture_for_district("Tamale")
        second = get_soil_moisture_for_district("Tamale")

    assert first == second
    # initialize_earth_engine() is the first real call inside the
    # uncached fetch path - it running only once proves the second call
    # was served from cache rather than repeating the Earth Engine query.
    assert mock_init.call_count == 1


def test_cache_does_not_apply_across_different_districts():
    """A cached Tamale reading must never leak into a different
    district's result."""
    image = _mock_ee_image(surface=0.25, rootzone=0.36, timestamp_ms=int(__import__("time").time() * 1000))
    collection = MagicMock()
    collection.filterDate.return_value = collection
    collection.select.return_value = collection
    collection.sort.return_value = collection
    collection.first.return_value = image

    with patch(
        "src.hydrology.smap_soil_moisture.initialize_earth_engine", return_value=True
    ) as mock_init, patch("ee.ImageCollection", return_value=collection), patch(
        "ee.Geometry.Point"
    ), patch("ee.Reducer.first"):
        get_soil_moisture_for_district("Tamale")
        get_soil_moisture_for_district("Accra Central")

    assert mock_init.call_count == 2


def test_unavailable_result_is_not_cached():
    """An honest available=False must never be cached - a transient
    Earth Engine outage shouldn't stay "stuck" unavailable for a full
    _CACHE_TTL_SECONDS once Earth Engine recovers on the very next
    request."""
    with patch(
        "src.hydrology.smap_soil_moisture.initialize_earth_engine", return_value=False
    ) as mock_init:
        get_soil_moisture_for_district("Tamale")
        get_soil_moisture_for_district("Tamale")

    assert mock_init.call_count == 2
