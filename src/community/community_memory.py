"""Community intelligence memory with report storage and validation."""

import json
import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CommunityMemoryEngine:
    """
    Complete community intelligence memory system.
    Stores, validates, and learns from community reports.
    """

    def __init__(self, db_path: str = "data/community_reports.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info("Community Memory Engine initialized")

    def _connect(self) -> sqlite3.Connection:
        """WAL mode is required for Litestream (litestream.yml) to
        replicate this database to GCS - see the matching pragma helper
        in src/database/alert_db.py for the full rationale."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_db(self):
        """Initialize database schema."""
        conn = self._connect()
        cursor = conn.cursor()

        # Main reports table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id TEXT UNIQUE NOT NULL,
                district TEXT NOT NULL,
                community TEXT NOT NULL,
                report_type TEXT NOT NULL,
                description TEXT,
                flood_depth_m REAL,
                photo_url TEXT,
                reporter_name TEXT,
                reporter_phone TEXT,
                reporter_email TEXT,
                report_time TIMESTAMP NOT NULL,
                validated BOOLEAN DEFAULT FALSE,
                validation_confidence REAL DEFAULT 0.5,
                trusted_score REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Migration for tables created before GPS/urgency existed - a
        # WhatsApp location share (real Twilio Latitude/Longitude webhook
        # fields) is a far more reliable signal than text district
        # matching, and "trapped"/"rescue"/"emergency" language in a
        # report is a genuine life-safety signal worth a human seeing
        # immediately rather than buried in free-text description.
        # SQLite has no "ADD COLUMN IF NOT EXISTS" - catching the
        # duplicate-column error is the standard idempotent pattern (see
        # src/database/alert_db.py's matching migration for pending_alerts).
        for column, coltype in (("latitude", "REAL"), ("longitude", "REAL")):
            try:
                cursor.execute(f"ALTER TABLE reports ADD COLUMN {column} {coltype}")
            except Exception:
                pass  # column already exists
        try:
            cursor.execute(
                "ALTER TABLE reports ADD COLUMN urgency TEXT NOT NULL DEFAULT 'MODERATE'"
            )
        except Exception:
            pass

        # Add indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_reports_district ON reports(district)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_reports_time ON reports(report_time)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_reports_validated ON reports(validated)"
        )

        conn.commit()
        conn.close()

    def submit_report(self, report_data: Dict) -> Dict:
        """Submit a community report.

        report_id includes a uuid4 suffix, not just a second-precision
        timestamp: two reports landing in the same second (real under
        WhatsApp inbound traffic, e.g. two "Unspecified"-community
        unclassified reports within a second of each other) used to
        collide on the UNIQUE constraint below - caught when the new
        WhatsApp webhook (src/api/routes/whatsapp_webhook.py) hit exactly
        this in testing.
        """
        conn = self._connect()
        try:
            cursor = conn.cursor()

            community_slug = (report_data.get("community") or "UNK")[:5]
            report_id = (
                f"RPT_{datetime.now().strftime('%Y%m%d%H%M%S')}_"
                f"{community_slug}_{uuid.uuid4().hex[:6]}"
            )

            cursor.execute(
                """
                INSERT INTO reports (
                    report_id, district, community, report_type, description,
                    flood_depth_m, photo_url, reporter_name, reporter_phone,
                    reporter_email, report_time, latitude, longitude, urgency
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    report_id,
                    report_data.get("district"),
                    report_data.get("community"),
                    report_data.get("report_type", "flood"),
                    report_data.get("description"),
                    report_data.get("flood_depth_m", 0),
                    report_data.get("photo_url"),
                    report_data.get("reporter_name"),
                    report_data.get("reporter_phone"),
                    report_data.get("reporter_email"),
                    datetime.now().isoformat(),
                    report_data.get("latitude"),
                    report_data.get("longitude"),
                    report_data.get("urgency", "MODERATE"),
                ),
            )

            conn.commit()

            return {
                "status": "submitted",
                "report_id": report_id,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_reports(
        self,
        district: Optional[str] = None,
        validated_only: bool = False,
        limit: int = 50,
    ) -> List[Dict]:
        """Get community reports."""
        conn = self._connect()
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM reports"
            params = []
            conditions = []

            if district:
                conditions.append("district = ?")
                params.append(district)

            if validated_only:
                conditions.append("validated = 1")

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY report_time DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]
        finally:
            conn.close()

    def validate_report(self, report_id: str, confidence: float) -> Dict:
        """Validate a community report."""
        conn = self._connect()
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE reports
                SET validated = 1, validation_confidence = ?
                WHERE report_id = ?
            """,
                (confidence, report_id),
            )

            conn.commit()

            return {
                "status": "validated",
                "report_id": report_id,
                "confidence": confidence,
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_report_stats(self, district: Optional[str] = None) -> Dict:
        """Get report statistics."""
        conn = self._connect()
        try:
            cursor = conn.cursor()

            query = "SELECT COUNT(*) as total FROM reports"
            params = []
            if district:
                query += " WHERE district = ?"
                params.append(district)

            cursor.execute(query, params)
            total = cursor.fetchone()[0]

            query = "SELECT COUNT(*) as validated FROM reports WHERE validated = 1"
            if district:
                query += " AND district = ?"
                cursor.execute(query, (district,))
            else:
                cursor.execute(query)
            validated = cursor.fetchone()[0]

            return {
                "total_reports": total,
                "validated_reports": validated,
                "validation_rate": validated / total if total > 0 else 0,
            }
        finally:
            conn.close()

    def get_validated_report_count_in_window(
        self, district: str, start_iso: str, end_iso: str
    ) -> int:
        """Real count of VALIDATED reports for a district within a real
        time window - used by src/verification/outcome_verifier.py to
        automatically check whether real citizen reports corroborate a
        past prediction, without a human needing to look each one up
        manually."""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) FROM reports
                WHERE district = ? AND validated = 1
                AND report_time >= ? AND report_time <= ?
                """,
                (district, start_iso, end_iso),
            )
            return cursor.fetchone()[0]
        finally:
            conn.close()


# Singleton instance
community_memory = CommunityMemoryEngine()
