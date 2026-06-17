"""Community intelligence memory with report storage and validation."""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

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
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(str(self.db_path))
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
        
        # Add indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_district ON reports(district)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_time ON reports(report_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_validated ON reports(validated)")
        
        conn.commit()
        conn.close()
    
    def submit_report(self, report_data: Dict) -> Dict:
        """Submit a community report."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        report_id = f"RPT_{datetime.now().strftime('%Y%m%d%H%M%S')}_{report_data.get('community', 'UNK')[:5]}"
        
        cursor.execute("""
            INSERT INTO reports (
                report_id, district, community, report_type, description,
                flood_depth_m, photo_url, reporter_name, reporter_phone, 
                reporter_email, report_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report_id,
            report_data.get('district'),
            report_data.get('community'),
            report_data.get('report_type', 'flood'),
            report_data.get('description'),
            report_data.get('flood_depth_m', 0),
            report_data.get('photo_url'),
            report_data.get('reporter_name'),
            report_data.get('reporter_phone'),
            report_data.get('reporter_email'),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return {
            'status': 'submitted',
            'report_id': report_id,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_reports(self, district: Optional[str] = None, 
                   validated_only: bool = False,
                   limit: int = 50) -> List[Dict]:
        """Get community reports."""
        conn = sqlite3.connect(str(self.db_path))
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
        conn.close()
        
        return [dict(row) for row in rows]
    
    def validate_report(self, report_id: str, confidence: float) -> Dict:
        """Validate a community report."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE reports 
            SET validated = 1, validation_confidence = ?
            WHERE report_id = ?
        """, (confidence, report_id))
        
        conn.commit()
        conn.close()
        
        return {
            'status': 'validated',
            'report_id': report_id,
            'confidence': confidence
        }
    
    def get_report_stats(self, district: Optional[str] = None) -> Dict:
        """Get report statistics."""
        conn = sqlite3.connect(str(self.db_path))
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
        
        conn.close()
        
        return {
            'total_reports': total,
            'validated_reports': validated,
            'validation_rate': validated / total if total > 0 else 0
        }

# Singleton instance
community_memory = CommunityMemoryEngine()
