"""
Persistence layer for flood alerts using SQLite.

This module provides database operations for storing and retrieving flood alert data,
including initialization, insertion, history queries, and statistical analysis.
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
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
    
    Creates the alerts table with the following columns:
    - id: Unique identifier (primary key)
    - timestamp: When the alert was generated (ISO format string)
    - location: Geographic location of the alert
    - risk_score: Numerical risk assessment (0-100 or similar scale)
    - risk_tier: Categorical risk level (e.g., 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL')
    - alert_sent: Whether the alert was successfully sent (boolean)
    - provider: Alert delivery provider (e.g., 'email', 'sms', 'push')
    - message_id: External identifier from the delivery provider
    - error: Any error message if alert delivery failed
    
    Creates indexes on frequently queried columns for performance optimization.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Create alerts table with comprehensive schema
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
        
        # Create indexes for optimized query performance
        # Index on location for geographic filtering
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_location ON alerts(location)")
        
        # Index on timestamp for time-based queries and sorting
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON alerts(timestamp)")
        
        # Index on risk_tier for risk-level filtering
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_risk_tier ON alerts(risk_tier)")
        
        conn.commit()


def save_alert(data_dict: Dict[str, Any]) -> int:
    """
    Save a new alert to the database.
    
    Args:
        data_dict: Dictionary containing alert data with expected keys:
            - timestamp (str): ISO format timestamp when alert was created
            - location (str): Geographic location identifier
            - risk_score (float): Numerical risk score
            - risk_tier (str): Risk level category
            - alert_sent (bool): Whether alert was sent successfully
            - provider (str, optional): Delivery provider name
            - message_id (str, optional): External message identifier
            - error (str, optional): Error message if alert failed
    
    Returns:
        int: The ID of the inserted alert record
    
    Raises:
        sqlite3.IntegrityError: If required fields are missing or invalid
        ValueError: If data_dict is missing required fields
    """
    # Validate required fields
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
        
        # Return the ID of the inserted record
        return cursor.lastrowid


def get_alert_history(
    limit: int = 100,
    offset: int = 0,
    location_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve alert history with pagination and optional location filtering.
    
    Fetches alerts ordered by timestamp in descending order (most recent first),
    supporting pagination for efficient data retrieval and optional geographic filtering.
    
    Args:
        limit (int): Maximum number of alerts to return (default: 100)
        offset (int): Number of alerts to skip for pagination (default: 0)
        location_filter (str, optional): If provided, only return alerts from this location
    
    Returns:
        List[Dict[str, Any]]: List of alert records as dictionaries with keys:
            - id, timestamp, location, risk_score, risk_tier, alert_sent, 
              provider, message_id, error
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Build query with optional location filter
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
        
        # Convert Row objects to dictionaries for consistent return type
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_alert_stats() -> Dict[str, Any]:
    """
    Calculate comprehensive alert statistics.
    
    Returns aggregated alert data including:
    - Count of alerts grouped by risk tier
    - Top 5 locations with the most alerts
    
    Returns:
        Dict[str, Any]: Statistics dictionary with keys:
            - 'by_risk_tier': Dict mapping risk tier to alert count
            - 'top_locations': List of tuples (location, count) for top 5 locations
    
    Example return value:
        {
            'by_risk_tier': {'LOW': 45, 'MEDIUM': 32, 'HIGH': 8, 'CRITICAL': 2},
            'top_locations': [('Accra', 25), ('Kumasi', 18), ('Tema', 14), ...]
        }
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Query 1: Count alerts grouped by risk_tier
        risk_tier_query = "SELECT risk_tier, COUNT(*) as count FROM alerts GROUP BY risk_tier"
        cursor.execute(risk_tier_query)
        by_risk_tier = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Query 2: Get top 5 locations with most alerts
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
