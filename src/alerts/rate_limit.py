"""Rate limiter for alerts to prevent spam."""

import time
from collections import defaultdict
from typing import Dict, List, Optional, Union
from datetime import datetime


class RateLimiter:
    """
    Rate limiter for alerts.

    Prevents excessive alerts to the same location within a time window.
    """

    def __init__(
        self,
        max_alerts_per_hour: int = 3,
        window_seconds: int = 3600,
        max_alerts: int = None,
    ):
        self.max_alerts = max_alerts if max_alerts is not None else max_alerts_per_hour
        self.window_seconds = window_seconds
        self.alerts: Dict[str, List[Union[float, datetime]]] = defaultdict(list)

    def _to_timestamp(self, value: Union[float, datetime]) -> float:
        """Convert datetime or timestamp to float timestamp."""
        if isinstance(value, datetime):
            return value.timestamp()
        return value

    def can_send(self, location: str) -> bool:
        """Check if an alert can be sent to a location."""
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds

        # Clean old alerts (keep only those within window)
        self.alerts[location] = [
            ts for ts in self.alerts[location] if self._to_timestamp(ts) > cutoff_time
        ]

        return len(self.alerts[location]) < self.max_alerts

    def record_send(self, location: str) -> None:
        """Record that an alert was sent."""
        self.alerts[location].append(time.time())

    def get_remaining(self, location: str) -> int:
        """Get remaining alerts allowed for a location."""
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds

        # Clean old alerts
        self.alerts[location] = [
            ts for ts in self.alerts[location] if self._to_timestamp(ts) > cutoff_time
        ]

        remaining = self.max_alerts - len(self.alerts[location])
        return max(0, remaining)

    def reset(self, location: Optional[str] = None) -> None:
        """Reset rate limits."""
        if location:
            self.alerts[location] = []
        else:
            self.alerts.clear()
