"""CiviSenti community flood report handler.

This script processes WhatsApp-style flood reports, validates them, stores
structured reports, and checks them against available rainfall/satellite-style
risk evidence from the NFCC data pipeline.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.chatbot.whatsapp_bot import (  # noqa: E402
    CiviSentiWhatsAppBot,
    CommunityFloodReport,
)

REPORTS_DIR = BASE_DIR / "data" / "community_reports"
PHOTOS_DIR = REPORTS_DIR / "photos"
REPORTS_JSONL = REPORTS_DIR / "reports.jsonl"
VALIDATION_REPORT = REPORTS_DIR / "civisenti_validation_summary.json"
RAINFALL_DATA_PATH = BASE_DIR / "data" / "processed" / "accra_features_2024.parquet"
LOG_PATH = BASE_DIR / "logs" / "civisenti_handler.log"

logger = logging.getLogger("nfcc.civisenti")


def setup_logging() -> None:
    """Configure logging for CiviSenti processing."""

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH),
            logging.StreamHandler(),
        ],
    )


def ensure_directories() -> None:
    """Create required CiviSenti folders."""

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)


def load_payload(payload_path: Path) -> Dict[str, Any]:
    """Load a sample incoming WhatsApp payload from JSON."""

    with payload_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_report(report: CommunityFloodReport, validation: Dict[str, Any]) -> Path:
    """Append a structured community report to JSONL storage."""

    ensure_directories()

    record = report.to_dict()
    record["validation"] = validation
    record["stored_at"] = datetime.now(timezone.utc).isoformat()

    with REPORTS_JSONL.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger.info("Stored community report %s", report.report_id)
    return REPORTS_JSONL


def load_reports() -> pd.DataFrame:
    """Load stored CiviSenti community reports."""

    if not REPORTS_JSONL.exists():
        return pd.DataFrame()

    records = []

    with REPORTS_JSONL.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    return pd.DataFrame(records)


def validate_against_rainfall_data(report: CommunityFloodReport) -> Dict[str, Any]:
    """Validate a report against available NFCC rainfall/risk data.

    This is an MVP validation step. It checks whether the existing processed
    rainfall/risk dataset shows elevated rainfall or risk near the report time.
    """

    if not RAINFALL_DATA_PATH.exists():
        return {
            "status": "pending",
            "reason": "Rainfall/risk dataset not found.",
            "source": str(RAINFALL_DATA_PATH),
        }

    try:
        df = pd.read_parquet(RAINFALL_DATA_PATH)
    except Exception as exc:
        logger.warning("Could not read rainfall data: %s", exc)
        return {
            "status": "pending",
            "reason": f"Could not read rainfall/risk dataset: {exc}",
            "source": str(RAINFALL_DATA_PATH),
        }

    if df.empty:
        return {
            "status": "pending",
            "reason": "Rainfall/risk dataset is empty.",
            "source": str(RAINFALL_DATA_PATH),
        }

    latest = df.iloc[-1]

    precipitation = _safe_float(latest.get("precipitation"))
    roll_3d = _safe_float(latest.get("roll_3d"))
    z_score = _safe_float(latest.get("z_score"))

    evidence = {
        "precipitation": precipitation,
        "roll_3d": roll_3d,
        "z_score": z_score,
    }

    if precipitation is None and roll_3d is None and z_score is None:
        return {
            "status": "pending",
            "reason": "No rainfall evidence columns were available.",
            "source": str(RAINFALL_DATA_PATH),
            "evidence": evidence,
        }

    elevated_rainfall = (precipitation or 0) >= 20 or (roll_3d or 0) >= 50
    elevated_anomaly = (z_score or 0) >= 1.5

    if elevated_rainfall or elevated_anomaly:
        status = "supported"
        reason = "Recent rainfall/risk evidence supports the community report."
    else:
        status = "not_supported"
        reason = (
            "Available rainfall/risk evidence does not strongly support the report."
        )

    return {
        "status": status,
        "reason": reason,
        "source": str(RAINFALL_DATA_PATH),
        "evidence": evidence,
    }


def generate_validation_summary() -> Path:
    """Create a summary file for scheduled CiviSenti checks."""

    ensure_directories()

    reports = load_reports()

    if reports.empty:
        summary = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_reports": 0,
            "message": "No CiviSenti community reports found.",
        }
    else:
        summary = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_reports": int(len(reports)),
            "status_counts": reports.get("status", pd.Series(dtype=str))
            .value_counts()
            .to_dict(),
            "severity_counts": reports.get("severity", pd.Series(dtype=str))
            .value_counts()
            .to_dict(),
        }

    with VALIDATION_REPORT.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)

    logger.info("Generated CiviSenti validation summary at %s", VALIDATION_REPORT)
    return VALIDATION_REPORT


def process_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Process one incoming WhatsApp payload."""

    bot = CiviSentiWhatsAppBot()

    report = bot.parse_incoming_payload(payload)
    validation = bot.validate_report(report)

    satellite_validation = validate_against_rainfall_data(report)
    report.satellite_validation = satellite_validation["status"]

    output_path = save_report(report, validation)
    reply = bot.build_reply(report, validation)

    return {
        "success": True,
        "report": report.to_dict(),
        "validation": validation,
        "satellite_validation": satellite_validation,
        "reply": reply,
        "stored_at": str(output_path),
    }


def _safe_float(value: Any) -> Optional[float]:
    """Convert a value to float safely."""

    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_sample_payload() -> Dict[str, Any]:
    """Create a local sample payload for testing without Twilio."""

    return {
        "From": "whatsapp:+233240000000",
        "Body": "Flooding at Kaneshie. Water is high and the road is blocked.",
        "Latitude": "5.5663",
        "Longitude": "-0.2374",
        "NumMedia": "1",
        "MediaUrl0": "https://example.com/sample-flood-photo.jpg",
        "MediaContentType0": "image/jpeg",
    }


def main() -> int:
    """Run the CiviSenti handler from the command line."""

    setup_logging()

    parser = argparse.ArgumentParser(description="Process CiviSenti flood reports")
    parser.add_argument(
        "--payload",
        type=str,
        help="Path to JSON file containing a sample WhatsApp webhook payload.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Generate scheduled CiviSenti validation summary.",
    )

    args = parser.parse_args()

    if args.summary:
        path = generate_validation_summary()
        print(f"CiviSenti summary generated: {path}")
        return 0

    if args.payload:
        payload = load_payload(Path(args.payload))
    else:
        payload = build_sample_payload()

    result = process_payload(payload)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
