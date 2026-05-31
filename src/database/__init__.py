"""Database module for flood alerts persistence."""

from .alert_db import (
    init_db,
    init_subscriptions_table,
    save_alert,
    get_alert_history,
    get_alert_stats,
    subscribe,
    unsubscribe,
    delete_subscription,
    get_subscription,
    get_all_subscriptions,
    get_subscriptions_for_location,
)

__all__ = [
    "init_db",
    "init_subscriptions_table",
    "save_alert",
    "get_alert_history",
    "get_alert_stats",
    "subscribe",
    "unsubscribe",
    "delete_subscription",
    "get_subscription",
    "get_all_subscriptions",
    "get_subscriptions_for_location",
]
