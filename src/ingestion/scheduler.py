"""
APScheduler-based orchestration for live data ingestion pipelines.

Schedules CHIRPS daily fetch, GPM IMERG refresh, and river gauge polling.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.ingestion.chirps_live import ChirpsLiveIngester
from src.ingestion.gpm_live import GpmLiveIngester
from src.ingestion.river_gauges import RiverGaugeClient
from src.monitoring.data_health import DataHealthMonitor

logger = logging.getLogger("nfcc.ingestion.scheduler")


class IngestionScheduler:
    """Coordinate scheduled ingestion jobs and health monitoring."""

    def __init__(
        self,
        chirps: Optional[ChirpsLiveIngester] = None,
        gpm: Optional[GpmLiveIngester] = None,
        gauges: Optional[RiverGaugeClient] = None,
        health: Optional[DataHealthMonitor] = None,
    ) -> None:
        self.chirps = chirps or ChirpsLiveIngester()
        self.gpm = gpm or GpmLiveIngester()
        self.gauges = gauges or RiverGaugeClient()
        self.health = health or DataHealthMonitor()
        self._scheduler = BackgroundScheduler(timezone="UTC")
        self._running = False

    def _wrap_job(self, name: str, func: Callable[[], dict[str, Any]]) -> Callable:
        def job() -> None:
            logger.info("Starting scheduled job: %s", name)
            try:
                result = func()
                self.health.record_ingestion_result(result)
                logger.info("Job %s completed: %s", name, result.get("status"))
            except Exception as exc:
                logger.exception("Job %s failed: %s", name, exc)
                self.health.record_ingestion_result(
                    {"source": name, "status": "error", "error": str(exc)}
                )

        return job

    def register_jobs(self) -> None:
        """Register default ingestion schedules."""
        self._scheduler.add_job(
            self._wrap_job("chirps", self.chirps.fetch_daily),
            CronTrigger(hour=8, minute=0),
            id="chirps_daily",
            replace_existing=True,
            name="CHIRPS daily rainfall",
        )
        self._scheduler.add_job(
            self._wrap_job("gpm", self.gpm.fetch_latest),
            IntervalTrigger(hours=4),
            id="gpm_refresh",
            replace_existing=True,
            name="GPM IMERG refresh",
        )
        self._scheduler.add_job(
            self._wrap_job("river_gauges", self.gauges.fetch_gauge_readings),
            IntervalTrigger(minutes=15),
            id="river_gauges_poll",
            replace_existing=True,
            name="River gauge polling",
        )
        self._scheduler.add_job(
            self.health.get_dashboard,
            IntervalTrigger(minutes=30),
            id="data_health_dashboard",
            replace_existing=True,
            name="Data health dashboard refresh",
        )
        logger.info("Registered %d ingestion jobs", len(self._scheduler.get_jobs()))

    def start(self, register_defaults: bool = True) -> None:
        """Start the background scheduler."""
        if self._running:
            return
        if register_defaults:
            self.register_jobs()
        self._scheduler.start()
        self._running = True
        logger.info("Ingestion scheduler started")

    def stop(self, wait: bool = True) -> None:
        """Shut down the scheduler."""
        if not self._running:
            return
        self._scheduler.shutdown(wait=wait)
        self._running = False
        logger.info("Ingestion scheduler stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    def run_job_now(self, source: str) -> dict[str, Any]:
        """Manually trigger an ingestion job."""
        jobs = {
            "chirps": self.chirps.fetch_daily,
            "gpm": self.gpm.fetch_latest,
            "river_gauges": self.gauges.fetch_gauge_readings,
            "health": self.health.get_dashboard,
        }
        if source not in jobs:
            raise ValueError(f"Unknown source: {source}. Choose from {list(jobs)}")
        result = jobs[source]()
        if source != "health":
            self.health.record_ingestion_result(result)
        return result

    def list_jobs(self) -> list[dict[str, Any]]:
        """Return metadata for all scheduled jobs."""
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run": (
                    next_run.isoformat()
                    if (next_run := getattr(job, "next_run_time", None))
                    else None
                ),
            }
            for job in self._scheduler.get_jobs()
        ]
