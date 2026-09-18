"""Regression tests for src/verification/reliefweb_client.py."""

from unittest.mock import MagicMock, patch

from src.verification.reliefweb_client import search_flood_reports


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
