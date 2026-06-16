"""Database module for alerts and subscriptions."""

from .alert_db import (
    get_db,
    init_db,
    init_alerts_table,
    init_subscriptions_table,
    save_alert,
    get_alerts,
    get_alert_history,
    get_alert_stats,
    subscribe,
    unsubscribe,
    get_subscription,
    get_all_subscriptions,
    get_subscriptions_for_location,
    update_subscription,
    delete_subscription,
)

__all__ = [
    "get_db",
    "init_db",
    "init_alerts_table",
    "init_subscriptions_table",
    "save_alert",
    "get_alerts",
    "get_alert_history",
    "get_alert_stats",
    "subscribe",
    "unsubscribe",
    "get_subscription",
    "get_all_subscriptions",
    "get_subscriptions_for_location",
    "update_subscription",
    "delete_subscription",
]
