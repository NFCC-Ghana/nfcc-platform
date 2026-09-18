"""Database operations for alerts and subscriptions."""

import json
import logging
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "data" / "alerts.db"


@contextmanager
def get_db():
    """
    Get a thread-safe database connection.
    Creates a NEW connection each time to avoid thread issues.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False allows connections across threads
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def get_db_connection():
    """
    Get a database connection (for backward compatibility).
    Creates a NEW connection each time.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize the alerts database with table and indexes."""
    init_alerts_table()
    init_subscriptions_table()
    init_pending_alerts_table()


def init_alerts_table() -> None:
    """Initialize the alerts table for storing alert history."""
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
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_alerts_location ON alerts(location)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)"
        )
        conn.commit()


def save_alert(
    location: str,
    score: float,
    risk_tier: str,
    precipitation: float,
    alert_sent: bool = False,
    provider: str = None,
    recipient: str = None,
) -> int:
    """Save an alert to the database."""
    now = datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO alerts (
                location, score, risk_tier, precipitation,
                alert_sent, timestamp, provider, recipient
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                location,
                score,
                risk_tier,
                precipitation,
                alert_sent,
                now,
                provider,
                recipient,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_alerts(
    location: str = None, limit: int = 100, offset: int = 0
) -> List[Dict[str, Any]]:
    """Retrieve alerts with optional filtering."""
    with get_db() as conn:
        cursor = conn.cursor()
        if location:
            cursor.execute(
                "SELECT * FROM alerts WHERE location = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (location, limit, offset),
            )
        else:
            cursor.execute(
                "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
        return [dict(row) for row in cursor.fetchall()]


def get_alert_history(
    location_filter: str = None, limit: int = 100, offset: int = 0
) -> List[Dict[str, Any]]:
    """Get alert history (alias for get_alerts).

    Parameter is named location_filter, not location, to match its
    sibling get_total_alerts_count() and the one caller of this function
    (src/api/routes/alerts.py's GET /alerts/history) - it used to be
    named `location`, which that route was never actually calling it
    with, raising a TypeError on every request that reached this far.
    """
    return get_alerts(location=location_filter, limit=limit, offset=offset)


def get_alert_stats() -> Dict[str, Any]:
    """Get statistics about alerts."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM alerts")
        total_row = cursor.fetchone()
        total = total_row["total"] if total_row else 0

        cursor.execute("""
            SELECT risk_tier, COUNT(*) as count
            FROM alerts
            GROUP BY risk_tier
            ORDER BY count DESC
        """)
        by_tier = {row["risk_tier"]: row["count"] for row in cursor.fetchall()}

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
            "top_locations": top_locations,
        }


# ============================================================
# PENDING ALERTS - human review queue
# ============================================================
# Automated risk assessment (scripts/automated_risk_assessment.py, run on
# a schedule via .github/workflows/automated_risk_assessment.yml) inserts
# rows here instead of calling AlertEngine directly - nothing gets sent to
# real people until a human reviews it in the dashboard's Alert Review
# Queue and explicitly approves it (src/api/routes/alert_review.py).
# Before this, AlertEngine.process() sent the moment a score crossed
# threshold with no human step anywhere in the code.


