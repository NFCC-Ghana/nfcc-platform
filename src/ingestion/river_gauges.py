"""
Ghana Hydrological Services Department (HSD) river gauge integration.

Fetches real-time water levels and flow rates with graceful degradation
when the API is unavailable.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests

logger = logging.getLogger("nfcc.ingestion.river_gauges")

HSD_API_BASE_URL = os.getenv(
    "HSD_API_BASE_URL", "https://api.hsd.gov.gh/v1"
)
HSD_API_KEY = os.getenv("HSD_API_KEY", "")
HSD_API_TIMEOUT = int(os.getenv("HSD_API_TIMEOUT_SECONDS", "30"))

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / "data" / "raw" / "river_gauges"
REPORT_DIR = BASE_DIR / "reports" / "data_quality"
CACHE_PATH = RAW_DIR / "latest.json"

# Primary Ghana monitoring stations (Volta basin and Accra catchments)
DEFAULT_STATIONS = [
    {"id": "akosombo", "name": "Akosombo", "river": "Volta"},
    {"id": "kpong", "name": "Kpong", "river": "Volta"},
    {"id": "bui", "name": "Bui Dam", "river": "Black Volta"},
    {"id": "weija", "name": "Weija", "river": "Densu"},
    {"id": "nsawam", "name": "Nsawam", "river": "Densu"},
]


class RiverGaugeClient:
    """Client for HSD river gauge API with caching and degradation."""

    def __init__(
        self,
        base_url: str = HSD_API_BASE_URL,
        api_key: str = HSD_API_KEY,
        timeout: int = HSD_API_TIMEOUT,
        raw_dir: Path = RAW_DIR,
        report_dir: Path = REPORT_DIR,
        cache_path: Optional[Path] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.raw_dir = raw_dir
        self.report_dir = report_dir
        self.cache_path = cache_path or (raw_dir / "latest.json")

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _request(self, path: str) -> tuple[Optional[dict[str, Any]], Optional[str]]:
        url = f"{self.base_url}{path}"
        try:
            response = requests.get(
                url, headers=self._headers(), timeout=self.timeout
            )
            response.raise_for_status()
            return response.json(), None
        except requests.RequestException as exc:
            logger.warning("HSD API request failed (%s): %s", url, exc)
            return None, str(exc)

    def _normalize_readings(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Normalize API response to a consistent station reading schema."""
        stations = payload.get("stations") or payload.get("data") or []
        readings: list[dict[str, Any]] = []

        for item in stations:
            readings.append(
                {
                    "station_id": item.get("id") or item.get("station_id"),
                    "station_name": item.get("name") or item.get("station_name"),
                    "river": item.get("river"),
                    "water_level_m": item.get("water_level_m")
                    or item.get("level_m")
                    or item.get("water_level"),
                    "flow_rate_m3s": item.get("flow_rate_m3s")
                    or item.get("discharge_m3s")
                    or item.get("flow_rate"),
                    "timestamp_utc": item.get("timestamp")
                    or item.get("observed_at")
                    or item.get("timestamp_utc"),
                }
            )
        return readings

    def _load_cache(self) -> Optional[dict[str, Any]]:
        if not self.cache_path.exists():
            return None
        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read gauge cache: %s", exc)
            return None

    def _save_cache(self, payload: dict[str, Any]) -> None:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

    def _write_quality_report(
        self, status: str, details: dict[str, Any]
    ) -> dict[str, Any]:
        self.report_dir.mkdir(parents=True, exist_ok=True)
        report = {
            "source": "river_gauges",
            "dataset": "HSD_API",
            "status": status,
            "ingested_at_utc": datetime.now(timezone.utc).isoformat(),
            **details,
        }
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        report_path = self.report_dir / f"river_gauge_quality_{ts}.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

    @staticmethod
    def validate_readings(readings: list[dict[str, Any]]) -> dict[str, Any]:
        issues: list[str] = []
        for reading in readings:
            sid = reading.get("station_id", "unknown")
            level = reading.get("water_level_m")
            flow = reading.get("flow_rate_m3s")

            if level is None:
                issues.append(f"{sid}: water_level_m missing")
            elif level < 0:
                issues.append(f"{sid}: water_level_m negative")

            if flow is not None and flow < 0:
                issues.append(f"{sid}: flow_rate_m3s negative")

        status = "passed" if not issues else "warning"
        return {"status": status, "issues": issues}

    def fetch_gauge_readings(
        self, station_ids: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """
        Fetch real-time water levels from HSD API.

        Falls back to cached readings on API failure (graceful degradation).
        """
        path = "/gauges/current"
        if station_ids:
            path += f"?stations={','.join(station_ids)}"

        payload, error = self._request(path)
        ingested_at = datetime.now(timezone.utc).isoformat()

        if payload is None:
            cached = self._load_cache()
            if cached:
                degraded = {
                    **cached,
                    "status": "degraded",
                    "degraded_reason": error,
                    "ingested_at_utc": ingested_at,
                    "from_cache": True,
                }
                self._write_quality_report(
                    "degraded",
                    {"error": error, "station_count": len(cached.get("readings", []))},
                )
                return degraded

            report = self._write_quality_report("unavailable", {"error": error})
            return {
                "source": "river_gauges",
                "status": "unavailable",
                "error": error,
                "report": report,
            }

        readings = self._normalize_readings(payload)
        validation = self.validate_readings(readings)
        result = {
            "source": "river_gauges",
            "status": "success",
            "quality_status": validation["status"],
            "readings": readings,
            "station_count": len(readings),
            "ingested_at_utc": ingested_at,
            "from_cache": False,
        }
        self._save_cache(result)
        self._write_quality_report(
            validation["status"],
            {"station_count": len(readings), "validation": validation},
        )
        return result

    def fetch_flow_rates(
        self, station_ids: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """Fetch flow-rate monitoring data (subset of gauge readings)."""
        result = self.fetch_gauge_readings(station_ids=station_ids)
        if result["status"] not in ("success", "degraded"):
            return result

        flow_readings = [
            {
                "station_id": r["station_id"],
                "station_name": r.get("station_name"),
                "flow_rate_m3s": r.get("flow_rate_m3s"),
                "timestamp_utc": r.get("timestamp_utc"),
            }
            for r in result.get("readings", [])
            if r.get("flow_rate_m3s") is not None
        ]

        return {
            **result,
            "flow_readings": flow_readings,
            "flow_station_count": len(flow_readings),
        }

    def list_stations(self) -> list[dict[str, str]]:
        """Return configured station metadata."""
        payload, error = self._request("/gauges/stations")
        if payload and "stations" in payload:
            return payload["stations"]
        if error:
            logger.info("Using default station list (API unavailable)")
        return DEFAULT_STATIONS
