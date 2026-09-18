"""Real, durable historical archive of every raw source reading this
platform ingests - the "Historical data" foundation for training,
backtesting, evaluation, model comparison, and event replay.

Before this table existed, this platform's only durable historical
records were src/hydrology/flood_polygons.py's 8 documented flood
EVENTS (a fixed, hand-curated list, useful for backtesting but never
growing) and risk_history's bare score/tier series (no per-source
detail, no quality metadata). Neither preserves what CHIRPS, Open-
Meteo, the real river gauge, dam levels, or SMAP actually said on any
given day - which is exactly what src/models/rare_event_verification.py
needed real Earth Engine calls to reconstruct after the fact for
rainfall specifically, and what every other source still lacks any
historical record of at all.

Every row is one real reading (or an honest miss) from one source for
one district, tagged with the QARTOD-based quality flag
(src/data_quality/quality_checks.py) it received at ingestion time -
so a future backtest can filter to only PASS-quality readings, or
study exactly when and how a source degraded, not just what the value
was.

Reuses alert_db.py's get_db() - same physical SQLite file, same real
Cloud Run ephemeral-filesystem caveat already disclosed for every other
table in this database. Durable long-term accumulation of this table
specifically is exactly the kind of growing archive that would benefit
most from migrating to a persistent store (Firestore/Cloud SQL) - see
alert_review.py's own module docstring for the same disclosed
limitation, not yet acted on here either.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.database.alert_db import get_db

logger = logging.getLogger(__name__)


def init_observation_history_table() -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS observation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                district TEXT NOT NULL,
                source TEXT NOT NULL,
                value REAL,
                unit TEXT,
                quality_flag TEXT NOT NULL,
                observation_date TEXT,
                recorded_at TEXT NOT NULL
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_observation_history_district_source_time "
            "ON observation_history(district, source, recorded_at)"
        )
        conn.commit()


def save_observation(
    district: str,
    source: str,
    value: Optional[float],
    unit: str,
    quality_flag: str,
    observation_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Records one real (or honestly missing) reading. `value=None`
    with quality_flag="missing" is a legitimate, real row - a
    documented absence, not skipped - so completeness can later be
    computed from real counts instead of inferred from gaps."""
    now = datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO observation_history
                (district, source, value, unit, quality_flag, observation_date, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (district, source, value, unit, quality_flag, observation_date, now),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "recorded_at": now}


def get_observations(
    district: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """Real recorded observations, most recent first - the growing
    dataset src/models/rare_event_verification.py's future extensions
    (model comparison, event replay against real accumulated history
    rather than a fresh Earth Engine call each time) would read from."""
    query = "SELECT * FROM observation_history WHERE 1=1"
    params: List[Any] = []
    if district:
        query += " AND district = ?"
        params.append(district)
    if source:
        query += " AND source = ?"
        params.append(source)
    # id DESC as a tiebreaker: two rapid inserts (the automated pipeline
    # writes several sources back-to-back) can land on the exact same
    # datetime.now().isoformat() string, which would otherwise make
    # "most recent first" non-deterministic between them - id always
    # reflects true insertion order.
    query += " ORDER BY recorded_at DESC, id DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
