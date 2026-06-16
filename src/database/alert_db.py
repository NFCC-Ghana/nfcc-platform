"""Database operations for alerts and subscriptions."""

import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
from datetime import datetime
import secrets

DB_PATH = Path(__file__).parent.parent.parent / "data" / "alerts.db"

@contextmanager
def get_db():
    """Get a thread-safe database connection."""
    # Use check_same_thread=False to allow multi-threaded access
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# Rest of the file remains the same...

def init_db() -> None:
    """
    Initialize the database with all tables.
    Creates alerts and subscriptions tables.
    """
    init_alerts_table()
    init_subscriptions_table()

def init_alerts_table() -> None:
    """
    Initialize the alerts table for storing alert history.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location TEXT NOT NULL,
                score REAL NOT NULL,
                risk_tier TEXT NOT NULL,
                precipitation REAL NOT NULL,
                alert_sent BOOLEAN DEFAULT 0,
                timestamp TEXT NOT NULL,
                provider TEXT,
                recipient TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_location ON alerts(location)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)")
        conn.commit()

# ============================================================
# Subscription Management Functions
# ============================================================

def init_subscriptions_table() -> None:
    """
    Initialize the subscriptions table for managing user alert subscriptions.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                phone TEXT,
                preferred_provider TEXT NOT NULL DEFAULT 'email',
                location_filter TEXT,
                min_risk_tier TEXT NOT NULL DEFAULT 'MODERATE',
                active BOOLEAN NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                unsubscribe_token TEXT UNIQUE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscription_email ON subscriptions(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscription_active ON subscriptions(active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscription_location ON subscriptions(location_filter)")
        conn.commit()


def subscribe(data_dict: Dict[str, Any]) -> int:
    """
    Create a new subscription.
    
    Args:
        data_dict: Dictionary with subscription data
        
    Returns:
        int: The ID of the created subscription
    """
    now = datetime.now().isoformat()
    token = secrets.token_urlsafe(16)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO subscriptions (
                email, phone, preferred_provider, location_filter,
                min_risk_tier, active, created_at, updated_at, unsubscribe_token
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data_dict.get("email"),
            data_dict.get("phone"),
            data_dict.get("preferred_provider", "email"),
            data_dict.get("location_filter"),
            data_dict.get("min_risk_tier", "MODERATE"),
            1,
            now,
            now,
            token
        ))
        conn.commit()
        return cursor.lastrowid


def unsubscribe(email: str) -> bool:
    """
    Unsubscribe a user by marking their subscription as inactive.
    
    Args:
        email: Email address to unsubscribe
        
    Returns:
        bool: True if subscription was found and deactivated
    """
    now = datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE subscriptions SET active = 0, updated_at = ? WHERE email = ?",
            (now, email)
        )
        conn.commit()
        return cursor.rowcount > 0


