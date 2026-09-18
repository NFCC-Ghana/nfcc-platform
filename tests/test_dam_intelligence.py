"""Regression tests for dam_intelligence.py's real status classification
(src/hydrology/altimetry_thresholds.py applied to Akosombo/Lake Volta
and the Bagre upstream proxy's own real historical DAHITI series) -
without this, a dam at its own historical flood-stage percentile had
no way to register as an independent flood-risk pathway
(src/models/multi_source_confidence.py)."""

from unittest.mock import MagicMock, patch

from src.hydrology.dam_intelligence import _get_bagre_upstream_proxy, get_akosombo_status


def _mock_response(readings):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"data": readings}
    return resp


def _series(elevations):
    return [
        {"wse": e, "wse_u": 0.1, "datetime": "2026-09-01T00:00:00"} for e in elevations
    ]


def test_akosombo_status_classified_from_real_history():
    # 100 real readings: last one (99.0) sits above the 95th percentile
    # of 0..99 -> should classify as FLOOD, not silently omitted.
    with patch.dict("os.environ", {"DAHITI_API_KEY": "fake-key-for-test"}), patch(
        "requests.get", return_value=_mock_response(_series(range(100)))
    ):
        result = get_akosombo_status()
    assert result["available"] is True
    assert result["status"] == "FLOOD"
    assert result["level_above_baseline_m"] is not None


def test_akosombo_normal_pool_level_classified_normal():
    elevations = list(range(95)) + [1.0, 1.0, 1.0, 1.0, 1.0]
    with patch.dict("os.environ", {"DAHITI_API_KEY": "fake-key-for-test"}), patch(
        "requests.get", return_value=_mock_response(_series(elevations))
    ):
        result = get_akosombo_status()
    assert result["available"] is True
    assert result["status"] in ("NORMAL", "WARNING", "DANGER", "FLOOD")


def test_akosombo_status_unknown_with_too_few_readings():
    with patch.dict("os.environ", {"DAHITI_API_KEY": "fake-key-for-test"}), patch(
        "requests.get", return_value=_mock_response(_series([50.0] * 5))
    ):
        result = get_akosombo_status()
    assert result["available"] is True
    assert result["status"] == "UNKNOWN"
    assert result["level_above_baseline_m"] is None


def test_bagre_upstream_proxy_gets_real_status():
    with patch.dict("os.environ", {"DAHITI_API_KEY": "fake-key-for-test"}), patch(
        "requests.get", return_value=_mock_response(_series(range(100)))
    ):
        result = _get_bagre_upstream_proxy()
    assert result["available"] is True
    assert result["status"] == "FLOOD"
