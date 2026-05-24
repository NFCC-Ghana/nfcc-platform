"""Reusable API assertion helpers for production hardening."""

from typing import List, Optional


class APIAssertions:
    """Reusable API assertion helpers for production hardening."""

    @staticmethod
    def assert_status(response, expected: int, message: str = None):
        """Assert response status code with optional custom message."""
        msg = message or f"Expected {expected}, got {response.status_code}. Body: {response.text[:200]}"
        assert response.status_code == expected, msg

    @staticmethod
    def assert_success(response, expected_status: int = 200):
        """Assert successful response (2xx)."""
        assert 200 <= response.status_code < 300, f"Expected success, got {response.status_code}"

    @staticmethod
    def assert_json_contains(response, keys: List[str]):
        """Assert response JSON contains all specified keys."""
        data = response.json()
        for key in keys:
            assert key in data, f"Missing key: '{key}'. Response keys: {list(data.keys())}"

    @staticmethod
    def assert_score_valid(response):
        """Assert response contains valid score (0-100)."""
        data = response.json()
        assert "score" in data or "risk_score" in data, f"No score field found: {data}"
        
        score = data.get("score") or data.get("risk_score")
        assert isinstance(score, (int, float)), f"Score must be numeric, got {type(score)}"
        assert 0 <= score <= 100, f"Score must be between 0-100, got {score}"
