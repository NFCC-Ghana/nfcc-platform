"""Rate limiter for alerts to prevent spam."""

import time
from collections import defaultdict
from typing import Dict, List, Optional


class RateLimiter:
    def __init__(
        self,
        max_alerts_per_hour: int = 3,
        window_seconds: int = 3600,
        max_alerts: int = None,
    ):
        self.max_alerts = max_alerts if max_alerts is not None else max_alerts_per_hour
        self.window_seconds = window_seconds
        self.alerts: Dict[str, List[float]] = defaultdict(list)

    def can_send(self, location: str) -> bool:
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds
        self.alerts[location] = [ts for ts in self.alerts[location] if ts > cutoff_time]
        return len(self.alerts[location]) < self.max_alerts

    def record_send(self, location: str) -> None:
        self.alerts[location].append(time.time())

    def get_remaining(self, location: str) -> int:
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds
        self.alerts[location] = [ts for ts in self.alerts[location] if ts > cutoff_time]
        return max(0, self.max_alerts - len(self.alerts[location]))
