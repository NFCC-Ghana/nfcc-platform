"""Rate limiting for alerts to prevent spam."""

from collections import defaultdict
from datetime import datetime, timedelta
import threading


class RateLimiter:
    """Rate limiter for alerts per location."""

    def __init__(self, max_alerts_per_hour: int = 3):
        self.max_alerts_per_hour = max_alerts_per_hour
        self._history = defaultdict(list)
        self._lock = threading.Lock()

    def can_send(self, location: str) -> bool:
        """Check if an alert can be sent to this location."""
        with self._lock:
            now = datetime.now()
            cutoff = now - timedelta(hours=1)
            self._history[location] = [
                ts for ts in self._history[location] if ts > cutoff
            ]
            return len(self._history[location]) < self.max_alerts_per_hour

    def record_send(self, location: str):
        """Record that an alert was sent."""
        with self._lock:
            self._history[location].append(datetime.now())

    def get_remaining(self, location: str) -> int:
        """Get remaining alerts allowed for this hour."""
        with self._lock:
            now = datetime.now()
            cutoff = now - timedelta(hours=1)
            recent = [ts for ts in self._history[location] if ts > cutoff]
            return max(0, self.max_alerts_per_hour - len(recent))
