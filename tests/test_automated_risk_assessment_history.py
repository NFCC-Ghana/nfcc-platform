"""Regression test for scripts/automated_risk_assessment.py's risk_history
orchestration (priority deliverable #9's "automated updates" piece) -
confirms it POSTs a snapshot for every district on every run, and that a
history POST failure doesn't fail the district's overall assessment."""

from unittest.mock import MagicMock, patch

import scripts.automated_risk_assessment as script


def _mock_response(json_data, raise_for_status_error=None):
    resp = MagicMock()
    resp.json.return_value = json_data
    if raise_for_status_error:
        resp.raise_for_status.side_effect = raise_for_status_error
    else:
        resp.raise_for_status.return_value = None
    return resp


def test_history_posted_for_every_district():
    with patch.object(
        script, "get_forecast_precipitation", return_value=42.0
    ), patch.object(
        script, "get_antecedent_precipitation", return_value=None
    ), patch("requests.post") as mock_post:
        mock_post.return_value = _mock_response({"queued": False, "score": 50})

        script.run("https://fake-api.example")

        history_calls = [
            c
            for c in mock_post.call_args_list
            if "/risk/history" in c.args[0]
        ]
        assert len(history_calls) == len(script.DISTRICT_COORDS)
        for call in history_calls:
            assert call.kwargs["json"]["precipitation_mm"] == 42.0
            assert call.kwargs["json"]["source"] == "scheduled"


def test_history_post_failure_does_not_fail_district():
    """A district whose /alerts/assess call succeeds but whose
    /risk/history call fails must NOT count as a failure - the real-time
    assessment already succeeded independently of the historical record."""

    def post_side_effect(url, **kwargs):
        if "/risk/history" in url:
            return _mock_response({}, raise_for_status_error=Exception("db down"))
        return _mock_response({"queued": False, "score": 50})

    with patch.object(
        script, "get_forecast_precipitation", return_value=10.0
    ), patch.object(
        script, "get_antecedent_precipitation", return_value=None
    ), patch("requests.post", side_effect=post_side_effect):
        exit_code = script.run("https://fake-api.example")

    assert exit_code == 0


def test_both_signals_assessed_and_tagged_with_basis():
    """The whole point of this pipeline change: forecast and antecedent
    rainfall are real, independent signals - each must be posted to
    /alerts/assess separately, tagged with which one it is, not merged
    into one opaque number."""
    with patch.object(
        script, "get_forecast_precipitation", return_value=5.0
    ), patch.object(
        script, "get_antecedent_precipitation", return_value=40.0
    ), patch("requests.post") as mock_post:
        mock_post.return_value = _mock_response({"queued": False, "score": 50})

        script.run("https://fake-api.example")

        assess_calls = [
            c for c in mock_post.call_args_list if "/alerts/assess" in c.args[0]
        ]
        # One forecast + one antecedent assessment per district
        assert len(assess_calls) == len(script.DISTRICT_COORDS) * 2

        bases = {c.kwargs["json"]["basis"] for c in assess_calls}
        assert bases == {"forecast_next_24h", "antecedent_3d_accumulation"}

        forecast_calls = [
            c for c in assess_calls if c.kwargs["json"]["basis"] == "forecast_next_24h"
        ]
        antecedent_calls = [
            c
            for c in assess_calls
            if c.kwargs["json"]["basis"] == "antecedent_3d_accumulation"
        ]
        assert all(c.kwargs["json"]["precipitation"] == 5.0 for c in forecast_calls)
        assert all(
            c.kwargs["json"]["precipitation"] == 40.0 for c in antecedent_calls
        )


def test_antecedent_unavailable_still_assesses_forecast():
    """A district with no real antecedent data yet (e.g. Earth Engine
    unavailable) must not block the forecast-based assessment that
    already worked before this signal existed."""
    with patch.object(
        script, "get_forecast_precipitation", return_value=15.0
    ), patch.object(
        script, "get_antecedent_precipitation", return_value=None
    ), patch("requests.post") as mock_post:
        mock_post.return_value = _mock_response({"queued": False, "score": 50})

        exit_code = script.run("https://fake-api.example")

        assess_calls = [
            c for c in mock_post.call_args_list if "/alerts/assess" in c.args[0]
        ]
        assert len(assess_calls) == len(script.DISTRICT_COORDS)
        assert all(
            c.kwargs["json"]["basis"] == "forecast_next_24h" for c in assess_calls
        )
    assert exit_code == 0


def test_get_antecedent_precipitation_returns_none_when_unavailable():
    with patch(
        "requests.get",
        return_value=_mock_response({"available": False, "reason": "no EE"}),
    ):
        result = script.get_antecedent_precipitation(
            "https://fake-api.example", "Accra Central"
        )
    assert result is None


def test_get_antecedent_precipitation_returns_real_value():
    with patch(
        "requests.get",
        return_value=_mock_response({"available": True, "rolling_3d_mm": 33.5}),
    ):
        result = script.get_antecedent_precipitation(
            "https://fake-api.example", "Accra Central"
        )
    assert result == 33.5
