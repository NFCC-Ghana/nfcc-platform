"""
Data quality monitoring dashboard and delay alerting.

Tracks ingestion freshness across CHIRPS, GPM IMERG, and river gauges.
Triggers alerts on stale data and reports graceful degradation state.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("nfcc.monitoring.data_health")

BASE_DIR = Path(__file__).resolve().parents[2]
HEALTH_DIR = BASE_DIR / "reports" / "data_health"
QUALITY_DIR = BASE_DIR / "reports" / "data_quality"
RAW_CHIRPS = BASE_DIR / "data" / "raw" / "chirps"
RAW_GPM = BASE_DIR / "data" / "raw" / "gpm"
RAW_GAUGES = BASE_DIR / "data" / "raw" / "river_gauges"

# Maximum acceptable staleness before alerting (hours)
DEFAULT_THRESHOLDS = {
    "chirps": 36,
    "gpm": 6,
    "river_gauges": 2,
}


class DataHealthMonitor:
    """Monitor ingestion pipeline health and surface dashboard metrics."""

    def __init__(
        self,
        health_dir: Path = HEALTH_DIR,
        thresholds: Optional[dict[str, int]] = None,
        raw_chirps: Path = RAW_CHIRPS,
        raw_gpm: Path = RAW_GPM,
        raw_gauges: Path = RAW_GAUGES,
        quality_dir: Path = QUALITY_DIR,
    ) -> None:
        self.health_dir = health_dir
        self.thresholds = thresholds or DEFAULT_THRESHOLDS.copy()
        self.raw_chirps = raw_chirps
        self.raw_gpm = raw_gpm
        self.raw_gauges = raw_gauges
        self.quality_dir = quality_dir
        self._alerts: list[dict[str, Any]] = []

    def _parse_timestamp(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _hours_since(self, ts: Optional[datetime]) -> Optional[float]:
        if ts is None:
            return None
        delta = datetime.now(timezone.utc) - ts
        return delta.total_seconds() / 3600

    def _latest_file_mtime(self, directory: Path, pattern: str) -> Optional[datetime]:
        if not directory.exists():
            return None
        files = sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime)
        if not files:
            return None
        return datetime.fromtimestamp(
            files[-1].stat().st_mtime, tz=timezone.utc
        )

    def _chirps_status(self) -> dict[str, Any]:
        latest_csv = self._latest_file_mtime(self.raw_chirps, "chirps_daily_*.csv")
        hours_stale = self._hours_since(latest_csv)
        threshold = self.thresholds["chirps"]
        delayed = hours_stale is not None and hours_stale > threshold
        unavailable = latest_csv is None

        return {
            "source": "chirps",
            "available": not unavailable,
            "last_update_utc": latest_csv.isoformat() if latest_csv else None,
            "hours_since_update": round(hours_stale, 2) if hours_stale else None,
            "threshold_hours": threshold,
            "delayed": delayed,
            "degraded": unavailable,
        }

    def _gpm_status(self) -> dict[str, Any]:
        latest = self.raw_gpm / "gpm_latest.json"
        last_update = None
        if latest.exists():
            try:
                data = json.loads(latest.read_text(encoding="utf-8"))
                last_update = self._parse_timestamp(
                    data.get("ingested_at_utc")
                    or data.get("observation_time_utc")
                )
            except (json.JSONDecodeError, OSError):
                last_update = self._latest_file_mtime(self.raw_gpm, "gpm_*.json")
        else:
            last_update = self._latest_file_mtime(self.raw_gpm, "gpm_*.json")

        hours_stale = self._hours_since(last_update)
        threshold = self.thresholds["gpm"]
        delayed = hours_stale is not None and hours_stale > threshold
        unavailable = last_update is None

        return {
            "source": "gpm",
            "available": not unavailable,
            "last_update_utc": last_update.isoformat() if last_update else None,
            "hours_since_update": round(hours_stale, 2) if hours_stale else None,
            "threshold_hours": threshold,
            "delayed": delayed,
            "degraded": unavailable,
        }

    def _river_gauge_status(self) -> dict[str, Any]:
        cache = self.raw_gauges / "latest.json"
        last_update = None
        degraded = False

        if cache.exists():
            try:
                data = json.loads(cache.read_text(encoding="utf-8"))
                last_update = self._parse_timestamp(data.get("ingested_at_utc"))
                degraded = data.get("status") == "degraded" or data.get(
                    "from_cache", False
                )
            except (json.JSONDecodeError, OSError):
                pass

        hours_stale = self._hours_since(last_update)
        threshold = self.thresholds["river_gauges"]
        delayed = hours_stale is not None and hours_stale > threshold
        unavailable = last_update is None

        return {
            "source": "river_gauges",
            "available": not unavailable,
            "last_update_utc": last_update.isoformat() if last_update else None,
            "hours_since_update": round(hours_stale, 2) if hours_stale else None,
            "threshold_hours": threshold,
            "delayed": delayed,
            "degraded": degraded or unavailable,
        }

    def check_delays(self) -> list[dict[str, Any]]:
        """Return alert records for sources exceeding staleness thresholds."""
        alerts: list[dict[str, Any]] = []
        for status in self.get_source_statuses():
            if status["delayed"]:
                alert = {
                    "source": status["source"],
                    "severity": "warning",
                    "message": (
                        f"{status['source']} data is {status['hours_since_update']}h "
                        f"stale (threshold: {status['threshold_hours']}h)"
                    ),
                    "hours_since_update": status["hours_since_update"],
                    "threshold_hours": status["threshold_hours"],
                    "triggered_at_utc": datetime.now(timezone.utc).isoformat(),
                }
                alerts.append(alert)
                logger.warning(alert["message"])
        self._alerts = alerts
        return alerts

    def get_degradation_state(self) -> dict[str, Any]:
        """Summarize which sources are unavailable or serving stale cache."""
        statuses = self.get_source_statuses()
        degraded_sources = [s["source"] for s in statuses if s["degraded"]]
        delayed_sources = [s["source"] for s in statuses if s["delayed"]]

        if not degraded_sources and not delayed_sources:
            overall = "healthy"
        elif degraded_sources:
            overall = "degraded"
        else:
            overall = "delayed"

        return {
            "overall_status": overall,
            "degraded_sources": degraded_sources,
            "delayed_sources": delayed_sources,
            "forecasting_impact": self._forecasting_impact(degraded_sources),
            "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _forecasting_impact(degraded: list[str]) -> str:
        if not degraded:
            return "none"
        if len(degraded) >= 2:
            return "high — multiple inputs unavailable; fusion weights should shift"
        if "gpm" in degraded:
            return "moderate — near-real-time rainfall unavailable; CHIRPS fallback"
        if "river_gauges" in degraded:
            return "moderate — hydrological validation unavailable"
        return "low — CHIRPS backfill available"

    def get_source_statuses(self) -> list[dict[str, Any]]:
        return [
            self._chirps_status(),
            self._gpm_status(),
            self._river_gauge_status(),
        ]

    def get_dashboard(self) -> dict[str, Any]:
        """Build data quality monitoring dashboard payload."""
        sources = self.get_source_statuses()
        alerts = self.check_delays()
        degradation = self.get_degradation_state()

        quality_reports = self._recent_quality_reports()

        dashboard = {
            "dashboard": "data_health",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "overall_status": degradation["overall_status"],
            "sources": sources,
            "alerts": alerts,
            "degradation": degradation,
            "recent_quality_reports": quality_reports,
        }
        self._persist_dashboard(dashboard)
        return dashboard

    def _recent_quality_reports(self, limit: int = 10) -> list[dict[str, Any]]:
        if not self.quality_dir.exists():
            return []
        reports = sorted(
            self.quality_dir.glob("*_quality_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:limit]
        result = []
        for path in reports:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                result.append({"file": path.name, "status": data.get("status")})
            except (json.JSONDecodeError, OSError):
                result.append({"file": path.name, "status": "unreadable"})
        return result

    def _persist_dashboard(self, dashboard: dict[str, Any]) -> Path:
        self.health_dir.mkdir(parents=True, exist_ok=True)
        path = self.health_dir / "latest.json"
        path.write_text(json.dumps(dashboard, indent=2), encoding="utf-8")
        return path

    def record_ingestion_result(self, result: dict[str, Any]) -> None:
        """Update health state after an ingestion job completes."""
        source = result.get("source", "unknown")
        status = result.get("status", "unknown")
        logger.info("Ingestion result recorded: %s → %s", source, status)
        self.get_dashboard()
