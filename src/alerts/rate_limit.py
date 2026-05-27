"""Thread-safe rate limiter for alerts."""

import time
from collections import defaultdict
from threading import Lock
from typing import Dict, Tuple


class RateLimiter:
    """Thread-safe rate limiter for per-location alert throttling."""
    
    def __init__(self, limit: int = 3, window_seconds: int = 3600, max_alerts_per_hour: int = None):
        """
        Initialize rate limiter.
        
        Args:
            limit: Maximum number of alerts per time window
            window_seconds: Time window in seconds (default 1 hour)
            max_alerts_per_hour: Legacy parameter for backward compatibility
        """
        self.limit = limit if max_alerts_per_hour is None else max_alerts_per_hour
        self.max_alerts_per_hour = self.limit  # For backward compatibility
        self.window_seconds = window_seconds
        self._sends: Dict[str, list] = defaultdict(list)
        self._lock = Lock()
    
    def can_send(self, location: str) -> Tuple[bool, int]:
        """Check if an alert can be sent to a location."""
        with self._lock:
            now = time.time()
            window_start = now - self.window_seconds
            self._sends[location] = [t for t in self._sends[location] if t > window_start]
            remaining = self.limit - len(self._sends[location])
            return remaining > 0, max(0, remaining)
    
    def record_send(self, location: str) -> None:
        """Record that an alert was sent to a location."""
        with self._lock:
            self._sends[location].append(time.time())
    
    def get_remaining(self, location: str) -> int:
        """Get remaining alerts available for a location."""
        _, remaining = self.can_send(location)
        return remaining
    
    def reset(self, location: str = None) -> None:
        """Reset rate limit for a specific location or all locations."""
        with self._lock:
            if location:
                self._sends[location] = []
            else:
                self._sends.clear()
