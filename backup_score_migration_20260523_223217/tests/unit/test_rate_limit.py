"""Tests for rate limiting module."""

from datetime import datetime, timedelta
from unittest.mock import patch

from src.alerts.rate_limit import RateLimiter

# ════════════════════════════════════════════════════════════════
# BASIC INITIALIZATION
# ════════════════════════════════════════════════════════════════


class TestRateLimiterInitialization:
    def test_default_limit(self):
        limiter = RateLimiter()

        assert limiter.max_alerts == 3

    def test_custom_limit(self):
        limiter = RateLimiter(max_alerts=5)

        assert limiter.max_alerts == 5


# ════════════════════════════════════════════════════════════════
# can_send()
# ════════════════════════════════════════════════════════════════


class TestCanSend:
    def test_can_send_initially(self):
        limiter = RateLimiter(max_alerts=3)

        assert limiter.can_send("Accra") is True

    def test_can_send_under_limit(self):
        limiter = RateLimiter(max_alerts=3)

        limiter.record_send("Accra")
        limiter.record_send("Accra")

        assert limiter.can_send("Accra") is True

    def test_cannot_send_at_limit(self):
        limiter = RateLimiter(max_alerts=3)

        limiter.record_send("Accra")
        limiter.record_send("Accra")
        limiter.record_send("Accra")

        assert limiter.can_send("Accra") is False

    def test_multiple_locations_are_independent(self):
        limiter = RateLimiter(max_alerts=2)

        limiter.record_send("Accra")
        limiter.record_send("Accra")

        assert limiter.can_send("Accra") is False
        assert limiter.can_send("Tema") is True

    def test_old_alerts_expire_after_one_hour(self):
        limiter = RateLimiter(max_alerts=2)

        old_time = datetime.now() - timedelta(hours=2)

        limiter.alerts["Accra"] = [old_time, old_time]

        assert limiter.can_send("Accra") is True

    def test_boundary_exactly_one_hour_old_expires(self):
        limiter = RateLimiter(max_alerts=1)

        exact_cutoff = datetime.now() - timedelta(hours=1)

        limiter.alerts["Accra"] = [exact_cutoff]

        assert limiter.can_send("Accra") is True

    def test_recent_alert_not_expired(self):
        limiter = RateLimiter(max_alerts=1)

        recent = datetime.now() - timedelta(minutes=59)

        limiter.alerts["Accra"] = [recent]

        assert limiter.can_send("Accra") is False


# ════════════════════════════════════════════════════════════════
# record_send()
# ════════════════════════════════════════════════════════════════


class TestRecordSend:
    def test_record_send_adds_timestamp(self):
        limiter = RateLimiter()

        limiter.record_send("Accra")

        assert len(limiter.alerts["Accra"]) == 1

    def test_record_send_multiple_entries(self):
        limiter = RateLimiter()

        limiter.record_send("Accra")
        limiter.record_send("Accra")

        assert len(limiter.alerts["Accra"]) == 2

    @patch("src.alerts.rate_limit.datetime")
    def test_record_send_uses_current_time(self, mock_datetime):
        limiter = RateLimiter()

        fake_now = datetime(2026, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = fake_now

        limiter.record_send("Accra")

        assert limiter.alerts["Accra"][0] == fake_now


# ════════════════════════════════════════════════════════════════
# get_remaining()
# ════════════════════════════════════════════════════════════════


class TestGetRemaining:
    def test_get_remaining_initial(self):
        limiter = RateLimiter(max_alerts=3)

        assert limiter.get_remaining("Accra") == 3

    def test_get_remaining_after_one_send(self):
        limiter = RateLimiter(max_alerts=3)

        limiter.record_send("Accra")

        assert limiter.get_remaining("Accra") == 2

    def test_get_remaining_at_limit(self):
        limiter = RateLimiter(max_alerts=2)

        limiter.record_send("Accra")
        limiter.record_send("Accra")

        assert limiter.get_remaining("Accra") == 0

    def test_get_remaining_never_negative(self):
        limiter = RateLimiter(max_alerts=1)

        limiter.record_send("Accra")
        limiter.record_send("Accra")
        limiter.record_send("Accra")

        assert limiter.get_remaining("Accra") == 0

    def test_get_remaining_ignores_old_entries(self):
        limiter = RateLimiter(max_alerts=2)

        old_time = datetime.now() - timedelta(hours=2)

        limiter.alerts["Accra"] = [old_time]

        assert limiter.get_remaining("Accra") == 2

    def test_get_remaining_counts_recent_entries_only(self):
        limiter = RateLimiter(max_alerts=3)

        old_time = datetime.now() - timedelta(hours=2)
        recent_time = datetime.now() - timedelta(minutes=30)

        limiter.alerts["Accra"] = [
            old_time,
            recent_time,
        ]

        assert limiter.get_remaining("Accra") == 2


# ════════════════════════════════════════════════════════════════
# CONCURRENCY-LIKE BEHAVIOR
# ════════════════════════════════════════════════════════════════


class TestConcurrencyBehavior:
    def test_repeated_calls_respect_limit(self):
        limiter = RateLimiter(max_alerts=3)

        for _ in range(3):
            assert limiter.can_send("Accra") is True
            limiter.record_send("Accra")

        assert limiter.can_send("Accra") is False

    def test_multiple_locations_do_not_interfere(self):
        limiter = RateLimiter(max_alerts=1)

        limiter.record_send("Accra")

        assert limiter.can_send("Accra") is False
        assert limiter.can_send("Tema") is True
        assert limiter.can_send("Kumasi") is True
