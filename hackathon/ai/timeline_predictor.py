"""Flood Timeline Predictor - Forecasts risk over 7 days."""

import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta

logger = logging.getLogger("hackathon.timeline")


class TimelinePredictor:
    """Predict flood risk over 1, 3, and 7 day horizons."""

    def __init__(self):
        pass

    def predict(
        self, current_risk: float, rainfall_forecast: List[float] = None
    ) -> Dict[str, float]:
        """Predict risk over time horizons."""
        if rainfall_forecast is None:
            # Simulate realistic decay
            rainfall_forecast = [
                current_risk * 0.8,
                current_risk * 0.6,
                current_risk * 0.4,
            ]

        # Day 1: immediate risk (closest to current)
        day1 = min(100, current_risk * 1.05)  # Slight adjustment for near-term

        # Day 3: medium-term (decay based on rainfall forecast)
        day3 = min(100, current_risk * 0.7 + rainfall_forecast[0] * 0.3)

        # Day 7: longer-term (more decay)
        day7 = min(
            100,
            current_risk * 0.4
            + rainfall_forecast[1] * 0.3
            + rainfall_forecast[2] * 0.3,
        )

        return {
            "day1": round(day1, 1),
            "day3": round(day3, 1),
            "day7": round(day7, 1),
        }

    def get_trend(self, timeline: Dict[str, float]) -> str:
        """Determine trend from timeline."""
        if timeline["day1"] > timeline["day3"] > timeline["day7"]:
            return "decreasing"
        elif timeline["day1"] < timeline["day3"] < timeline["day7"]:
            return "increasing"
        else:
            return "stable"

    def format_for_dashboard(
        self, timeline: Dict[str, float], trend: str
    ) -> List[Dict[str, Any]]:
        """Format timeline for dashboard chart."""
        dates = [
            datetime.now().strftime("%Y-%m-%d"),
            (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
            (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"),
            (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
        ]

        return [
            {"date": dates[0], "risk": timeline.get("day1", 0), "forecast": False},
            {"date": dates[1], "risk": timeline.get("day1", 0), "forecast": True},
            {"date": dates[2], "risk": timeline.get("day3", 0), "forecast": True},
            {"date": dates[3], "risk": timeline.get("day7", 0), "forecast": True},
        ]


# Singleton instance
timeline_predictor = TimelinePredictor()
