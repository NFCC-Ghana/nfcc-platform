"""Thread-safe rate limiter for alerts.

Counts live in Redis when a client is given, so the limit holds across
all uvicorn workers (4 per instance - see entrypoint.sh). In-memory
counts are per process, which let each worker send its own full quota.
Any Redis error falls back to the in-memory counts rather than blocking
or failing an alert.
"""

import logging
import time
import uuid
from collections import defaultdict
from threading import Lock
from typing import Dict, Tuple

logger = logging.getLogger("nfcc.alert.rate_limit")

KEY_PREFIX = "nfcc:ratelimit:"


class RateLimiter:
    """Thread-safe rate limiter for per-location alert throttling."""

    def __init__(
        self,
        limit: int = 3,
        window_seconds: int = 3600,
        max_alerts_per_hour: int = None,
        redis_client=None,
    ):
        """
        Initialize rate limiter.

        Args:
            limit: Maximum number of alerts per time window
            window_seconds: Time window in seconds (default 1 hour)
            max_alerts_per_hour: Legacy parameter for backward compatibility
            redis_client: Optional Redis client for counts shared across
                processes; None keeps counts in this process only
        """
        self.limit = limit if max_alerts_per_hour is None else max_alerts_per_hour
        self.max_alerts_per_hour = self.limit  # For backward compatibility
        self.window_seconds = window_seconds
        self._sends: Dict[str, list] = defaultdict(list)
        self._lock = Lock()
        self._redis = redis_client

    def _key(self, location: str) -> str:
        return f"{KEY_PREFIX}{location}"

    def _redis_count(self, location: str) -> int:
        """Sliding-window count from a Redis sorted set of send times."""
        key = self._key(location)
        window_start = time.time() - self.window_seconds
        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        return int(pipe.execute()[1])

    def can_send(self, location: str) -> Tuple[bool, int]:
        """Check if an alert can be sent to a location."""
        if self._redis is not None:
            try:
                remaining = self.limit - self._redis_count(location)
                return remaining > 0, max(0, remaining)
            except Exception as e:
                logger.warning(f"Redis rate limit check failed, using memory: {e}")
        with self._lock:
            now = time.time()
            window_start = now - self.window_seconds
            self._sends[location] = [
                t for t in self._sends[location] if t > window_start
            ]
            remaining = self.limit - len(self._sends[location])
            return remaining > 0, max(0, remaining)

    def record_send(self, location: str) -> None:
        """Record that an alert was sent to a location."""
        if self._redis is not None:
            try:
                key = self._key(location)
                now = time.time()
                pipe = self._redis.pipeline()
                pipe.zadd(key, {f"{now}:{uuid.uuid4().hex}": now})
                pipe.expire(key, self.window_seconds)
                pipe.execute()
                return
            except Exception as e:
                logger.warning(f"Redis rate limit record failed, using memory: {e}")
        with self._lock:
            self._sends[location].append(time.time())

    def get_remaining(self, location: str) -> int:
        """Get remaining alerts available for a location."""
        _, remaining = self.can_send(location)
        return remaining

    def reset(self, location: str = None) -> None:
        """Reset rate limit for a specific location or all locations."""
        if self._redis is not None:
            try:
                if location:
                    self._redis.delete(self._key(location))
                else:
                    for key in self._redis.scan_iter(f"{KEY_PREFIX}*"):
                        self._redis.delete(key)
            except Exception as e:
                logger.warning(f"Redis rate limit reset failed: {e}")
        with self._lock:
            if location:
                self._sends[location] = []
            else:
                self._sends.clear()
