"""Database module for alerts and subscriptions."""

from .alert_db import (
    get_db,
    init_db,
    init_alerts_table,
    save_alert,
    get_alerts,
    get_alert_history,
    get_alert_stats,
)

__all__ = [
    "get_db",
    "init_db",
    "init_alerts_table",
    "save_alert",
    "get_alerts",
    "get_alert_history",
    "get_alert_stats",
]
