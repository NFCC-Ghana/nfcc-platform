"""
Persistence layer for flood alerts using SQLite.

This module provides database operations for storing and retrieving flood alert data,
including initialization, insertion, history queries, and statistical analysis.
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

# Database file location
DB_PATH = Path(__file__).parent.parent.parent / "data" / "alerts.db"


@contextmanager
def get_db():
    """
    Context manager for database connections.

    Ensures proper connection handling and cleanup.
    Uses row factory to return rows as dictionaries for easier access.
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """
    Initialize the alerts database with table and indexes.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            location TEXT NOT NULL,
            risk_score REAL NOT NULL,
            risk_tier TEXT NOT NULL,
            alert_sent BOOLEAN NOT NULL,
            provider TEXT,
            message_id TEXT,
            error TEXT
        )
        """
        cursor.execute(create_table_sql)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_location ON alerts(location)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON alerts(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_risk_tier ON alerts(risk_tier)")

        conn.commit()


def save_alert(data_dict: Dict[str, Any]) -> int:
    """
    Save a new alert to the database.

    Args:
        data_dict: Dictionary containing alert data

    Returns:
        int: The ID of the inserted alert record
    """
    required_fields = ["timestamp", "location", "risk_score", "risk_tier", "alert_sent"]
    missing_fields = [field for field in required_fields if field not in data_dict]
    if missing_fields:
        raise ValueError(f"Missing required fields: {missing_fields}")

    with get_db() as conn:
        cursor = conn.cursor()

        insert_sql = """
        INSERT INTO alerts
        (timestamp, location, risk_score, risk_tier, alert_sent, provider, message_id, error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

        cursor.execute(
            insert_sql,
            (
                data_dict["timestamp"],
                data_dict["location"],
                data_dict["risk_score"],
                data_dict["risk_tier"],
                data_dict["alert_sent"],
                data_dict.get("provider"),
                data_dict.get("message_id"),
                data_dict.get("error"),
            ),
        )

        conn.commit()
        return cursor.lastrowid


def get_alert_history(
    limit: int = 100,
    offset: int = 0,
    location_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve alert history with pagination and optional location filtering.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        if location_filter:
            query_sql = """
            SELECT * FROM alerts
            WHERE location = ?
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """
            cursor.execute(query_sql, (location_filter, limit, offset))
        else:
            query_sql = """
            SELECT * FROM alerts
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """
            cursor.execute(query_sql, (limit, offset))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_total_alerts_count(location_filter: Optional[str] = None) -> int:
    """
    Get total number of alerts matching the filter.

    This function is used for pagination to provide the total count
    of available records, enabling frontend to calculate total pages.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        if location_filter:
            cursor.execute(
                "SELECT COUNT(*) FROM alerts WHERE location = ?", (location_filter,)
            )
        else:
            cursor.execute("SELECT COUNT(*) FROM alerts")
        return cursor.fetchone()[0]


def get_alert_stats() -> Dict[str, Any]:
    """
    Calculate comprehensive alert statistics.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Count alerts grouped by risk_tier
        cursor.execute(
            "SELECT risk_tier, COUNT(*) as count FROM alerts GROUP BY risk_tier"
        )
        by_risk_tier = {row[0]: row[1] for row in cursor.fetchall()}

        # Get top 5 locations with most alerts
        top_locations_query = """
        SELECT location, COUNT(*) as count FROM alerts
        GROUP BY location
        ORDER BY count DESC
        LIMIT 5
        """
        cursor.execute(top_locations_query)
        top_locations = [(row[0], row[1]) for row in cursor.fetchall()]

        return {
            "by_risk_tier": by_risk_tier,
            "top_locations": top_locations,
        }
