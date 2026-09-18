"""The prediction ledger - real, durable storage answering exactly what
a national flood center's forecast-verification archive must answer
(the same principle behind ECMWF's MARS archive and NOAA's forecast
verification systems: every forecast is stored alongside its eventual
observation, since verification is impossible without both): what
happened (the real evidence snapshot), where (district), when
(predicted_at), what the system predicted (risk_score/tier/confidence),
why it predicted it (reason/risk_attribution), and - filled in later,
often much later - what eventually happened (outcome).

Before this table existed, nothing preserved a real assessment once it
scrolled past: pending_alerts (src/database/alert_db.py) only holds
rows that crossed the review threshold and only until reviewed/expired,
and risk_history (src/database/risk_history_db.py) stores just a bare
score/tier time series with none of the evidence or reasoning behind
it. Neither can answer "what would CivicFlood have said, and why" for
an assessment made yesterday - or support the reliability/calibration
analysis src/models/rare_event_verification.py already does for the
rainfall threshold, extended to the full fused system, once enough
real outcomes accumulate here.

outcome starts NULL and is filled in later via record_outcome() - by a
human curator confirming a real flood (or its absence) from news
reports, satellite confirmation, or verified citizen reports crossing
a real threshold. A NULL outcome is not a missing row, it's an honest
"not yet known" - the same disclosed-uncertainty standard applied
everywhere else in this platform.

Reuses alert_db.py's get_db() - same physical SQLite file, same
connection pattern, same real Cloud Run ephemeral-filesystem caveat
already disclosed for every other table in this database.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.database.alert_db import get_db

logger = logging.getLogger(__name__)


def init_prediction_ledger_table() -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prediction_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                district TEXT NOT NULL,
                predicted_at TEXT NOT NULL,
                evidence_snapshot TEXT NOT NULL,
                risk_score REAL,
                risk_tier TEXT,
                fused_risk_score REAL,
                fused_risk_tier TEXT,
                confidence REAL,
                reason TEXT,
                risk_attribution TEXT,
                outcome TEXT,
                outcome_source TEXT,
                outcome_recorded_at TEXT
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_prediction_ledger_district_time "
            "ON prediction_ledger(district, predicted_at)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_prediction_ledger_outcome "
            "ON prediction_ledger(outcome)"
        )
        conn.commit()


def save_prediction(
    district: str,
    evidence_snapshot: Dict[str, Any],
    risk_score: Optional[float] = None,
    risk_tier: Optional[str] = None,
    fused_risk_score: Optional[float] = None,
    fused_risk_tier: Optional[str] = None,
    confidence: Optional[float] = None,
    reason: Optional[str] = None,
    risk_attribution: Optional[str] = None,
) -> Dict[str, Any]:
    """Records one real prediction - the "what happened" (evidence
    snapshot) and "what/why" (score/tier/confidence/reason) halves of
    the ledger. Returns {"id":..., "predicted_at":...}."""
    now = datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO prediction_ledger (
                district, predicted_at, evidence_snapshot, risk_score,
                risk_tier, fused_risk_score, fused_risk_tier, confidence,
                reason, risk_attribution
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                district,
                now,
                json.dumps(evidence_snapshot),
                risk_score,
                risk_tier,
                fused_risk_score,
                fused_risk_tier,
                confidence,
                reason,
                risk_attribution,
            ),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "predicted_at": now}


def record_outcome(prediction_id: int, outcome: str, outcome_source: str) -> bool:
    """Fills in the "what eventually happened" half, once it's real and
    known - never guessed or defaulted. Returns False if no such
    prediction exists rather than silently no-op'ing."""
    now = datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE prediction_ledger
            SET outcome = ?, outcome_source = ?, outcome_recorded_at = ?
            WHERE id = ?
            """,
            (outcome, outcome_source, now, prediction_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def _decode(row: Dict[str, Any]) -> Dict[str, Any]:
    raw = row.get("evidence_snapshot")
    try:
        row["evidence_snapshot"] = json.loads(raw) if raw else {}
    except (TypeError, ValueError):
        row["evidence_snapshot"] = {}
    return row


def get_predictions(
    district: Optional[str] = None, limit: int = 100, outcome: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Real recorded predictions, most recent first. `outcome`
    filters to a specific outcome value (e.g. "flood_confirmed"), or
    pass outcome="__pending__" for predictions with no outcome yet -
    the queue a human curator would work through."""
    query = "SELECT * FROM prediction_ledger WHERE 1=1"
    params: List[Any] = []
    if district:
        query += " AND district = ?"
        params.append(district)
    if outcome == "__pending__":
        query += " AND outcome IS NULL"
    elif outcome:
        query += " AND outcome = ?"
        params.append(outcome)
    # id DESC as a tiebreaker - see observation_history_db.py's
    # get_observations() for why: rapid inserts can share an identical
    # datetime.now().isoformat() string.
    query += " ORDER BY predicted_at DESC, id DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [_decode(dict(row)) for row in cursor.fetchall()]


def get_prediction(prediction_id: int) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM prediction_ledger WHERE id = ?", (prediction_id,))
        row = cursor.fetchone()
        return _decode(dict(row)) if row else None
