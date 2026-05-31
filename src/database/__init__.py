"""Database module for flood alerts persistence."""

from .alert_db import init_db, save_alert, get_alert_history, get_alert_stats

__all__ = ["init_db", "save_alert", "get_alert_history", "get_alert_stats"]
