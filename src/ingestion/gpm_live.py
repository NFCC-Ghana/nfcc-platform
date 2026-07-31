"""
GPM IMERG near-real-time rainfall ingestion via Google Earth Engine.

IMERG Final Run half-hourly product has ~4-hour latency.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("nfcc.ingestion.gpm")

PROJECT_ID = os.getenv("GEE_PROJECT_ID", "nfcc-earth-engine-2026")
GPM_COLLECTION = "NASA/GPM_L3/IMERG_V07"
PRECIP_BAND = "precipitation"
# IMERG Final Run typical latency (hours)
IMERG_LATENCY_HOURS = int(os.getenv("GPM_LATENCY_HOURS", "4"))

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / "data" / "raw" / "gpm"
REPORT_DIR = BASE_DIR / "reports" / "data_quality"

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


class GpmLiveIngester:
    """GPM IMERG ingestion with automatic refresh and quality monitoring."""

    def __init__(
        self,
        project_id: str = PROJECT_ID,
        raw_dir: Path = RAW_DIR,
        report_dir: Path = REPORT_DIR,
        latency_hours: int = IMERG_LATENCY_HOURS,
    ) -> None:
        self.project_id = project_id
        self.raw_dir = raw_dir
        self.report_dir = report_dir
        self.latency_hours = latency_hours
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        _ee().Initialize(project=self.project_id)
        self._initialized = True
        logger.info("Earth Engine initialized for GPM (project=%s)", self.project_id)

    def _region(self) -> Any:
        return _ee().Geometry.Rectangle(ACCRA_BBOX)

    def _collection_for_window(self, start: datetime, end: datetime) -> Any:
        ee = _ee()
        self.initialize()
        start_str = start.strftime("%Y-%m-%dT%H:%M:%S")
        end_str = end.strftime("%Y-%m-%dT%H:%M:%S")
        return (
            ee.ImageCollection(GPM_COLLECTION)
            .filterDate(start_str, end_str)
            .select(PRECIP_BAND)
        )

    def fetch_latest(self) -> dict[str, Any]:
        """
        Fetch the most recent IMERG half-hourly observation.

        Applies latency offset so only finalized granules are requested.
        """
        now = datetime.now(timezone.utc)
        safe_end = now - timedelta(hours=self.latency_hours)
        window_start = safe_end - timedelta(hours=6)

        try:
            collection = self._collection_for_window(window_start, safe_end)
            count = collection.size().getInfo()
            if count == 0:
                report = self._write_missing_report(safe_end.isoformat())
                return {
                    "source": "gpm",
                    "status": "missing_data",
                    "window_end_utc": safe_end.isoformat(),
                    "report": report,
                }

            latest = collection.sort("system:time_start", False).first()
            record = self._extract_halfhourly(latest, safe_end)
            validation = self.validate_record(record)
            quality_report = {
                "dataset": GPM_COLLECTION,
                "region": "Accra",
                "status": validation["status"],
                "validation": validation,
                "record": record,
                "latency_hours": self.latency_hours,
            }
            self._write_outputs(record, quality_report, suffix="latest")
            return {
                "source": "gpm",
                "status": "success",
                "quality_status": validation["status"],
                "record": record,
            }
        except Exception as exc:
            logger.exception("GPM latest fetch failed: %s", exc)
            return {"source": "gpm", "status": "error", "error": str(exc)}

    def fetch_daily(self, target_date: str) -> dict[str, Any]:
        """Aggregate half-hourly IMERG to a daily rainfall total (mm)."""
        start = datetime.fromisoformat(f"{target_date}T00:00:00+00:00")
        end = start + timedelta(days=1)

        try:
            collection = self._collection_for_window(start, end)
            ee = _ee()
            count = collection.size().getInfo()
            if count == 0:
                report = self._write_missing_report(target_date)
                return {
                    "source": "gpm",
                    "status": "missing_data",
                    "date": target_date,
                    "report": report,
                }

            # Sum half-hourly precipitation (mm/hr) * 0.5 h per granule
            daily_total = collection.map(
                lambda img: img.multiply(0.5)
            ).sum()

            stats = daily_total.reduceRegion(
                reducer=ee.Reducer.mean()
                .combine(ee.Reducer.min(), sharedInputs=True)
                .combine(ee.Reducer.max(), sharedInputs=True)
                .combine(ee.Reducer.count(), sharedInputs=True),
                geometry=self._region(),
                scale=11132,
                maxPixels=1_000_000,
                bestEffort=True,
            ).getInfo()

            record = {
                "date": target_date,
                "region": "Accra",
                "dataset": GPM_COLLECTION,
                "precipitation_total_mm": stats.get("precipitation_mean"),
                "precipitation_min_mm": stats.get("precipitation_min"),
                "precipitation_max_mm": stats.get("precipitation_max"),
                "granule_count": count,
                "valid_pixel_count": stats.get("precipitation_count", 0),
                "bbox": ACCRA_BBOX,
                "ingested_at_utc": datetime.now(timezone.utc).isoformat(),
            }
            validation = self.validate_record(record)
            quality_report = {
                "date": target_date,
                "dataset": GPM_COLLECTION,
                "region": "Accra",
                "status": validation["status"],
                "validation": validation,
                "record": record,
            }
            self._write_outputs(record, quality_report, suffix=target_date)
            return {
                "source": "gpm",
                "status": "success",
                "date": target_date,
                "quality_status": validation["status"],
                "record": record,
            }
        except Exception as exc:
            logger.exception("GPM daily fetch failed for %s: %s", target_date, exc)
            return {
                "source": "gpm",
                "status": "error",
                "date": target_date,
                "error": str(exc),
            }

    def _extract_halfhourly(
        self, image: Any, reference_time: datetime
    ) -> dict[str, Any]:
        ee = _ee()
        stats = image.reduceRegion(
            reducer=ee.Reducer.mean()
            .combine(ee.Reducer.max(), sharedInputs=True)
            .combine(ee.Reducer.count(), sharedInputs=True),
            geometry=self._region(),
            scale=11132,
            maxPixels=1_000_000,
            bestEffort=True,
        ).getInfo()

        obs_time_ms = image.get("system:time_start").getInfo()
        obs_time = datetime.fromtimestamp(obs_time_ms / 1000, tz=timezone.utc)

        return {
            "observation_time_utc": obs_time.isoformat(),
            "reference_time_utc": reference_time.isoformat(),
            "region": "Accra",
            "dataset": GPM_COLLECTION,
            "precipitation_rate_mm_hr": stats.get("precipitation_mean"),
            "precipitation_max_mm_hr": stats.get("precipitation_max"),
            "valid_pixel_count": stats.get("precipitation_count", 0),
            "bbox": ACCRA_BBOX,
            "ingested_at_utc": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def validate_record(record: dict[str, Any]) -> dict[str, Any]:
        issues: list[str] = []
        precip_fields = [
            f
            for f in record
            if "precipitation" in f and f.endswith(("_mm", "_mm_hr"))
        ]

        if record.get("valid_pixel_count", 0) == 0:
            issues.append("No valid pixels found for selected region.")

        for field in precip_fields:
            value = record.get(field)
            if value is None:
                issues.append(f"{field} is missing.")
            elif value < 0:
                issues.append(f"{field} is negative.")

        status = "passed" if not issues else "warning"
        return {"status": status, "issues": issues}

    def _write_outputs(
        self,
        record: dict[str, Any],
        quality_report: dict[str, Any],
        suffix: str,
    ) -> Path:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)

        json_path = self.raw_dir / f"gpm_{suffix}.json"
        report_path = self.report_dir / f"gpm_quality_{suffix}.json"

        json_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        report_path.write_text(json.dumps(quality_report, indent=2), encoding="utf-8")
        logger.info("GPM outputs written: %s", json_path)
        return json_path

    def _write_missing_report(self, reference: str) -> dict[str, Any]:
        self.report_dir.mkdir(parents=True, exist_ok=True)
        report = {
            "reference": reference,
            "dataset": GPM_COLLECTION,
            "status": "missing_data",
            "message": "No GPM IMERG granules available for the requested window.",
            "ingested_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        safe_name = reference.replace(":", "-")
        report_path = self.report_dir / f"gpm_quality_{safe_name}.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report
