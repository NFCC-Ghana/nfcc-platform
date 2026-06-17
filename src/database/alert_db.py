"""Alert database module - stores and retrieves flood alerts."""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

DB_PATH = Path("data/alerts.db")

def get_db_connection() -> sqlite3.Connection:
    """Get database connection with row factory."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database schema with proper columns."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Drop existing table to recreate with correct schema
    cursor.execute("DROP TABLE IF EXISTS alerts")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_id TEXT UNIQUE NOT NULL,
            district TEXT NOT NULL,
            community TEXT,
            risk_score REAL NOT NULL,
            risk_tier TEXT NOT NULL,
            message TEXT,
            timestamp TEXT NOT NULL,
            sent_to TEXT,
            provider TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_alerts_district ON alerts(district)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)
    """)
    
    conn.commit()
    conn.close()
    logger.info("Alert database initialized with correct schema")

def save_alert(alert_data: Dict) -> str:
    """Save an alert to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    alert_id = alert_data.get('alert_id') or f"ALT_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    cursor.execute("""
        INSERT OR REPLACE INTO alerts (
            alert_id, district, community, risk_score, risk_tier, 
            message, timestamp, sent_to, provider, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        alert_id,
        alert_data.get('district', 'Unknown'),
        alert_data.get('community', ''),
        alert_data.get('risk_score', 0.0),
        alert_data.get('risk_tier', 'LOW'),
        alert_data.get('message', ''),
        alert_data.get('timestamp', datetime.now().isoformat()),
        json.dumps(alert_data.get('sent_to', [])),
        alert_data.get('provider', 'unknown'),
        json.dumps(alert_data.get('metadata', {}))
    ))
    
    conn.commit()
    conn.close()
    return alert_id

def get_alert_history(district: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict]:
    """Get alert history from database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM alerts"
    params = []
    
    if district:
        query += " WHERE district = ?"
        params.append(district)
    
    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_alert_stats(district: Optional[str] = None) -> Dict:
    """Get alert statistics."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT risk_tier, COUNT(*) as count FROM alerts"
    params = []
    
    if district:
        query += " WHERE district = ?"
        params.append(district)
    
    query += " GROUP BY risk_tier"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    stats = {row['risk_tier']: row['count'] for row in rows}
    
    # Get top locations
    cursor = conn.cursor()
    query = "SELECT district, COUNT(*) as count FROM alerts"
    if district:
        query += " WHERE district = ?"
    query += " GROUP BY district ORDER BY count DESC LIMIT 5"
    
    cursor.execute(query, params if district else [])
    top_locations = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {
        'risk_tiers': stats,
        'top_locations': top_locations,
        'total': sum(stats.values())
    }

def get_total_alerts() -> int:
    """Get total number of alerts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM alerts")
    count = cursor.fetchone()[0]
    conn.close()
    return count

# Initialize database on import
init_db()
