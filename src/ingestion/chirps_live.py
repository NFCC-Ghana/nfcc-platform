"""
Live CHIRPS rainfall ingestion via Google Earth Engine.

Provides daily automated fetch, historical backfill, and quality reporting.
Complements scripts/daily_chirps_pull.py with a reusable module API.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

logger = logging.getLogger("nfcc.ingestion.chirps")

PROJECT_ID = os.getenv("GEE_PROJECT_ID", "nfcc-earth-engine-2026")
CHIRPS_COLLECTION = "UCSB-CHG/CHIRPS/DAILY"

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / "data" / "raw" / "chirps"
REPORT_DIR = BASE_DIR / "reports" / "data_quality"

# Accra bounding box: west, south, east, north
ACCRA_BBOX = [-0.35, 5.45, 0.05, 5.75]


def _ee():
    """Lazy import so tests and CI can load the module without earthengine-api."""
    try:
        import ee
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "earthengine-api is required for live GEE ingestion. "
            "Install with: pip install earthengine-api"
        ) from exc
    return ee


class ChirpsLiveIngester:
    """Earth Engine CHIRPS ingestion with daily updates and backfill."""

    def __init__(
        self,
        project_id: str = PROJECT_ID,
        raw_dir: Path = RAW_DIR,
        report_dir: Path = REPORT_DIR,
    ) -> None:
        self.project_id = project_id
        self.raw_dir = raw_dir
        self.report_dir = report_dir
        self._initialized = False

    def initialize(self) -> None:
        """Initialize Google Earth Engine (idempotent)."""
        if self._initialized:
            return
        _ee().Initialize(project=self.project_id)
        self._initialized = True
        logger.info("Earth Engine initialized (project=%s)", self.project_id)

    def default_target_date(self) -> str:
        """Yesterday UTC — CHIRPS final daily product latency."""
        return (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()

    def get_image(self, target_date: str) -> Optional[Any]:
        """Return CHIRPS daily image for a date, or None if unavailable."""
        ee = _ee()
        self.initialize()
        start = ee.Date(target_date)
        end = start.advance(1, "day")
        collection = (
            ee.ImageCollection(CHIRPS_COLLECTION)
            .filterDate(start, end)
            .select("precipitation")
        )
        if collection.size().getInfo() == 0:
            return None
        return collection.first()

    def extract_stats(self, image: Any, target_date: str) -> dict[str, Any]:
        """Extract regional rainfall statistics from a CHIRPS image."""
        ee = _ee()
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

        return {
            "date": target_date,
            "region": "Accra",
            "dataset": CHIRPS_COLLECTION,
            "precipitation_mean_mm": stats.get("precipitation_mean"),
            "precipitation_min_mm": stats.get("precipitation_min"),
            "precipitation_max_mm": stats.get("precipitation_max"),
            "valid_pixel_count": stats.get("precipitation_count", 0),
            "bbox": ACCRA_BBOX,
            "ingested_at_utc": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def validate_record(record: dict[str, Any]) -> dict[str, Any]:
        """Run data-quality checks on an extracted record."""
        issues: list[str] = []

        if record.get("valid_pixel_count", 0) == 0:
            issues.append("No valid pixels found for selected region.")

        for field in (
            "precipitation_mean_mm",
            "precipitation_min_mm",
            "precipitation_max_mm",
        ):
            value = record.get(field)
            if value is None:
                issues.append(f"{field} is missing.")
            elif value < 0:
                issues.append(f"{field} is negative.")

        status = "passed" if not issues else "warning"
        return {
            "status": status,
            "checks": {
                "has_valid_pixels": record.get("valid_pixel_count", 0) > 0,
                "mean_present": record.get("precipitation_mean_mm") is not None,
                "min_present": record.get("precipitation_min_mm") is not None,
                "max_present": record.get("precipitation_max_mm") is not None,
                "non_negative_values": all(
                    record.get(f) is None or record.get(f) >= 0
                    for f in (
                        "precipitation_mean_mm",
                        "precipitation_min_mm",
                        "precipitation_max_mm",
                    )
                ),
            },
            "issues": issues,
        }

    def write_outputs(
        self, record: dict[str, Any], quality_report: dict[str, Any]
    ) -> Path:
        """Persist CSV record and JSON quality report."""
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)

        target_date = record["date"]
        csv_path = self.raw_dir / f"chirps_daily_{target_date}.csv"
        report_path = self.report_dir / f"chirps_quality_{target_date}.json"

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
        logger.info("CHIRPS outputs written: %s, %s", csv_path, report_path)
        return csv_path

    def write_missing_report(self, target_date: str) -> dict[str, Any]:
        """Record graceful degradation when no image is available."""
        self.report_dir.mkdir(parents=True, exist_ok=True)
        report = {
            "date": target_date,
            "dataset": CHIRPS_COLLECTION,
            "status": "missing_data",
            "message": "No CHIRPS image was available for the requested date.",
            "ingested_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        report_path = self.report_dir / f"chirps_quality_{target_date}.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

    def fetch_daily(self, target_date: Optional[str] = None) -> dict[str, Any]:
        """
        Fetch and persist a single day of CHIRPS data.

        Returns a result dict with status: success | missing_data | error.
        """
        target_date = target_date or self.default_target_date()
        logger.info("Fetching CHIRPS for %s", target_date)

        try:
            image = self.get_image(target_date)
            if image is None:
                report = self.write_missing_report(target_date)
                return {
                    "source": "chirps",
                    "status": "missing_data",
                    "date": target_date,
                    "report": report,
                }

            record = self.extract_stats(image, target_date)
            validation = self.validate_record(record)
            quality_report = {
                "date": target_date,
                "dataset": CHIRPS_COLLECTION,
                "region": "Accra",
                "status": validation["status"],
                "validation": validation,
                "record": record,
            }
            self.write_outputs(record, quality_report)
            return {
                "source": "chirps",
                "status": "success",
                "date": target_date,
                "quality_status": validation["status"],
                "record": record,
            }
        except Exception as exc:
            logger.exception("CHIRPS fetch failed for %s: %s", target_date, exc)
            return {
                "source": "chirps",
                "status": "error",
                "date": target_date,
                "error": str(exc),
            }

    def _date_range(self, start_date: str, end_date: str) -> Iterator[str]:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        current = start
        while current <= end:
            yield current.isoformat()
            current += timedelta(days=1)

    def backfill(
        self,
        start_date: str,
        end_date: str,
        skip_existing: bool = True,
    ) -> dict[str, Any]:
        """
        Historical backfill over a date range.

        Args:
            start_date: Inclusive YYYY-MM-DD.
            end_date: Inclusive YYYY-MM-DD.
            skip_existing: Skip dates that already have CSV output.
        """
        results: list[dict[str, Any]] = []
        skipped = 0

        for target_date in self._date_range(start_date, end_date):
            csv_path = self.raw_dir / f"chirps_daily_{target_date}.csv"
            if skip_existing and csv_path.exists():
                skipped += 1
                continue
            results.append(self.fetch_daily(target_date))

        success = sum(1 for r in results if r["status"] == "success")
        missing = sum(1 for r in results if r["status"] == "missing_data")
        errors = sum(1 for r in results if r["status"] == "error")

        return {
            "source": "chirps",
            "operation": "backfill",
            "start_date": start_date,
            "end_date": end_date,
            "processed": len(results),
            "skipped": skipped,
            "success": success,
            "missing_data": missing,
            "errors": errors,
            "results": results,
        }
