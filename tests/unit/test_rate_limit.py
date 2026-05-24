"""Tests for rate limiter."""

import time
import threading
from src.alerts.rate_limit import RateLimiter


class TestRateLimiterInitialization:
    """Test rate limiter initialization."""

    def test_default_limit(self):
        limiter = RateLimiter()
        assert limiter.max_alerts_per_hour == 3

    def test_custom_limit(self):
        limiter = RateLimiter(max_alerts_per_hour=5)
        assert limiter.max_alerts_per_hour == 5


class TestCanSend:
    """Test can_send() method."""

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

    def test_multiple_locations_are_independent(self):
        limiter = RateLimiter(max_alerts_per_hour=1)
        limiter.record_send("loc1")
        assert limiter.can_send("loc1") is False
        assert limiter.can_send("loc2") is True

    def test_old_alerts_expire_after_window(self):
        """Test that alerts expire after the time window."""
        limiter = RateLimiter(max_alerts_per_hour=1, window_seconds=1)

        limiter.record_send("Accra")
        assert limiter.can_send("Accra") is False

        # Wait for window to expire
        time.sleep(1.1)

        assert limiter.can_send("Accra") is True


class TestRecordSend:
    """Test record_send() method."""

    def test_record_send_adds_timestamp(self):
        limiter = RateLimiter(max_alerts_per_hour=2)
        limiter.record_send("Accra")
        assert len(limiter.alerts["Accra"]) == 1

    def test_record_send_multiple_entries(self):
        limiter = RateLimiter(max_alerts_per_hour=3)
        limiter.record_send("Accra")
        limiter.record_send("Accra")
        assert len(limiter.alerts["Accra"]) == 2


class TestGetRemaining:
    """Test get_remaining() method."""

    def test_get_remaining_initial(self):
        limiter = RateLimiter(max_alerts_per_hour=3)
        assert limiter.get_remaining("test") == 3

    def test_get_remaining_after_one_send(self):
        limiter = RateLimiter(max_alerts_per_hour=3)
        limiter.record_send("test")
        assert limiter.get_remaining("test") == 2

    def test_get_remaining_at_limit(self):
        limiter = RateLimiter(max_alerts_per_hour=2)
        limiter.record_send("test")
        limiter.record_send("test")
        assert limiter.get_remaining("test") == 0

    def test_get_remaining_never_negative(self):
        limiter = RateLimiter(max_alerts_per_hour=1)
        limiter.record_send("test")
        limiter.record_send("test")  # This will add but we're checking remaining
        # After 2 records, should still be 0 remaining (can't go negative)
        assert limiter.get_remaining("test") == 0


class TestReset:
    """Test reset() method."""

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


class TestConcurrencyBehavior:
    """Test concurrency safety."""

    def test_repeated_calls_respect_limit(self):
        limiter = RateLimiter(max_alerts_per_hour=3)
        results = []

        def send_alerts():
            for _ in range(5):
                if limiter.can_send("test"):
                    limiter.record_send("test")
                    results.append(True)
                else:
                    results.append(False)

        threads = [threading.Thread(target=send_alerts) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have exactly 3 successful sends total (not more)
        assert sum(results) <= 3

    def test_multiple_locations_do_not_interfere(self):
        limiter = RateLimiter(max_alerts_per_hour=1)
        results = {"loc1": [], "loc2": []}

        def send_to_loc1():
            for _ in range(3):
                if limiter.can_send("loc1"):
                    limiter.record_send("loc1")
                    results["loc1"].append(True)
                else:
                    results["loc1"].append(False)

        def send_to_loc2():
            for _ in range(3):
                if limiter.can_send("loc2"):
                    limiter.record_send("loc2")
                    results["loc2"].append(True)
                else:
                    results["loc2"].append(False)

        t1 = threading.Thread(target=send_to_loc1)
        t2 = threading.Thread(target=send_to_loc2)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Each location should have exactly 1 successful send
        assert sum(results["loc1"]) == 1
        assert sum(results["loc2"]) == 1