def init_pending_alerts_table() -> None:
    """Initialize the pending_alerts table (human review queue)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location TEXT NOT NULL,
                score REAL NOT NULL,
                risk_tier TEXT NOT NULL,
                precipitation REAL NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                reviewed_at TEXT,
                reviewed_by TEXT
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_pending_alerts_status "
            "ON pending_alerts(status)"
        )
        # Migration for tables created before severity/urgency/certainty
        # existed (the Common Alerting Protocol's own three independent
        # decision axes - OASIS CAP standard - replacing a single
        # collapsed risk_tier as the only context a reviewer sees).
        # SQLite has no "ADD COLUMN IF NOT EXISTS"; catching the duplicate-
        # column error is the standard way to make this idempotent.
        for column in ("severity", "urgency", "certainty"):
            try:
                cursor.execute(
                    f"ALTER TABLE pending_alerts ADD COLUMN {column} TEXT"
                )
            except Exception:
                pass  # column already exists

        # cap_status is CAP's OWN status axis (Actual vs. Exercise/Test/
        # Draft) - deliberately a different column from the existing
        # `status` field above, which tracks this app's *workflow* state
        # (pending/approved/dismissed/cancelled) and would collide in
        # meaning if reused. An 'Exercise' row lets the team practice the
        # full review workflow with zero risk of a real message going out
        # (see approve_pending_alert's cap_status check in
        # src/api/routes/alert_review.py).
        try:
            cursor.execute(
                "ALTER TABLE pending_alerts ADD COLUMN cap_status TEXT "
                "NOT NULL DEFAULT 'Actual'"
            )
        except Exception:
            pass

        # Geotargeting (real named communities, not just a district name)
        # and JMA-style tiered response guidance (who specifically should
        # act) - stored as JSON text / plain text respectively so a
        # reviewer sees this context without recomputing it every render.
        for column in ("affected_communities", "response_guidance"):
            try:
                cursor.execute(
                    f"ALTER TABLE pending_alerts ADD COLUMN {column} TEXT"
                )
            except Exception:
                pass

        # basis = which real signal produced this assessment - real
        # rare-event backtesting (src/models/rare_event_verification.py)
        # found that a 3-day rolling accumulation of real observed
        # rainfall has meaningfully better SEDI (rare-event skill) than
        # same-day/forecast-only scoring, so the automated pipeline now
        # runs both a forward-looking forecast assessment AND a backward-
        # looking antecedent-accumulation assessment per district
        # (scripts/automated_risk_assessment.py) - a reviewer needs to
        # know which one triggered a given queued item, since they carry
        # different meaning ("heavy rain is coming" vs "the ground/rivers
        # are already saturated from the last 3 days").
        try:
            cursor.execute(
                "ALTER TABLE pending_alerts ADD COLUMN basis TEXT "
                "NOT NULL DEFAULT 'forecast_next_24h'"
            )
        except Exception:
            pass
        conn.commit()


def save_pending_alert(
    location: str,
    score: float,
    risk_tier: str,
    precipitation: float,
    message: str,
    severity: str = None,
    urgency: str = None,
    certainty: str = None,
    cap_status: str = "Actual",
    affected_communities: Optional[List[str]] = None,
    response_guidance: str = None,
    basis: str = "forecast_next_24h",
) -> int:
    """Queue an automated assessment for human review. Returns the new row's id.

    severity/urgency/certainty are the Common Alerting Protocol's three
    independent decision axes (OASIS CAP standard, the international
    backbone behind FEMA IPAWS, EU/Japan/Canada alerting systems) -
    optional here so existing callers/tests that don't compute them yet
    keep working, but src/api/routes/alert_review.py's real assessment
    path always sets all three.

    cap_status is CAP's Actual/Exercise axis - 'Exercise' rows are drills
    the review workflow can be practiced on without ever reaching
    AlertEngine.process() (see approve_pending_alert). affected_communities
    (real named neighborhoods, src/exposure/community_names.py) and
    response_guidance (JMA-style "who should act") are stored as-computed
    so the review card can show them without recomputing on every read.

    basis records which real rainfall signal this assessment used -
    'forecast_next_24h' (anticipatory) or 'antecedent_3d_accumulation'
    (real observed rainfall already fallen) - see the pending_alerts
    migration above for why this distinction matters to a reviewer.
    """
    now = datetime.now().isoformat()
    communities_json = (
        json.dumps(affected_communities) if affected_communities else None
    )
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO pending_alerts (
                location, score, risk_tier, precipitation, message,
                status, created_at, severity, urgency, certainty,
                cap_status, affected_communities, response_guidance, basis
            ) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                location,
                score,
                risk_tier,
                precipitation,
                message,
                now,
                severity,
                urgency,
                certainty,
                cap_status,
                communities_json,
                response_guidance,
                basis,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def _decode_pending_alert(row: Dict[str, Any]) -> Dict[str, Any]:
    """affected_communities is stored as a JSON string (see save_pending_alert)
    - decode it back to a real list for API consumers, defaulting to []
    for rows saved before this column existed or with nothing stored."""
    raw = row.get("affected_communities")
    try:
        row["affected_communities"] = json.loads(raw) if raw else []
    except (TypeError, ValueError):
        row["affected_communities"] = []
    return row


def get_pending_alerts(status: str = "pending") -> List[Dict[str, Any]]:
    """List pending-review alerts, newest first. status=None returns all."""
    with get_db() as conn:
        cursor = conn.cursor()
        if status:
            cursor.execute(
                "SELECT * FROM pending_alerts WHERE status = ? "
                "ORDER BY created_at DESC",
                (status,),
            )
        else:
            cursor.execute("SELECT * FROM pending_alerts ORDER BY created_at DESC")
        return [_decode_pending_alert(dict(row)) for row in cursor.fetchall()]


def get_pending_alert(alert_id: int) -> Optional[Dict[str, Any]]:
    """Fetch one pending-review alert by id, or None if it doesn't exist."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pending_alerts WHERE id = ?", (alert_id,))
        row = cursor.fetchone()
        return _decode_pending_alert(dict(row)) if row else None


