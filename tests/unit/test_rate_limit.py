"""Tests for rate limiter."""

import time
from src.alerts.rate_limit import RateLimiter


class TestRateLimiterInitialization:
    def test_default_limit(self):
        limiter = RateLimiter()
        assert limiter.max_alerts_per_hour == 3

    def test_custom_limit(self):
        limiter = RateLimiter(max_alerts_per_hour=5)
        assert limiter.max_alerts_per_hour == 5


class TestCanSend:
    def test_can_send_initially(self):
        limiter = RateLimiter(max_alerts_per_hour=3)
        assert limiter.can_send("test") is True

    def test_can_send_under_limit(self):
        limiter = RateLimiter(max_alerts_per_hour=2)
        limiter.record_send("test")
        assert limiter.can_send("test") is True

    def test_cannot_send_at_limit(self):
        limiter = RateLimiter(max_alerts_per_hour=2)
        limiter.record_send("test")
        limiter.record_send("test")
        assert limiter.can_send("test") is False

    def test_multiple_locations_independent(self):
        limiter = RateLimiter(max_alerts_per_hour=1)
        limiter.record_send("loc1")
        assert limiter.can_send("loc2") is True
        assert limiter.can_send("loc1") is False


class TestRecordSend:
    def test_record_send_adds_entry(self):
        limiter = RateLimiter(max_alerts_per_hour=2)
        limiter.record_send("test")
        assert len(limiter._history["test"]) == 1

    def test_record_send_multiple_entries(self):
        limiter = RateLimiter(max_alerts_per_hour=3)
        limiter.record_send("test")
        limiter.record_send("test")
        assert len(limiter._history["test"]) == 2


class TestGetRemaining:
    def test_get_remaining_initial(self):
        limiter = RateLimiter(max_alerts_per_hour=3)
        assert limiter.get_remaining("test") == 3

    def test_get_remaining_after_send(self):
        limiter = RateLimiter(max_alerts_per_hour=3)
        limiter.record_send("test")
        assert limiter.get_remaining("test") == 2

    def test_get_remaining_at_limit(self):
        limiter = RateLimiter(max_alerts_per_hour=2)
        limiter.record_send("test")
        limiter.record_send("test")
        assert limiter.get_remaining("test") == 0


class TestReset:
    def test_reset_specific_location(self):
        limiter = RateLimiter(max_alerts_per_hour=1)
        limiter.record_send("loc1")
        limiter.record_send("loc2")
        limiter.reset("loc1")
        assert limiter.can_send("loc1") is True
        assert limiter.can_send("loc2") is False

    def test_reset_all_locations(self):
        limiter = RateLimiter(max_alerts_per_hour=1)
        limiter.record_send("loc1")
        limiter.record_send("loc2")
        limiter.reset()
        assert limiter.can_send("loc1") is True
        assert limiter.can_send("loc2") is True
