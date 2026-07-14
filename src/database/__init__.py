"""Database module for flood alerts persistence."""

from .alert_db import get_alert_history, get_alert_stats, init_db, save_alert

__all__ = ["init_db", "save_alert", "get_alert_history", "get_alert_stats"]
