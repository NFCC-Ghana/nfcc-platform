"""GloFAS discharge ratio (src/hydrology/glofas_discharge.py)."""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from src.hydrology import glofas_discharge as g


def _series(today_value, normal_value=10.0, days=3650):
    end = date(2026, 10, 31)
    times = [(end - timedelta(days=days - i)).isoformat() for i in range(days + 1)]
    values = [normal_value] * days + [today_value]
    return {"daily": {"time": times, "river_discharge": values}}


def _fetch(payload):
    g._cached_ratio.cache_clear()
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    with patch.object(g.requests, "get", return_value=resp) as get:
        ratio = g._cached_ratio(9.4, -0.84, "2026-10-31")
    return ratio, get.call_args.kwargs["params"]


def test_ratio_is_against_the_day_of_year_climatology():
    ratio, params = _fetch(_series(today_value=20.0))
    assert ratio == 2.0
    assert params["daily"] == "river_discharge"
    assert (
        "river_discharge_mean" not in params["daily"]
    )  # ensemble mean, not climatology


def test_short_history_gives_no_ratio():
    ratio, _ = _fetch(_series(today_value=20.0, days=200))
    assert ratio is None
