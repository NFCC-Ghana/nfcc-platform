"""Community subscription management for alerts."""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SubscriptionManager:
    """Manage community subscriptions for flood alerts."""

    def __init__(self, db_path: str = "data/subscriptions.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info("Subscription Manager initialized")

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("DROP TABLE IF EXISTS subscriptions")

        cursor.execute("""
            CREATE TABLE subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number VARCHAR(20) UNIQUE NOT NULL,
                whatsapp_verified BOOLEAN DEFAULT FALSE,
                sms_verified BOOLEAN DEFAULT FALSE,
                email VARCHAR(100),
                district VARCHAR(100) NOT NULL,
                alert_level VARCHAR(20) DEFAULT 'MODERATE',
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_subscriptions_phone 
            ON subscriptions(phone_number)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_subscriptions_district 
            ON subscriptions(district)
        """)

        conn.commit()
        conn.close()
        logger.info("Subscription database initialized")

    def subscribe(self, phone: str, district: str, channel: str = "whatsapp") -> Dict:
        """Subscribe a user to alerts."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM subscriptions WHERE phone_number = ?", (phone,))
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                """
                UPDATE subscriptions 
                SET district = ?,
                    updated_at = CURRENT_TIMESTAMP,
                    active = TRUE
                WHERE phone_number = ?
            """,
                (district, phone),
            )
        else:
            cursor.execute(
                """
                INSERT INTO subscriptions (phone_number, district)
                VALUES (?, ?)
            """,
                (phone, district),
            )

        conn.commit()
        conn.close()

        return {
            "status": "subscribed",
            "phone": phone,
            "district": district,
            "channel": channel,
        }

    def unsubscribe(self, phone: str) -> Dict:
        """Unsubscribe a user."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE subscriptions SET active = FALSE WHERE phone_number = ?", (phone,)
        )

        conn.commit()
        conn.close()

        return {"status": "unsubscribed", "phone": phone}

    def get_subscribers(self, district: str, alert_level: str = None) -> List[str]:
        """Get all subscribers for a district."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        query = """
            SELECT phone_number FROM subscriptions 
            WHERE active = TRUE AND district = ?
        """
        params = [district]

        if alert_level:
            query += " AND alert_level <= ?"
            params.append(alert_level)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [row[0] for row in rows]

    def get_stats(self) -> Dict:
        """Get subscription statistics."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE active = TRUE")
        total = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM subscriptions WHERE whatsapp_verified = TRUE AND active = TRUE"
        )
        whatsapp = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM subscriptions WHERE sms_verified = TRUE AND active = TRUE"
        )
        sms = cursor.fetchone()[0]

        cursor.execute("""
            SELECT district, COUNT(*) as count 
            FROM subscriptions 
            WHERE active = TRUE 
            GROUP BY district 
            ORDER BY count DESC 
            LIMIT 5
        """)
        top_districts = cursor.fetchall()

        conn.close()

        return {
            "total_subscribers": total,
            "whatsapp_verified": whatsapp,
            "sms_verified": sms,
            "top_districts": [{"district": d, "count": c} for d, c in top_districts],
        }

    def _get_connection(self):
        """Get database connection (for API endpoints)."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn


subscription_manager = SubscriptionManager()
