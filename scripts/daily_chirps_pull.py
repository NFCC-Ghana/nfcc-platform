"""
Daily CHIRPS rainfall ingestion for NFCC.

This script:
1. Connects to Google Earth Engine.
2. Pulls daily CHIRPS rainfall for a target date.
3. Handles missing data gracefully.
4. Writes a CSV output.
5. Writes a data quality JSON report.
6. Logs success and failure events.

Default target date:
    Yesterday in UTC/GMT.

Default region:
    Accra bounding box.

Usage:
    python scripts/daily_chirps_pull.py
    python scripts/daily_chirps_pull.py --date 2026-05-18
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import ee


PROJECT_ID = os.getenv("GEE_PROJECT_ID", "nfcc-earth-engine-2026")
CHIRPS_COLLECTION = "UCSB-CHG/CHIRPS/DAILY"

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw" / "chirps"
REPORT_DIR = BASE_DIR / "reports" / "data_quality"
LOG_DIR = BASE_DIR / "logs"

# Approximate Accra bounding box: west, south, east, north
ACCRA_BBOX = [-0.35, 5.45, 0.05, 5.75]


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / "daily_chirps_pull.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ],
    )


def parse_args() -> argparse.Namespace:
    yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)

    parser = argparse.ArgumentParser(description="Pull daily CHIRPS rainfall data.")
    parser.add_argument(
        "--date",
        default=yesterday.isoformat(),
        help="Target date in YYYY-MM-DD format. Defaults to yesterday in UTC.",
    )
    return parser.parse_args()


def initialize_earth_engine() -> None:
    try:
        ee.Initialize(project=PROJECT_ID)
        logging.info("Google Earth Engine initialized with project: %s", PROJECT_ID)
    except Exception as exc:
        logging.error("Failed to initialize Google Earth Engine: %s", exc)
        raise


def get_chirps_image(target_date: str) -> ee.Image | None:
    start = ee.Date(target_date)
    end = start.advance(1, "day")

    collection = (
        ee.ImageCollection(CHIRPS_COLLECTION)
        .filterDate(start, end)
        .select("precipitation")
    )

    image_count = collection.size().getInfo()
    logging.info("CHIRPS image count for %s: %s", target_date, image_count)

    if image_count == 0:
        return None

    return collection.first()


def extract_rainfall_stats(image: ee.Image, target_date: str) -> dict[str, Any]:
    region = ee.Geometry.Rectangle(ACCRA_BBOX)

    stats = image.reduceRegion(
        reducer=ee.Reducer.mean()
        .combine(ee.Reducer.min(), sharedInputs=True)
        .combine(ee.Reducer.max(), sharedInputs=True)
        .combine(ee.Reducer.count(), sharedInputs=True),
        geometry=region,
        scale=5566,
        maxPixels=1_000_000,
        bestEffort=True,
    ).getInfo()

    mean_value = stats.get("precipitation_mean")
    min_value = stats.get("precipitation_min")
    max_value = stats.get("precipitation_max")
    pixel_count = stats.get("precipitation_count", 0)

    return {
        "date": target_date,
        "region": "Accra",
        "dataset": CHIRPS_COLLECTION,
        "precipitation_mean_mm": mean_value,
        "precipitation_min_mm": min_value,
        "precipitation_max_mm": max_value,
        "valid_pixel_count": pixel_count,
        "bbox": ACCRA_BBOX,
        "ingested_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def validate_record(record: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []

    if record["valid_pixel_count"] == 0:
        issues.append("No valid pixels found for selected region.")

    for field in [
        "precipitation_mean_mm",
        "precipitation_min_mm",
        "precipitation_max_mm",
    ]:
        value = record.get(field)

        if value is None:
            issues.append(f"{field} is missing.")
        elif value < 0:
            issues.append(f"{field} is negative.")

    status = "passed" if not issues else "warning"

    return {
        "status": status,
        "checks": {
            "has_valid_pixels": record["valid_pixel_count"] > 0,
            "mean_present": record["precipitation_mean_mm"] is not None,
            "min_present": record["precipitation_min_mm"] is not None,
            "max_present": record["precipitation_max_mm"] is not None,
            "non_negative_values": all(
                record.get(field) is None or record.get(field) >= 0
                for field in [
                    "precipitation_mean_mm",
                    "precipitation_min_mm",
                    "precipitation_max_mm",
                ]
            ),
        },
        "issues": issues,
    }


def write_outputs(record: dict[str, Any], quality_report: dict[str, Any]) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    target_date = record["date"]
    csv_path = RAW_DIR / f"chirps_daily_{target_date}.csv"
    report_path = REPORT_DIR / f"chirps_quality_{target_date}.json"

    csv_header = (
        "date,region,dataset,precipitation_mean_mm,precipitation_min_mm,"
        "precipitation_max_mm,valid_pixel_count,ingested_at_utc\n"
    )
    csv_row = (
        f"{record['date']},{record['region']},{record['dataset']},"
        f"{record['precipitation_mean_mm']},{record['precipitation_min_mm']},"
        f"{record['precipitation_max_mm']},{record['valid_pixel_count']},"
        f"{record['ingested_at_utc']}\n"
    )

    csv_path.write_text(csv_header + csv_row, encoding="utf-8")
    report_path.write_text(json.dumps(quality_report, indent=2), encoding="utf-8")

    logging.info("CHIRPS CSV written to: %s", csv_path)
    logging.info("Data quality report written to: %s", report_path)


def write_missing_data_report(target_date: str) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    report = {
        "date": target_date,
        "dataset": CHIRPS_COLLECTION,
        "status": "missing_data",
        "message": "No CHIRPS image was available for the requested date.",
        "ingested_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_path = REPORT_DIR / f"chirps_quality_{target_date}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    logging.warning("Missing data report written to: %s", report_path)


def main() -> int:
    setup_logging()
    args = parse_args()
    target_date = args.date

    logging.info("Starting daily CHIRPS ingestion for %s", target_date)

    try:
        initialize_earth_engine()
        image = get_chirps_image(target_date)

        if image is None:
            write_missing_data_report(target_date)
            logging.warning("No CHIRPS data available for %s", target_date)
            return 0

        record = extract_rainfall_stats(image, target_date)
        validation = validate_record(record)

        quality_report = {
            "date": target_date,
            "dataset": CHIRPS_COLLECTION,
            "region": "Accra",
            "status": validation["status"],
            "validation": validation,
            "record": record,
        }

        write_outputs(record, quality_report)

        logging.info(
            "Daily CHIRPS ingestion completed for %s with status: %s",
            target_date,
            validation["status"],
        )
        return 0

    except Exception as exc:
        logging.exception("Daily CHIRPS ingestion failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())