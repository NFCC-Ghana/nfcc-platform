"""Tests for rate limiter module."""

import time

import pytest

from src.alerts.rate_limit import RateLimiter


class TestRateLimiterInitialization:
    """Test rate limiter initialization."""

    def test_default_limit(self):
        limiter = RateLimiter()
        assert limiter.limit == 3
        assert limiter.max_alerts_per_hour == 3

    def test_custom_limit(self):
        limiter = RateLimiter(limit=5)
        assert limiter.limit == 5
        assert limiter.max_alerts_per_hour == 5
        # Test legacy parameter
        limiter2 = RateLimiter(max_alerts_per_hour=5)
        assert limiter2.limit == 5


class TestCanSend:
    """Test can_send method."""

    def test_can_send_initially(self):
        limiter = RateLimiter(limit=3)
        can_send, remaining = limiter.can_send("Accra")
        assert can_send is True
        assert remaining == 3

    def test_can_send_under_limit(self):
        limiter = RateLimiter(limit=2)
        limiter.record_send("Accra")
        can_send, remaining = limiter.can_send("Accra")
        assert can_send is True
        assert remaining == 1

    def test_cannot_send_at_limit(self):
        limiter = RateLimiter(limit=2)
        limiter.record_send("Accra")
        limiter.record_send("Accra")
        can_send, remaining = limiter.can_send("Accra")
        assert can_send is False
        assert remaining == 0

    def test_multiple_locations_independent(self):
        limiter = RateLimiter(limit=1)
        limiter.record_send("Accra")
        can_send_accra, _ = limiter.can_send("Accra")
        can_send_tema, _ = limiter.can_send("Tema")
        assert can_send_accra is False
        assert can_send_tema is True


class TestRecordSend:
    """Test record_send method."""

    def test_record_send_adds_entry(self):
        limiter = RateLimiter(limit=2)
        initial_remaining = limiter.get_remaining("Accra")
        assert initial_remaining == 2
        limiter.record_send("Accra")
        after_remaining = limiter.get_remaining("Accra")
        assert after_remaining == 1

    def test_record_send_multiple_entries(self):
        limiter = RateLimiter(limit=3)
        limiter.record_send("Accra")
        limiter.record_send("Accra")
        remaining = limiter.get_remaining("Accra")
        assert remaining == 1


class TestGetRemaining:
    """Test get_remaining method."""

    def test_get_remaining_initial(self):
        limiter = RateLimiter(limit=3)
        assert limiter.get_remaining("Accra") == 3

    def test_get_remaining_after_send(self):
        limiter = RateLimiter(limit=3)
        limiter.record_send("Accra")
        assert limiter.get_remaining("Accra") == 2

    def test_get_remaining_at_limit(self):
        limiter = RateLimiter(limit=2)
        limiter.record_send("Accra")
        limiter.record_send("Accra")
        assert limiter.get_remaining("Accra") == 0


class TestReset:
    """Test reset method."""

    def test_reset_specific_location(self):
        limiter = RateLimiter(limit=1)
        limiter.record_send("Accra")
        limiter.record_send("Tema")
        assert limiter.get_remaining("Accra") == 0
        assert limiter.get_remaining("Tema") == 0
        limiter.reset("Accra")
        assert limiter.get_remaining("Accra") == 1
        assert limiter.get_remaining("Tema") == 0

    def test_reset_all_locations(self):
        limiter = RateLimiter(limit=1)
        limiter.record_send("Accra")
        limiter.record_send("Tema")
        assert limiter.get_remaining("Accra") == 0
        assert limiter.get_remaining("Tema") == 0
        limiter.reset()
        assert limiter.get_remaining("Accra") == 1
        assert limiter.get_remaining("Tema") == 1