def update_pending_alert_status(
    alert_id: int, status: str, reviewed_by: str = None
) -> None:
    """Mark a pending alert as approved/dismissed with a review timestamp."""
    now = datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE pending_alerts SET status = ?, reviewed_at = ?, "
            "reviewed_by = ? WHERE id = ?",
            (status, now, reviewed_by, alert_id),
        )
        conn.commit()


def get_total_alerts_count(location_filter: Optional[str] = None) -> int:
    """Get total number of alerts, optionally filtered by location."""
    with get_db() as conn:
        cursor = conn.cursor()
        if location_filter:
            cursor.execute(
                "SELECT COUNT(*) FROM alerts WHERE location = ?", (location_filter,)
            )
        else:
            cursor.execute("SELECT COUNT(*) FROM alerts")
        row = cursor.fetchone()
        return row[0] if row else 0


# ============================================================
# Subscription Management Functions
# ============================================================


def init_subscriptions_table() -> None:
    """Initialize the subscriptions table."""
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
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_subscription_email ON subscriptions(email)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_subscription_active ON subscriptions(active)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_subscription_location ON subscriptions(location_filter)"
        )
        conn.commit()


def subscribe(data_dict: Dict[str, Any]) -> int:
    """Create a new subscription."""
    now = datetime.now().isoformat()
    token = secrets.token_urlsafe(16)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO subscriptions (
                email, phone, preferred_provider, location_filter,
                min_risk_tier, active, created_at, updated_at, unsubscribe_token
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                data_dict.get("email"),
                data_dict.get("phone"),
                data_dict.get("preferred_provider", "email"),
                data_dict.get("location_filter"),
                data_dict.get("min_risk_tier", "MODERATE"),
                1,
                now,
                now,
                token,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def unsubscribe(email: str) -> bool:
    """Unsubscribe a user by marking their subscription as inactive."""
    now = datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE subscriptions SET active = 0, updated_at = ? WHERE email = ?",
            (now, email),
        )
        conn.commit()
        return cursor.rowcount > 0


def get_subscription(email: str) -> Optional[Dict[str, Any]]:
    """Retrieve a subscription by email address."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subscriptions WHERE email = ?", (email,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_all_subscriptions(active_only: bool = True) -> List[Dict[str, Any]]:
    """Retrieve all subscriptions, optionally filtered by active status."""
    with get_db() as conn:
        cursor = conn.cursor()
        if active_only:
            cursor.execute(
                "SELECT * FROM subscriptions WHERE active = 1 ORDER BY created_at DESC"
            )
        else:
            cursor.execute("SELECT * FROM subscriptions ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]


def get_subscriptions_for_location(
    location: str, active_only: bool = True
) -> List[Dict[str, Any]]:
    """Retrieve subscriptions for a specific location."""
    with get_db() as conn:
        cursor = conn.cursor()
        if active_only:
            cursor.execute(
                """
                SELECT * FROM subscriptions
                WHERE (location_filter = ? OR location_filter IS NULL)
                AND active = 1
                ORDER BY created_at DESC
            """,
                (location,),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM subscriptions
                WHERE location_filter = ? OR location_filter IS NULL
                ORDER BY created_at DESC
            """,
                (location,),
            )
        return [dict(row) for row in cursor.fetchall()]


def update_subscription(email: str, updates: Dict[str, Any]) -> bool:
    """Update a subscription with provided fields."""
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
            values,
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_subscription(email: str) -> bool:
    """Permanently delete a subscription record."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM subscriptions WHERE email = ?", (email,))
        conn.commit()
        return cursor.rowcount > 0
