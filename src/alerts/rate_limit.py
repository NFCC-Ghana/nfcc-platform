"""Rate limiting for alerts to prevent spam."""

from collections import defaultdict
import time
import threading
from typing import Dict, List, Optional


class RateLimiter:
    """Thread-safe rate limiter for alerts per location."""

    def __init__(self, max_alerts_per_hour: int = 3, window_seconds: int = 3600):
        """
        Initialize rate limiter.

        Args:
            max_alerts_per_hour: Maximum alerts allowed per location per hour
            window_seconds: Time window in seconds (default 1 hour = 3600 seconds)
        """
        self.max_alerts_per_hour = max_alerts_per_hour
        self.window_seconds = window_seconds
        self.alerts: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def can_send(self, location: str) -> bool:
        """
        Check whether an alert can be sent to this location.

        This method checks the rate limit but does NOT record the send.
        The caller must call record_send() after successful dispatch.
        """
        with self._lock:
            self._prune_old_entries(location)
            return len(self.alerts[location]) < self.max_alerts_per_hour

    def record_send(self, location: str) -> None:
        """Record that an alert was sent."""
        with self._lock:
            self.alerts[location].append(time.time())

    def get_remaining(self, location: str) -> int:
        """Get remaining alerts allowed for this hour."""
        with self._lock:
            self._prune_old_entries(location)
            remaining = self.max_alerts_per_hour - len(self.alerts[location])
            return max(0, remaining)

    def reset(self, location: Optional[str] = None) -> None:
        """Reset rate limiter state (useful for testing)."""
        with self._lock:
            if location:
                self.alerts[location] = []
            else:
                self.alerts.clear()

    def _prune_old_entries(self, location: str):
        """Remove expired timestamps."""
        cutoff = time.time() - self.window_seconds
        self.alerts[location] = [ts for ts in self.alerts[location] if ts > cutoff]
