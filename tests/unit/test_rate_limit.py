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


class _FakeRedis:
    """Minimal sorted-set Redis stand-in; one instance = one shared server."""

    def __init__(self, fail=False):
        self.zsets = {}
        self.fail = fail

    def pipeline(self):
        return _FakePipeline(self)

    def delete(self, key):
        self.zsets.pop(key, None)

    def scan_iter(self, pattern):
        prefix = pattern.rstrip("*")
        return [k for k in list(self.zsets) if k.startswith(prefix)]


class _FakePipeline:
    def __init__(self, redis):
        self.redis = redis
        self.ops = []

    def zremrangebyscore(self, key, lo, hi):
        self.ops.append(("zrem", key, lo, hi))

    def zcard(self, key):
        self.ops.append(("zcard", key))

    def zadd(self, key, mapping):
        self.ops.append(("zadd", key, mapping))

    def expire(self, key, seconds):
        self.ops.append(("expire", key))

    def execute(self):
        if self.redis.fail:
            raise ConnectionError("redis down")
        out = []
        for op in self.ops:
            zset = self.redis.zsets.setdefault(op[1], {})
            if op[0] == "zrem":
                for m in [m for m, s in zset.items() if op[2] <= s <= op[3]]:
                    del zset[m]
                out.append(None)
            elif op[0] == "zcard":
                out.append(len(zset))
            elif op[0] == "zadd":
                zset.update(op[2])
                out.append(1)
            else:
                out.append(True)
        return out


class TestRedisBackedLimit:
    """Counts shared through Redis hold across separate worker processes."""

    def test_limit_shared_across_instances(self):
        redis = _FakeRedis()
        worker_a = RateLimiter(limit=2, redis_client=redis)
        worker_b = RateLimiter(limit=2, redis_client=redis)
        worker_a.record_send("Accra")
        worker_b.record_send("Accra")
        assert worker_a.can_send("Accra") == (False, 0)
        assert worker_b.can_send("Accra") == (False, 0)
        assert worker_a.can_send("Tema") == (True, 2)

    def test_old_sends_expire_from_window(self):
        redis = _FakeRedis()
        limiter = RateLimiter(limit=1, window_seconds=3600, redis_client=redis)
        redis.zsets["nfcc:ratelimit:Accra"] = {"old": time.time() - 7200}
        assert limiter.can_send("Accra") == (True, 1)

    def test_reset_clears_shared_counts(self):
        redis = _FakeRedis()
        limiter = RateLimiter(limit=1, redis_client=redis)
        limiter.record_send("Accra")
        limiter.record_send("Tema")
        limiter.reset("Accra")
        assert limiter.get_remaining("Accra") == 1
        assert limiter.get_remaining("Tema") == 0
        limiter.reset()
        assert limiter.get_remaining("Tema") == 1

    def test_falls_back_to_memory_when_redis_fails(self):
        limiter = RateLimiter(limit=1, redis_client=_FakeRedis(fail=True))
        assert limiter.can_send("Accra") == (True, 1)
        limiter.record_send("Accra")
        assert limiter.can_send("Accra") == (False, 0)
