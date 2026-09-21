"""Real WhatsApp/Telegram alert-opt-in subscribers - who actually
receives an outbound flood alert, keyed by the same channel identifier
(a WhatsApp phone number or Telegram chat_id) a citizen already used to
report a flood.

Deliberately NOT the existing email-centric `subscriptions` table
(src/database/alert_db.py, src/api/routes/subscriptions.py): that
table's schema requires an email address (SubscriptionRequest.email is
a mandatory EmailStr, and unsubscribe/get_subscription are keyed by
email), which cannot represent a WhatsApp-only or Telegram-only
subscriber with no email at all. That table was also found, while
building this, to have zero real consumers - no provider or engine
code ever actually queries it, so a location_filter/min_risk_tier
subscription there has never once affected who gets alerted (every
send instead goes to a static settings.WHATSAPP_RECIPIENTS/SMS_
RECIPIENTS list). This module exists specifically so that mistake isn't
repeated: src/alerts/providers/whatsapp_provider.py and
telegram_provider.py both genuinely query get_subscribers_for_alert()
on every send.

Lives in the same alerts.db file as everything else in this package
(reuses its get_db()/_apply_pragmas()) rather than a new SQLite file, to
avoid a third file needing its own litestream.yml replication entry.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from src.alerts.formatter import tier_at_least
from src.database.alert_db import get_db

logger = logging.getLogger("nfcc.database.channel_subscriptions")

ALLOWED_CHANNELS = {"whatsapp", "telegram"}


def init_channel_subscriptions_table() -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channel_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel TEXT NOT NULL,
                identifier TEXT NOT NULL,
                district TEXT,
                min_risk_tier TEXT NOT NULL DEFAULT 'MODERATE',
                active BOOLEAN NOT NULL DEFAULT 1,
                subscribed_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(channel, identifier)
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_channel_sub_district "
            "ON channel_subscriptions(district)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_channel_sub_active "
            "ON channel_subscriptions(active)"
        )
        conn.commit()


def subscribe(
    channel: str, identifier: str, district: Optional[str] = None, min_risk_tier: str = "MODERATE"
) -> Dict:
    """district=None means "all districts" - a citizen who didn't name
    one, or explicitly asked for every alert."""
    if channel not in ALLOWED_CHANNELS:
        raise ValueError(f"channel must be one of {sorted(ALLOWED_CHANNELS)}")

    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO channel_subscriptions
                (channel, identifier, district, min_risk_tier, active, subscribed_at, updated_at)
            VALUES (?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(channel, identifier) DO UPDATE SET
                district = excluded.district,
                min_risk_tier = excluded.min_risk_tier,
                active = 1,
                updated_at = excluded.updated_at
            """,
            (channel, identifier, district, min_risk_tier, now, now),
        )
        conn.commit()
    return {"channel": channel, "identifier": identifier, "district": district, "active": True}


def unsubscribe(channel: str, identifier: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE channel_subscriptions SET active = 0, updated_at = ?
            WHERE channel = ? AND identifier = ?
            """,
            (now, channel, identifier),
        )
        conn.commit()
        return cursor.rowcount > 0


def get_subscribers_for_alert(channel: str, district: str, risk_tier: str) -> List[Dict]:
    """Real, active subscribers for `channel` who should receive an
    alert about `district` at `risk_tier` - either subscribed to this
    exact district or to "all districts" (district IS NULL), and whose
    min_risk_tier is at or below this alert's actual tier."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM channel_subscriptions
            WHERE channel = ? AND active = 1
            AND (district = ? OR district IS NULL)
            """,
            (channel, district),
        )
        rows = [dict(row) for row in cursor.fetchall()]
    return [r for r in rows if tier_at_least(risk_tier, r["min_risk_tier"])]


def get_all_channel_subscriptions(active_only: bool = True) -> List[Dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        if active_only:
            cursor.execute("SELECT * FROM channel_subscriptions WHERE active = 1 ORDER BY subscribed_at DESC")
        else:
            cursor.execute("SELECT * FROM channel_subscriptions ORDER BY subscribed_at DESC")
        return [dict(row) for row in cursor.fetchall()]