def get_subscription(email: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a subscription by email address.
    
    Args:
        email: Email address to look up
        
    Returns:
        dict or None: Subscription data or None if not found
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subscriptions WHERE email = ?", (email,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_all_subscriptions(active_only: bool = True) -> List[Dict[str, Any]]:
    """
    Retrieve all subscriptions, optionally filtered by active status.
    
    Args:
        active_only: If True, only return active subscriptions
        
    Returns:
        List of subscription records as dictionaries
    """
    with get_db() as conn:
        cursor = conn.cursor()
        if active_only:
            cursor.execute("SELECT * FROM subscriptions WHERE active = 1 ORDER BY created_at DESC")
        else:
            cursor.execute("SELECT * FROM subscriptions ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]


def get_subscriptions_for_location(location: str, active_only: bool = True) -> List[Dict[str, Any]]:
    """
    Retrieve subscriptions for a specific location.
    
    Args:
        location: Location to filter by
        active_only: If True, only return active subscriptions
        
    Returns:
        List of matching subscription records
    """
    with get_db() as conn:
        cursor = conn.cursor()
        if active_only:
            cursor.execute("""
                SELECT * FROM subscriptions
                WHERE (location_filter = ? OR location_filter IS NULL)
                AND active = 1
                ORDER BY created_at DESC
            """, (location,))
        else:
            cursor.execute("""
                SELECT * FROM subscriptions
                WHERE location_filter = ? OR location_filter IS NULL
                ORDER BY created_at DESC
            """, (location,))
        return [dict(row) for row in cursor.fetchall()]


def update_subscription(email: str, updates: Dict[str, Any]) -> bool:
    """
    Update a subscription with provided fields.
    
    Args:
        email: Email of the subscription to update
        updates: Dictionary of fields to update
        
    Returns:
        bool: True if successful, False if not found
    """
    if not updates:
        return True
    
    now = datetime.now().isoformat()
    set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
    values = list(updates.values())
    values.append(now)
    values.append(email)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE subscriptions SET {set_clause}, updated_at = ? WHERE email = ?",
            values
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_subscription(email: str) -> bool:
    """
    Permanently delete a subscription record.
    
    Args:
        email: Email address to delete
        
    Returns:
        bool: True if found and deleted
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM subscriptions WHERE email = ?", (email,))
        conn.commit()
        return cursor.rowcount > 0

def save_alert(location: str, score: float, risk_tier: str, 
               precipitation: float, alert_sent: bool = False,
               provider: str = None, recipient: str = None) -> int:
    """
    Save an alert to the database.
    
    Args:
        location: District location
        score: Risk score (0-100)
        risk_tier: Risk tier (LOW, MODERATE, HIGH, CRITICAL, EXTREME)
        precipitation: Rainfall in mm
        alert_sent: Whether an alert was sent
        provider: Provider used (email, sms, whatsapp)
        recipient: Recipient address
        
    Returns:
        int: The ID of the saved alert
    """
    now = datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO alerts (
                location, score, risk_tier, precipitation,
                alert_sent, timestamp, provider, recipient
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (location, score, risk_tier, precipitation, alert_sent, now, provider, recipient))
        conn.commit()
        return cursor.lastrowid

# ============================================================
# Alert Saving Functions
# ============================================================

def save_alert(location: str, score: float, risk_tier: str, 
               precipitation: float, alert_sent: bool = False,
               provider: str = None, recipient: str = None) -> int:
    """
    Save an alert to the database.
    
    Args:
        location: District location
        score: Risk score (0-100)
        risk_tier: Risk tier (LOW, MODERATE, HIGH, CRITICAL, EXTREME)
        precipitation: Rainfall in mm
        alert_sent: Whether an alert was sent
        provider: Provider used (email, sms, whatsapp)
        recipient: Recipient address
        
    Returns:
        int: The ID of the saved alert
    """
    from datetime import datetime
    now = datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO alerts (
                location, score, risk_tier, precipitation,
                alert_sent, timestamp, provider, recipient
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (location, score, risk_tier, precipitation, alert_sent, now, provider, recipient))
        conn.commit()
        return cursor.lastrowid


def get_alerts(location: str = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Retrieve alerts with optional filtering.
    
    Args:
        location: Filter by location
        limit: Maximum number of alerts to return
        offset: Number of alerts to skip
        
    Returns:
        List of alert records
    """
    with get_db() as conn:
        cursor = conn.cursor()
        if location:
            cursor.execute(
                "SELECT * FROM alerts WHERE location = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (location, limit, offset)
            )
        else:
            cursor.execute(
                "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
        return [dict(row) for row in cursor.fetchall()]


def get_alert_stats() -> Dict[str, Any]:
    """
    Get statistics about alerts.
    
    Returns:
        Dictionary with alert statistics
    """
    with get_db() as conn:
        cursor = conn.cursor()
        # Total alerts
        cursor.execute("SELECT COUNT(*) as total FROM alerts")
        total = cursor.fetchone()["total"]
        
        # By risk tier
        cursor.execute("""
            SELECT risk_tier, COUNT(*) as count 
            FROM alerts 
            GROUP BY risk_tier
            ORDER BY count DESC
        """)
        by_tier = {row["risk_tier"]: row["count"] for row in cursor.fetchall()}
        
        # Top locations
        cursor.execute("""
            SELECT location, COUNT(*) as count 
            FROM alerts 
            GROUP BY location 
            ORDER BY count DESC 
            LIMIT 10
        """)
        top_locations = [dict(row) for row in cursor.fetchall()]
        
        return {
            "total_alerts": total,
            "by_risk_tier": by_tier,
            "top_locations": top_locations
        }


# ============================================================
# Subscription Management Functions
# ============================================================

def init_subscriptions_table() -> None:
    """
    Initialize the subscriptions table for managing user alert subscriptions.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                phone TEXT,
                preferred_provider TEXT NOT NULL DEFAULT 'email',
                location_filter TEXT,
                min_risk_tier TEXT NOT NULL DEFAULT 'MODERATE',
                active BOOLEAN NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                unsubscribe_token TEXT UNIQUE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscription_email ON subscriptions(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscription_active ON subscriptions(active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscription_location ON subscriptions(location_filter)")
        conn.commit()


def subscribe(data_dict: Dict[str, Any]) -> int:
    """
    Create a new subscription.
    
    Args:
        data_dict: Dictionary with subscription data
        
    Returns:
        int: The ID of the created subscription
    """
    from datetime import datetime
    import secrets
    
    now = datetime.now().isoformat()
    token = secrets.token_urlsafe(16)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO subscriptions (
                email, phone, preferred_provider, location_filter,
                min_risk_tier, active, created_at, updated_at, unsubscribe_token
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data_dict.get("email"),
            data_dict.get("phone"),
            data_dict.get("preferred_provider", "email"),
            data_dict.get("location_filter"),
            data_dict.get("min_risk_tier", "MODERATE"),
            1,
            now,
            now,
            token
        ))
        conn.commit()
        return cursor.lastrowid


def unsubscribe(email: str) -> bool:
    """
    Unsubscribe a user by marking their subscription as inactive.
    
    Args:
        email: Email address to unsubscribe
        
    Returns:
        bool: True if subscription was found and deactivated
    """
    from datetime import datetime
    now = datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE subscriptions SET active = 0, updated_at = ? WHERE email = ?",
            (now, email)
        )
        conn.commit()
        return cursor.rowcount > 0


def get_subscription(email: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a subscription by email address.
    
    Args:
        email: Email address to look up
        
    Returns:
        dict or None: Subscription data or None if not found
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subscriptions WHERE email = ?", (email,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_all_subscriptions(active_only: bool = True) -> List[Dict[str, Any]]:
    """
    Retrieve all subscriptions, optionally filtered by active status.
    
    Args:
        active_only: If True, only return active subscriptions
        
    Returns:
        List of subscription records as dictionaries
    """
    with get_db() as conn:
        cursor = conn.cursor()
        if active_only:
            cursor.execute("SELECT * FROM subscriptions WHERE active = 1 ORDER BY created_at DESC")
        else:
            cursor.execute("SELECT * FROM subscriptions ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]


def get_subscriptions_for_location(location: str, active_only: bool = True) -> List[Dict[str, Any]]:
    """
    Retrieve subscriptions for a specific location.
    
    Args:
        location: Location to filter by
        active_only: If True, only return active subscriptions
        
    Returns:
        List of matching subscription records
    """
    with get_db() as conn:
        cursor = conn.cursor()
        if active_only:
            cursor.execute("""
                SELECT * FROM subscriptions
                WHERE (location_filter = ? OR location_filter IS NULL)
                AND active = 1
                ORDER BY created_at DESC
            """, (location,))
        else:
            cursor.execute("""
                SELECT * FROM subscriptions
                WHERE location_filter = ? OR location_filter IS NULL
                ORDER BY created_at DESC
            """, (location,))
        return [dict(row) for row in cursor.fetchall()]


def update_subscription(email: str, updates: Dict[str, Any]) -> bool:
    """
    Update a subscription with provided fields.
    
    Args:
        email: Email of the subscription to update
        updates: Dictionary of fields to update
        
    Returns:
        bool: True if successful, False if not found
    """
    from datetime import datetime
    if not updates:
        return True
    
    now = datetime.now().isoformat()
    set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
    values = list(updates.values())
    values.append(now)
    values.append(email)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE subscriptions SET {set_clause}, updated_at = ? WHERE email = ?",
            values
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_subscription(email: str) -> bool:
    """
    Permanently delete a subscription record.
    
    Args:
        email: Email address to delete
        
    Returns:
        bool: True if found and deleted
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM subscriptions WHERE email = ?", (email,))
        conn.commit()
        return cursor.rowcount > 0

def get_alert_history(location: str = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Get alert history with optional location filtering.
    Alias for get_alerts for backward compatibility.
    
    Args:
        location: Filter by location
        limit: Maximum number of alerts to return
        offset: Number of alerts to skip
        
    Returns:
        List of alert records
    """
    return get_alerts(location=location, limit=limit, offset=offset)
