"""Unit tests for live data ingestion pipelines."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.ingestion.chirps_live import ChirpsLiveIngester
from src.ingestion.gpm_live import GpmLiveIngester
from src.ingestion.river_gauges import RiverGaugeClient
from src.ingestion.scheduler import IngestionScheduler
from src.monitoring.data_health import DataHealthMonitor


@pytest.fixture
def tmp_ingestion_dirs(tmp_path):
    """Isolated raw/report directories for ingestion tests."""
    raw_chirps = tmp_path / "raw" / "chirps"
    raw_gpm = tmp_path / "raw" / "gpm"
    raw_gauges = tmp_path / "raw" / "river_gauges"
    report_dir = tmp_path / "reports" / "data_quality"
    health_dir = tmp_path / "reports" / "data_health"
    for d in (raw_chirps, raw_gpm, raw_gauges, report_dir, health_dir):
        d.mkdir(parents=True)
    return {
        "raw_chirps": raw_chirps,
        "raw_gpm": raw_gpm,
        "raw_gauges": raw_gauges,
        "report_dir": report_dir,
        "health_dir": health_dir,
        "base": tmp_path,
    }


class TestChirpsLiveIngester:
    def test_validate_record_passed(self):
        record = {
            "valid_pixel_count": 100,
            "precipitation_mean_mm": 5.2,
            "precipitation_min_mm": 0.0,
            "precipitation_max_mm": 12.0,
        }
        result = ChirpsLiveIngester.validate_record(record)
        assert result["status"] == "passed"
        assert result["issues"] == []

    def test_validate_record_warning_on_missing_pixels(self):
        record = {
            "valid_pixel_count": 0,
            "precipitation_mean_mm": None,
            "precipitation_min_mm": None,
            "precipitation_max_mm": None,
        }
        result = ChirpsLiveIngester.validate_record(record)
        assert result["status"] == "warning"
        assert len(result["issues"]) > 0

    def test_write_outputs_creates_csv_and_report(self, tmp_ingestion_dirs):
        ingester = ChirpsLiveIngester(
            raw_dir=tmp_ingestion_dirs["raw_chirps"],
            report_dir=tmp_ingestion_dirs["report_dir"],
        )
        record = {
            "date": "2026-05-18",
            "region": "Accra",
            "dataset": "UCSB-CHG/CHIRPS/DAILY",
            "precipitation_mean_mm": 3.5,
            "precipitation_min_mm": 0.0,
            "precipitation_max_mm": 8.0,
            "valid_pixel_count": 50,
            "ingested_at_utc": "2026-05-19T08:00:00+00:00",
        }
        quality = {"status": "passed", "record": record}
        path = ingester.write_outputs(record, quality)

        assert path.exists()
        assert (tmp_ingestion_dirs["report_dir"] / "chirps_quality_2026-05-18.json").exists()

    @patch.object(ChirpsLiveIngester, "initialize")
    @patch.object(ChirpsLiveIngester, "get_image")
    @patch.object(ChirpsLiveIngester, "extract_stats")
    def test_fetch_daily_success(
        self, mock_extract, mock_get_image, mock_init, tmp_ingestion_dirs
    ):
        mock_get_image.return_value = MagicMock()
        mock_extract.return_value = {
            "date": "2026-05-18",
            "region": "Accra",
            "dataset": "UCSB-CHG/CHIRPS/DAILY",
            "precipitation_mean_mm": 2.0,
            "precipitation_min_mm": 0.0,
            "precipitation_max_mm": 5.0,
            "valid_pixel_count": 40,
            "ingested_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        ingester = ChirpsLiveIngester(
            raw_dir=tmp_ingestion_dirs["raw_chirps"],
            report_dir=tmp_ingestion_dirs["report_dir"],
        )
        result = ingester.fetch_daily("2026-05-18")
        assert result["status"] == "success"
        assert result["source"] == "chirps"

    @patch.object(ChirpsLiveIngester, "initialize")
    @patch.object(ChirpsLiveIngester, "get_image")
    def test_fetch_daily_missing_data(
        self, mock_get_image, mock_init, tmp_ingestion_dirs
    ):
        mock_get_image.return_value = None
        ingester = ChirpsLiveIngester(
            raw_dir=tmp_ingestion_dirs["raw_chirps"],
            report_dir=tmp_ingestion_dirs["report_dir"],
        )
        result = ingester.fetch_daily("2026-05-18")
        assert result["status"] == "missing_data"

    @patch.object(ChirpsLiveIngester, "fetch_daily")
    def test_backfill_skips_existing(self, mock_fetch, tmp_ingestion_dirs):
        existing = tmp_ingestion_dirs["raw_chirps"] / "chirps_daily_2026-05-18.csv"
        existing.write_text("date\n2026-05-18", encoding="utf-8")

        ingester = ChirpsLiveIngester(
            raw_dir=tmp_ingestion_dirs["raw_chirps"],
            report_dir=tmp_ingestion_dirs["report_dir"],
        )
        result = ingester.backfill("2026-05-18", "2026-05-18", skip_existing=True)
        assert result["skipped"] == 1
        assert result["processed"] == 0
        mock_fetch.assert_not_called()


class TestGpmLiveIngester:
    def test_validate_record_passed(self):
        record = {
            "valid_pixel_count": 80,
            "precipitation_rate_mm_hr": 1.5,
            "precipitation_max_mm_hr": 3.0,
        }
        result = GpmLiveIngester.validate_record(record)
        assert result["status"] == "passed"

    @patch.object(GpmLiveIngester, "initialize")
    @patch.object(GpmLiveIngester, "_collection_for_window")
    def test_fetch_latest_missing_data(
        self, mock_collection, mock_init, tmp_ingestion_dirs
    ):
        mock_col = MagicMock()
        mock_col.size.return_value.getInfo.return_value = 0
        mock_collection.return_value = mock_col

        ingester = GpmLiveIngester(
            raw_dir=tmp_ingestion_dirs["raw_gpm"],
            report_dir=tmp_ingestion_dirs["report_dir"],
        )
        result = ingester.fetch_latest()
        assert result["status"] == "missing_data"


class TestRiverGaugeClient:
    def test_validate_readings(self):
        readings = [
            {
                "station_id": "akosombo",
                "water_level_m": 75.0,
                "flow_rate_m3s": 1200.0,
            }
        ]
        result = RiverGaugeClient.validate_readings(readings)
        assert result["status"] == "passed"

    @patch("src.ingestion.river_gauges.requests.get")
    def test_fetch_gauge_readings_success(self, mock_get, tmp_ingestion_dirs):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "stations": [
                {
                    "id": "akosombo",
                    "name": "Akosombo",
                    "river": "Volta",
                    "water_level_m": 74.5,
                    "flow_rate_m3s": 1100,
                    "timestamp": "2026-05-19T10:00:00Z",
                }
            ]
        }
        mock_get.return_value = mock_response

        client = RiverGaugeClient(
            raw_dir=tmp_ingestion_dirs["raw_gauges"],
            report_dir=tmp_ingestion_dirs["report_dir"],
        )
        result = client.fetch_gauge_readings()
        assert result["status"] == "success"
        assert result["station_count"] == 1
        assert (tmp_ingestion_dirs["raw_gauges"] / "latest.json").exists()

    @patch("src.ingestion.river_gauges.requests.get")
    def test_graceful_degradation_uses_cache(self, mock_get, tmp_ingestion_dirs):
        mock_get.side_effect = requests.ConnectionError("connection refused")

        cache = {
            "status": "success",
            "readings": [{"station_id": "kpong", "water_level_m": 20.0}],
            "ingested_at_utc": "2026-05-19T08:00:00+00:00",
        }
        cache_path = tmp_ingestion_dirs["raw_gauges"] / "latest.json"
        cache_path.write_text(json.dumps(cache), encoding="utf-8")

        client = RiverGaugeClient(
            raw_dir=tmp_ingestion_dirs["raw_gauges"],
            report_dir=tmp_ingestion_dirs["report_dir"],
        )
        result = client.fetch_gauge_readings()
        assert result["status"] == "degraded"
        assert result["from_cache"] is True

    @patch("src.ingestion.river_gauges.requests.get")
    def test_unavailable_without_cache(self, mock_get, tmp_ingestion_dirs):
        mock_get.side_effect = requests.Timeout("timeout")
        client = RiverGaugeClient(
            raw_dir=tmp_ingestion_dirs["raw_gauges"],
            report_dir=tmp_ingestion_dirs["report_dir"],
        )
        result = client.fetch_gauge_readings()
        assert result["status"] == "unavailable"


class TestDataHealthMonitor:
    def test_check_delays_triggers_alert(self, tmp_ingestion_dirs):
        stale_csv = tmp_ingestion_dirs["raw_chirps"] / "chirps_daily_2020-01-01.csv"
        stale_csv.write_text("date\n2020-01-01", encoding="utf-8")
        # Set file mtime to 48 hours ago so staleness check fires
        old_mtime = time.time() - (48 * 3600)
        os.utime(stale_csv, (old_mtime, old_mtime))

        monitor = DataHealthMonitor(
            health_dir=tmp_ingestion_dirs["health_dir"],
            thresholds={"chirps": 1, "gpm": 6, "river_gauges": 2},
            raw_chirps=tmp_ingestion_dirs["raw_chirps"],
            raw_gpm=tmp_ingestion_dirs["raw_gpm"],
            raw_gauges=tmp_ingestion_dirs["raw_gauges"],
            quality_dir=tmp_ingestion_dirs["report_dir"],
        )
        alerts = monitor.check_delays()
        chirps_alerts = [a for a in alerts if a["source"] == "chirps"]
        assert len(chirps_alerts) == 1
        assert chirps_alerts[0]["severity"] == "warning"

    def test_degradation_state_healthy(self, tmp_ingestion_dirs):
        now = datetime.now(timezone.utc).isoformat()
        gpm_path = tmp_ingestion_dirs["raw_gpm"] / "gpm_latest.json"
        gpm_path.write_text(json.dumps({"ingested_at_utc": now}), encoding="utf-8")

        gauge_cache = tmp_ingestion_dirs["raw_gauges"] / "latest.json"
        gauge_cache.write_text(
            json.dumps({"ingested_at_utc": now, "status": "success"}),
            encoding="utf-8",
        )
        chirps_csv = tmp_ingestion_dirs["raw_chirps"] / "chirps_daily_2026-05-18.csv"
        chirps_csv.write_text("date\n2026-05-18", encoding="utf-8")

        with patch.object(DataHealthMonitor, "_chirps_status") as mock_chirps, patch.object(
            DataHealthMonitor, "_gpm_status"
        ) as mock_gpm, patch.object(
            DataHealthMonitor, "_river_gauge_status"
        ) as mock_gauges:
            healthy = {
                "available": True,
                "delayed": False,
                "degraded": False,
                "hours_since_update": 0.5,
                "threshold_hours": 36,
                "last_update_utc": now,
            }
            mock_chirps.return_value = {**healthy, "source": "chirps"}
            mock_gpm.return_value = {**healthy, "source": "gpm"}
            mock_gauges.return_value = {**healthy, "source": "river_gauges"}

            monitor = DataHealthMonitor(health_dir=tmp_ingestion_dirs["health_dir"])
            state = monitor.get_degradation_state()
            assert state["overall_status"] == "healthy"

    def test_dashboard_persisted(self, tmp_ingestion_dirs):
        monitor = DataHealthMonitor(health_dir=tmp_ingestion_dirs["health_dir"])
        dashboard = monitor.get_dashboard()
        assert dashboard["dashboard"] == "data_health"
        assert (tmp_ingestion_dirs["health_dir"] / "latest.json").exists()


class TestIngestionScheduler:
    def test_register_jobs(self):
        scheduler = IngestionScheduler()
        scheduler.register_jobs()
        jobs = scheduler.list_jobs()
        ids = {j["id"] for j in jobs}
        assert "chirps_daily" in ids
        assert "gpm_refresh" in ids
        assert "river_gauges_poll" in ids
        assert "data_health_dashboard" in ids

    def test_run_job_now_chirps(self):
        scheduler = IngestionScheduler()
        with patch.object(
            scheduler.chirps, "fetch_daily", return_value={"source": "chirps", "status": "success"}
        ):
            result = scheduler.run_job_now("chirps")
        assert result["status"] == "success"

    def test_run_job_now_unknown_source(self):
        scheduler = IngestionScheduler()
        with pytest.raises(ValueError, match="Unknown source"):
            scheduler.run_job_now("invalid")
