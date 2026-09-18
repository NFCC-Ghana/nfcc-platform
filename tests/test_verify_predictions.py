"""Regression tests for scripts/verify_predictions.py - the automated
replacement for manually curating prediction outcomes."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import scripts.verify_predictions as script


def _mock_response(json_data, raise_for_status_error=None):
    resp = MagicMock()
    resp.json.return_value = json_data
    if raise_for_status_error:
        resp.raise_for_status.side_effect = raise_for_status_error
    else:
        resp.raise_for_status.return_value = None
    return resp


def _iso_days_ago(days: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def test_predictions_within_age_window_are_verified():
    pending = {
        "predictions": [
            {"id": 1, "district": "Tamale", "predicted_at": _iso_days_ago(5)},
        ]
    }

    def get_side_effect(url, **kwargs):
        return _mock_response(pending)

    def post_side_effect(url, **kwargs):
        return _mock_response(
            {"verification": {"outcome": "no_evidence_found", "outcome_source": "automated_check_no_signal"}}
        )

    with patch("requests.get", side_effect=get_side_effect), patch(
        "requests.post", side_effect=post_side_effect
    ) as mock_post:
        exit_code = script.run("https://fake-api.example")

    verify_calls = [c for c in mock_post.call_args_list if "auto-verify" in c.args[0]]
    assert len(verify_calls) == 1
    assert exit_code == 0


def test_too_recent_predictions_skipped():
    pending = {
        "predictions": [
            {"id": 1, "district": "Tamale", "predicted_at": _iso_days_ago(0.5)},
        ]
    }
    with patch("requests.get", return_value=_mock_response(pending)), patch(
        "requests.post"
    ) as mock_post:
        script.run("https://fake-api.example")

    assert mock_post.call_count == 0


def test_too_old_predictions_skipped():
    pending = {
        "predictions": [
            {"id": 1, "district": "Tamale", "predicted_at": _iso_days_ago(90)},
        ]
    }
    with patch("requests.get", return_value=_mock_response(pending)), patch(
        "requests.post"
    ) as mock_post:
        script.run("https://fake-api.example")

    assert mock_post.call_count == 0


def test_confirmed_outcome_logged_as_warning(caplog):
    pending = {
        "predictions": [
            {"id": 42, "district": "Tema", "predicted_at": _iso_days_ago(10)},
        ]
    }
    with patch("requests.get", return_value=_mock_response(pending)), patch(
        "requests.post",
        return_value=_mock_response(
            {"verification": {"outcome": "flood_confirmed", "outcome_source": "ReliefWeb"}}
        ),
    ):
        with caplog.at_level("WARNING"):
            script.run("https://fake-api.example")

    assert any("CONFIRMED" in r.message for r in caplog.records)


def test_auto_verify_failure_does_not_crash_other_predictions():
    pending = {
        "predictions": [
            {"id": 1, "district": "Tamale", "predicted_at": _iso_days_ago(5)},
            {"id": 2, "district": "Tema", "predicted_at": _iso_days_ago(5)},
        ]
    }

    def post_side_effect(url, **kwargs):
        if "/1/" in url:
            return _mock_response({}, raise_for_status_error=Exception("timeout"))
        return _mock_response(
            {"verification": {"outcome": "no_evidence_found", "outcome_source": "automated_check_no_signal"}}
        )

    with patch("requests.get", return_value=_mock_response(pending)), patch(
        "requests.post", side_effect=post_side_effect
    ) as mock_post:
        exit_code = script.run("https://fake-api.example")

    assert mock_post.call_count == 2
    assert exit_code == 0  # one real success out of two means overall success


def test_fetch_pending_failure_returns_error_exit_code():
    with patch("requests.get", side_effect=Exception("connection refused")):
        exit_code = script.run("https://fake-api.example")
    assert exit_code == 1


def test_no_pending_predictions_is_a_clean_success():
    with patch("requests.get", return_value=_mock_response({"predictions": []})), patch(
        "requests.post"
    ) as mock_post:
        exit_code = script.run("https://fake-api.example")

    assert mock_post.call_count == 0
    assert exit_code == 0
