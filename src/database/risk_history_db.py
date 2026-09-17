"""Append-only risk score time series - the genuinely new capability
behind GET /v1/districts/{district}/risk/history (priority deliverable
#9). Nothing like this existed before: alert_db.py's `alerts` table only
records a row when a real alert was actually SENT, and pending_alerts
only exists while an assessment awaits human review - neither is a
continuous record of computed risk over time.

Reuses alert_db.py's get_db() (same SQLite file, same connection
pattern) rather than opening a second database - this is one more table
in the same physical DB, not a separate store.

Write path: scripts/automated_risk_assessment.py (run every 3 hours by
.github/workflows/automated_risk_assessment.yml) calls POST /v1/districts/
{district}/risk/history for each tracked district on every scheduled run,
alongside its existing POST /alerts/assess call - this is the
"orchestration for automated updates" that keeps this table populated
without any endpoint needing to write a row on every ad hoc read (which
would pollute the history with every dashboard page load instead of a
clean periodic trend).
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from src.database.alert_db import get_db

logger = logging.getLogger(__name__)


def init_risk_history_table() -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS risk_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                district TEXT NOT NULL,
                score REAL NOT NULL,
                risk_tier TEXT NOT NULL,
                precipitation REAL NOT NULL,
                source TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_risk_history_district_time "
            "ON risk_history(district, recorded_at)"
        )
        conn.commit()


def save_risk_snapshot(
    district: str, score: float, risk_tier: str, precipitation: float, source: str = "scheduled"
) -> Dict[str, Any]:
    """Record one real, timestamped risk computation. Returns
    {"id": ..., "recorded_at": ...} - callers building a response should
    use this returned recorded_at, not compute their own, so the value
    shown to a caller always matches what was actually written (same
    naive-local-isoformat convention alert_db.py's own tables already
    use - a new timezone-aware format here alone would just be a third
    timestamp convention in this codebase)."""
    now = datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO risk_history
                (district, score, risk_tier, precipitation, source, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (district, score, risk_tier, precipitation, source, now),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "recorded_at": now}


def get_risk_history(district: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Real recorded snapshots for a district, oldest first (natural
    order for plotting a trend), most recent `limit` points."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM (
                SELECT * FROM risk_history
                WHERE district = ?
                ORDER BY recorded_at DESC
                LIMIT ?
            ) ORDER BY recorded_at ASC
            """,
            (district, limit),
        )
        return [dict(row) for row in cursor.fetchall()]
