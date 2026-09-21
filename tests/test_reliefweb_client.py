"""Regression tests for src/verification/reliefweb_client.py."""

from unittest.mock import MagicMock, patch

from src.verification.reliefweb_client import _to_iso_datetime, search_flood_reports


def test_unavailable_when_appname_not_configured():
    with patch.dict("os.environ", {}, clear=False):
        import os

        os.environ.pop("RELIEFWEB_APPNAME", None)
        result = search_flood_reports("Tamale", "2026-01-01", "2026-01-15")
    assert result["available"] is False
    assert "RELIEFWEB_APPNAME" in result["reason"]


def test_real_reports_parsed_when_configured():
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "data": [
            {
                "href": "https://reliefweb.int/report/ghana/example",
                "fields": {
                    "title": "Ghana: Floods - Example Report",
                    "date": {"created": "2026-01-05T00:00:00+00:00"},
                },
            }
        ]
    }
    with patch.dict("os.environ", {"RELIEFWEB_APPNAME": "approved-app"}), patch(
        "requests.get", return_value=mock_resp
    ):
        result = search_flood_reports("Tamale", "2026-01-01", "2026-01-15")
    assert result["available"] is True
    assert result["count"] == 1
    assert result["matched_reports"][0]["title"] == "Ghana: Floods - Example Report"


def test_graceful_on_request_failure():
    with patch.dict("os.environ", {"RELIEFWEB_APPNAME": "approved-app"}), patch(
        "requests.get", side_effect=Exception("connection refused")
    ):
        result = search_flood_reports("Tamale", "2026-01-01", "2026-01-15")
    assert result["available"] is False


def test_bare_dates_are_normalized_to_full_iso_datetimes():
    """Regression test for a real bug: ReliefWeb's date.created range
    filter rejects a bare 'YYYY-MM-DD' with 'UnexpectedValueException:
    ... It must be an ISO 8601 date' - only caught by testing through
    the real outcome_verifier.py code path (which passes bare dates)
    against the live API, not by a simpler direct call that omitted the
    date filter entirely."""
    assert _to_iso_datetime("2026-09-21") == "2026-09-21T00:00:00+00:00"
    assert _to_iso_datetime("2026-09-21", end_of_day=True) == "2026-09-21T23:59:59+00:00"
    # Already a full datetime - passed through unchanged, not double-appended.
    already_full = "2026-09-21T12:00:00+00:00"
    assert _to_iso_datetime(already_full) == already_full


def test_search_sends_full_iso_datetimes_to_reliefweb():
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"data": []}

    with patch.dict("os.environ", {"RELIEFWEB_APPNAME": "approved-app"}), patch(
        "requests.get", return_value=mock_resp
    ) as mock_get:
        search_flood_reports("Tamale", "2026-01-01", "2026-01-15")

    sent_params = mock_get.call_args.kwargs["params"]
    assert sent_params["filter[value][from]"] == "2026-01-01T00:00:00+00:00"
    assert sent_params["filter[value][to]"] == "2026-01-15T23:59:59+00:00"
