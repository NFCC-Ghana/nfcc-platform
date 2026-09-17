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
    ), patch("requests.post", side_effect=post_side_effect):
        exit_code = script.run("https://fake-api.example")

    assert exit_code == 0
