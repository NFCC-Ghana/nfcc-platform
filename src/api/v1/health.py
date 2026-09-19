"""GET /v1/health/data-sources - priority deliverable #10's missing half.

src/api/health.py's existing GET /health already covers alert-provider
config (Twilio/WhatsApp), Redis, and the ML model - it has never reported
on the actual data sources this platform's risk assessments depend on
(Earth Engine/Sentinel-1, DAHITI, Open-Meteo, the community reports
database). This endpoint adds that missing view rather than duplicating
the existing one.

Follows src/api/health.py's own stated philosophy ("no startup network
calls") for everything except Open-Meteo: Earth Engine and DAHITI are
reported from state already computed at process startup/first use (a
boolean flag, an env var check) with no new network call, but Open-Meteo
gets one real, short-timeout live request - a request-time health check
actively verifying a live dependency is exactly what a composite health
endpoint is for (unlike the app's own startup path, which must stay fast
and can't block on a flaky external call), and Open-Meteo needs no API
key and responds quickly.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import requests
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["v1"])

_OPEN_METEO_HEALTHCHECK_URL = "https://api.open-meteo.com/v1/forecast"
_COMMUNITY_DB_PATH = Path("data/community_reports.db")


class DataSourceStatus(BaseModel):
    name: str
    status: str  # "connected" | "configured" | "not_configured" | "unavailable"
    detail: str


class DataSourceHealthResponse(BaseModel):
    overall_status: str  # "healthy" | "degraded"
    sources: List[DataSourceStatus]
    checked_at: str


def _check_earth_engine() -> DataSourceStatus:
    """Real state already computed once at process startup
    (src/hydrology/ee_auth.py via src/hydrology/sentinel_processor.py) -
    covers Sentinel-1 SAR flood detection AND CHIRPS-via-Earth-Engine
    rainfall ingestion (src/ingestion/chirps_live.py), which share the
    same underlying GEE authentication."""
    from src.hydrology.sentinel_processor import sentinel_processor

    if sentinel_processor.ee_initialized:
        return DataSourceStatus(
            name="Google Earth Engine (Sentinel-1 SAR + CHIRPS)",
            status="connected",
            detail="Authenticated - real satellite flood detection available",
        )
    return DataSourceStatus(
        name="Google Earth Engine (Sentinel-1 SAR + CHIRPS)",
        status="unavailable",
        detail="Not authenticated - falling back to simulated satellite data",
    )


def _check_dahiti() -> DataSourceStatus:
    """DAHITI_API_KEY presence (src/hydrology/dam_intelligence.py) - not
    a live call, since a live call would need a real dam to query
    against, which get_akosombo_status() already does when this endpoint
    isn't the one asking."""
    import os

    if os.getenv("DAHITI_API_KEY"):
        return DataSourceStatus(
            name="DAHITI (Lake Volta satellite altimetry)",
            status="configured",
            detail="API key present - real Akosombo/Lake Volta water levels available",
        )
    return DataSourceStatus(
        name="DAHITI (Lake Volta satellite altimetry)",
        status="not_configured",
        detail="DAHITI_API_KEY not set - register free at https://dahiti.dgfi.tum.de",
    )


def _check_open_meteo() -> DataSourceStatus:
    """The one real live call this endpoint makes - Open-Meteo needs no
    API key and responds quickly, and confirming it's actually reachable
    right now is more useful here than a static "configured" label would
    be, since every risk/forecast computation depends on it."""
    try:
        resp = requests.get(
            _OPEN_METEO_HEALTHCHECK_URL,
            params={"latitude": 5.56, "longitude": -0.21, "current": "rain"},
            timeout=5,
        )
        if resp.status_code == 200:
            return DataSourceStatus(
                name="Open-Meteo (rainfall/river forecast)",
                status="connected",
                detail="Reachable",
            )
        return DataSourceStatus(
            name="Open-Meteo (rainfall/river forecast)",
            status="unavailable",
            detail=f"Returned HTTP {resp.status_code}",
        )
    except Exception as e:
        return DataSourceStatus(
            name="Open-Meteo (rainfall/river forecast)",
            status="unavailable",
            detail=f"Request failed: {e}",
        )


def _check_river_gauges() -> DataSourceStatus:
    """src/hydrology/river_gauge_api.py's real API integration was never
    completed - self.api_key is hardcoded None (never loaded from an env
    var; no such var exists), and its configured base_url
    (hydrology.gov.gh) doesn't publicly resolve. Every reading it returns
    today comes from _generate_realistic_data() (simulated fallback).
    Reported here as not_configured rather than a live reachability
    check against a domain already established not to resolve - that
    would just add a guaranteed-timeout delay to every call of this
    endpoint for no new information."""
    return DataSourceStatus(
        name="Ghana River Gauges (Hydrological Services)",
        status="not_configured",
        detail=(
            "No API key configured and no public endpoint confirmed - "
            "src/hydrology/river_gauge_api.py currently always falls "
            "back to simulated gauge readings"
        ),
    )


def _check_community_reports_db() -> DataSourceStatus:
    """A cheap real query against the actual SQLite file
    (src/community/community_memory.py), not just a file-existence
    check - confirms the database is genuinely queryable."""
    try:
        conn = sqlite3.connect(str(_COMMUNITY_DB_PATH), timeout=3)
        # Matches the pragmas CommunityMemoryEngine._connect() applies
        # (src/community/community_memory.py) - harmless for a read-only
        # SELECT 1, but keeps every connection path to this Litestream-
        # replicated file consistent rather than one silent exception.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("SELECT 1")
        conn.close()
        return DataSourceStatus(
            name="Community reports database",
            status="connected",
            detail=str(_COMMUNITY_DB_PATH),
        )
    except Exception as e:
        return DataSourceStatus(
            name="Community reports database",
            status="unavailable",
            detail=f"Query failed: {e}",
        )


@router.get("/data-sources", response_model=DataSourceHealthResponse)
async def get_data_source_health() -> DataSourceHealthResponse:
    sources = [
        _check_earth_engine(),
        _check_dahiti(),
        _check_open_meteo(),
        _check_river_gauges(),
        _check_community_reports_db(),
    ]
    # DAHITI's "not_configured" is expected/optional (a real degraded-but-
    # functioning state, not an outage - the platform works without it,
    # just with less Akosombo evidence) - only genuine unreachability
    # marks the platform overall as degraded.
    overall = "healthy"
    if any(s.status == "unavailable" for s in sources):
        overall = "degraded"

    return DataSourceHealthResponse(
        overall_status=overall,
        sources=sources,
        checked_at=datetime.now(timezone.utc).isoformat(),
    )
