"""Metrics validation utilities."""

from typing import Dict, Any, Optional
from collections import defaultdict


class MetricsValidator:
    """Validate metric emissions."""

    def __init__(self):
        self.metrics: Dict[str, list] = defaultdict(list)
        self.snapshots: Dict[str, Dict[str, Any]] = {}

    def record(
        self, metric_name: str, value: Any, tags: Optional[Dict[str, str]] = None
    ):
        """Record a metric value."""
        self.metrics[metric_name].append(
            {
                "value": value,
                "tags": tags or {},
                "timestamp": None,  # Would use time.time() in production
            }
        )

    def snapshot(self, name: str):
        """Take a snapshot of current metrics."""
        self.snapshots[name] = {
            metric: len(values) for metric, values in self.metrics.items()
        }

    def assert_increased(self, metric_name: str, from_snapshot: str, to_snapshot: str):
        """Assert metric increased between snapshots."""
        from_count = self.snapshots.get(from_snapshot, {}).get(metric_name, 0)
        to_count = self.snapshots.get(to_snapshot, {}).get(metric_name, 0)
        assert (
            to_count > from_count
        ), f"Metric {metric_name} did not increase: {from_count} -> {to_count}"

    def assert_count(self, metric_name: str, expected_count: int):
        """Assert specific count of metric emissions."""
        count = len(self.metrics.get(metric_name, []))
        assert count == expected_count, f"Expected {expected_count}, got {count}"

    def get_counter(self, metric_name: str) -> int:
        """Get counter value."""
        return len(self.metrics.get(metric_name, []))

    def reset(self):
        """Reset all metrics."""
        self.metrics.clear()
        self.snapshots.clear()
