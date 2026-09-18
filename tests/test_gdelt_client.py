"""Regression tests for src/verification/gdelt_client.py."""

from unittest.mock import MagicMock, patch

from src.verification import gdelt_client
from src.verification.gdelt_client import search_flood_news


def test_real_articles_parsed():
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "articles": [
            {
                "title": "Flooding reported in Tamale",
                "url": "https://example.com/article",
                "seendate": "20260105T120000Z",
                "domain": "example.com",
            }
        ]
    }
    with patch.object(gdelt_client, "_throttle"), patch("requests.get", return_value=mock_resp):
        result = search_flood_news("Tamale", "2026-01-01", "2026-01-15")
    assert result["available"] is True
    assert result["count"] == 1
    assert result["matched_articles"][0]["domain"] == "example.com"


def test_rate_limited_plain_text_response_handled_gracefully():
    """The real, confirmed failure mode: a 429 rate-limit response is
    plain text, not JSON - resp.json() raises, and this must be caught
    and reported honestly, not crash or be silently misread as zero
    articles found."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.side_effect = ValueError("Expecting value: line 1 column 1")
    with patch.object(gdelt_client, "_throttle"), patch("requests.get", return_value=mock_resp):
        result = search_flood_news("Tamale", "2026-01-01", "2026-01-15")
    assert result["available"] is False
    assert "rate-limited" in result["reason"].lower() or "non-json" in result["reason"].lower()


def test_missing_fields_handled_defensively():
    """Since the exact live schema couldn't be verified due to
    rate-limiting during development, missing/unexpected fields must
    not crash parsing."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"articles": [{}]}
    with patch.object(gdelt_client, "_throttle"), patch("requests.get", return_value=mock_resp):
        result = search_flood_news("Tamale", "2026-01-01", "2026-01-15")
    assert result["available"] is True
    assert result["matched_articles"][0]["title"] is None


def test_graceful_on_request_failure():
    with patch.object(gdelt_client, "_throttle"), patch(
        "requests.get", side_effect=Exception("connection refused")
    ):
        result = search_flood_news("Tamale", "2026-01-01", "2026-01-15")
    assert result["available"] is False


def test_throttle_does_not_sleep_when_interval_already_elapsed():
    gdelt_client._last_request_time = 0.0
    start = gdelt_client.time.time()
    gdelt_client._throttle()
    # elapsed since epoch is huge, so no sleep should occur
    assert gdelt_client._last_request_time >= start


def test_throttle_sleeps_when_called_too_soon():
    gdelt_client._last_request_time = gdelt_client.time.time()
    with patch.object(gdelt_client.time, "sleep") as mock_sleep:
        gdelt_client._throttle()
    mock_sleep.assert_called_once()
    slept_seconds = mock_sleep.call_args[0][0]
    assert 0 < slept_seconds <= gdelt_client._MIN_REQUEST_INTERVAL_SECONDS
