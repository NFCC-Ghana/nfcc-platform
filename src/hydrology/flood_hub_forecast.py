"""Google Flood Hub integration - real river-forecast data for Ghana.

Built 2026-09-27 in response to a decision to actually integrate Flood
Hub, rather than leave it as a named-but-never-fetched third leg of
src/models/forecast_fusion.py's fusion math (that module's own docstring
already documented it as a "disconnected chirps/glofas/flood_hub demo").

Ghana is confirmed covered - Flood Hub was developed at Google's Africa
Research Center in Accra, and Ghana was in the platform's original batch
of African countries. But the real Flood Forecasting API
(floodforecasting.googleapis.com) is NOT a public open API: access
requires joining a pilot waitlist (support.google.com/flood-hub, answer
16364306), and Google's own docs note approval can take "several
months." No API key exists for this project as of this writing - this is
a real, external, human action item (apply for pilot access), not
something fixable in code.

Consequently this module is honestly UNTESTED against the live API. It
is implemented as precisely as the public REST documentation
(developers.google.com/flood-forecasting/rest/v1, fetched 2026-09-27)
describes, following the exact same honest-unavailability discipline as
this codebase's other real-but-sometimes-unconfigured sources (e.g.
src/hydrology/river_level_intelligence.py's DAHITI coverage gaps):
get_flood_hub_forecast_for_district() returns {"available": False, ...}
whenever FLOOD_HUB_API_KEY isn't set - which is what happens in
production today - rather than ever fabricating a value. Wire this in
for real (into src/api/routes/situation.py's real per-district evidence,
already done below, and from there into src/models/
multi_source_confidence.py's fusion weights as a real 6th pathway, not
yet done - a separate, deliberate decision once this can actually be
validated against live data) the moment pilot access is granted.

One unverified detail flagged for whoever validates this against a real
key: Google's docs describe the API-key *requirement* but not its exact
wire format for this specific API at the time this was written. ?key=
<API_KEY> as a query parameter is implemented here as the standard
convention across other Google Cloud REST APIs (Maps, YouTube, etc.),
not confirmed against Flood Forecasting specifically - check this first
if every call 401s once a real key exists.

Real schema used below, per developers.google.com/flood-forecasting/
rest/v1 (no example JSON payloads were shown on those documentation
pages, so this follows their documented field lists/types exactly):
- POST /v1/gauges:searchGaugesByArea {regionCode, pageSize} ->
  {gauges: [{gaugeId, location: {latitude, longitude}, siteName, river,
  countryCode, qualityVerified, hasModel}], nextPageToken}
- GET /v1/gaugeModels/{gaugeId} -> {thresholds: {warningLevel,
  dangerLevel, extremeDangerLevel}, gaugeValueUnit, qualityVerified}
- GET /v1/gauges:queryGaugeForecasts?gaugeIds=...&issuedTimeStart=...
  &issuedTimeEnd=... -> {forecasts: {gaugeId: {forecasts: [{gaugeId,
  issuedTime, forecastRanges: [{value, forecastStartTime,
  forecastEndTime}]}]}}}

Risk normalization: Google's API does not expose a 0-100 risk score or
return-period label directly (confirmed via their docs) - only a raw
forecast value plus a gauge's real warningLevel/dangerLevel/
extremeDangerLevel thresholds. This module converts a raw forecast value
to a 0-100 score via piecewise-linear interpolation against those real,
per-gauge thresholds (0 at value=0, 40 at warningLevel, 75 at
dangerLevel, 100 at extremeDangerLevel, or 1.5x dangerLevel if extreme
isn't set for that gauge) - the same piecewise-curve style
src/alerts/formatter.py's calculate_score() already uses for
precipitation, grounded in Google's real per-gauge values rather than an
invented scale.
"""

from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import requests

logger = logging.getLogger("nfcc.hydrology.flood_hub")

_BASE_URL = "https://floodforecasting.googleapis.com/v1"
_API_KEY_ENV = "FLOOD_HUB_API_KEY"

# 65km matches the same real-world "is this actually useful for this
# district" proximity threshold already applied to DAHITI station
# coverage elsewhere in this codebase.
_MAX_GAUGE_DISTANCE_KM = 65.0

# In-process cache only, not persisted - Google's own docs warn against
# caching *search results* "for long periods" since gauges are
# occasionally added/removed; a few hours in memory is a reasonable
# middle ground, matching this codebase's other real API clients (e.g.
# smap_soil_moisture.py's 3h cache).
_CACHE_TTL_HOURS = 6
_gauge_cache: Dict[str, "GaugeInfo"] = {}
_gauge_cache_at: Optional[datetime] = None


@dataclass(frozen=True)
class GaugeInfo:
    gauge_id: str
    lat: float
    lon: float
    site_name: str
    river: str
    quality_verified: bool
    has_model: bool


def _api_key() -> Optional[str]:
    key = os.getenv(_API_KEY_ENV, "").strip()
    return key or None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance - the same formula already used by
    src/hydrology/river_level_intelligence.py to find the nearest real
    DAHITI station to a district, applied here identically to find the
    nearest real Flood Hub gauge."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def _fetch_ghana_gauges() -> Dict[str, GaugeInfo]:
    """All real Flood Hub gauges Google has for Ghana (regionCode=GH),
    cached in-process for _CACHE_TTL_HOURS. Returns {} whenever no API
    key is configured or the request fails - callers must treat that as
    "unavailable," never as "zero real gauges exist."""
    global _gauge_cache, _gauge_cache_at

    now = datetime.now(timezone.utc)
    if _gauge_cache_at and (now - _gauge_cache_at) < timedelta(hours=_CACHE_TTL_HOURS):
        return _gauge_cache

    key = _api_key()
    if key is None:
        return {}

    try:
        resp = requests.post(
            f"{_BASE_URL}/gauges:searchGaugesByArea",
            params={"key": key},
            json={"regionCode": "GH", "pageSize": 500},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        logger.warning(f"Flood Hub gauge search failed: {e}")
        return {}

    gauges: Dict[str, GaugeInfo] = {}
    for g in data.get("gauges", []):
        loc = g.get("location") or {}
        gauge_id = g.get("gaugeId")
        if not gauge_id or "latitude" not in loc or "longitude" not in loc:
            continue
        gauges[gauge_id] = GaugeInfo(
            gauge_id=gauge_id,
            lat=loc["latitude"],
            lon=loc["longitude"],
            site_name=g.get("siteName", ""),
            river=g.get("river", ""),
            quality_verified=bool(g.get("qualityVerified", False)),
            has_model=bool(g.get("hasModel", False)),
        )

    _gauge_cache = gauges
    _gauge_cache_at = now
    return gauges


def _nearest_gauge(lat: float, lon: float) -> Optional[GaugeInfo]:
    """Nearest real Flood Hub gauge with a hydrological model to (lat,
    lon), within _MAX_GAUGE_DISTANCE_KM - None if the search API is
    unavailable, no gauge has a model, or the nearest one is too far to
    be meaningfully representative of this district."""
    gauges = _fetch_ghana_gauges()
    candidates = [g for g in gauges.values() if g.has_model]
    if not candidates:
        return None
    nearest = min(candidates, key=lambda g: _haversine_km(lat, lon, g.lat, g.lon))
    if _haversine_km(lat, lon, nearest.lat, nearest.lon) > _MAX_GAUGE_DISTANCE_KM:
        return None
    return nearest


def _fetch_thresholds(gauge_id: str) -> Optional[Dict[str, float]]:
    key = _api_key()
    if key is None:
        return None
    try:
        resp = requests.get(
            f"{_BASE_URL}/gaugeModels/{gauge_id}",
            params={"key": key},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("thresholds")
    except requests.exceptions.RequestException as e:
        logger.warning(f"Flood Hub threshold fetch failed for {gauge_id}: {e}")
        return None


def _fetch_latest_forecast_value(gauge_id: str) -> Optional[float]:
    key = _api_key()
    if key is None:
        return None
    try:
        resp = requests.get(
            f"{_BASE_URL}/gauges:queryGaugeForecasts",
            params={"key": key, "gaugeIds": [gauge_id]},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        logger.warning(f"Flood Hub forecast fetch failed for {gauge_id}: {e}")
        return None

    entry = data.get("forecasts", {}).get(gauge_id, {})
    forecasts = entry.get("forecasts", [])
    if not forecasts:
        return None
    # Most recently issued forecast's first (nearest-term) range - the
    # "right now" reading this platform's other per-source evidence
    # values (rainfall/river/soil/satellite) each already represent, not
    # a full multi-day series.
    latest = max(forecasts, key=lambda f: f.get("issuedTime", ""))
    ranges = latest.get("forecastRanges", [])
    if not ranges:
        return None
    return ranges[0].get("value")


def _normalize_risk(value: float, thresholds: Dict[str, float]) -> Optional[float]:
    """Real per-gauge warningLevel/dangerLevel/extremeDangerLevel
    (Google's own model thresholds, never invented here) -> a 0-100
    score via piecewise-linear interpolation - the same curve style
    src/alerts/formatter.py's calculate_score() already uses for
    precipitation. Returns None (honest unavailability, not a guess)
    when this gauge's thresholds are missing or degenerate."""
    warning = thresholds.get("warningLevel")
    danger = thresholds.get("dangerLevel")
    extreme = thresholds.get("extremeDangerLevel")
    if extreme is None and danger is not None:
        extreme = danger * 1.5

    if warning is None or danger is None or extreme is None:
        return None
    if not (0 < warning < danger < extreme):
        return None

    if value <= 0:
        return 0.0
    if value < warning:
        return round(40.0 * (value / warning), 1)
    if value < danger:
        return round(40.0 + 35.0 * (value - warning) / (danger - warning), 1)
    if value < extreme:
        return round(75.0 + 25.0 * (value - danger) / (extreme - danger), 1)
    return 100.0


def get_flood_hub_forecast_for_district(lat: float, lon: float) -> Dict:
    """Real Google Flood Hub river forecast nearest (lat, lon), as a
    0-100 risk score matching src/models/forecast_fusion.py's
    flood_hub_risk input shape - or an honest {"available": False, ...}
    when: the API key isn't configured (true in production today - see
    this module's docstring for why), the request fails, no gauge with a
    real hydrological model exists within range, or that gauge's
    thresholds/forecast are missing. Never fabricates a value."""
    if _api_key() is None:
        return {
            "available": False,
            "reason": "FLOOD_HUB_API_KEY not configured (Flood Forecasting API pilot access not yet granted)",
        }

    gauge = _nearest_gauge(lat, lon)
    if gauge is None:
        return {
            "available": False,
            "reason": f"No real Flood Hub gauge with a hydrological model within {_MAX_GAUGE_DISTANCE_KM:.0f}km",
        }

    thresholds = _fetch_thresholds(gauge.gauge_id)
    value = _fetch_latest_forecast_value(gauge.gauge_id)
    if thresholds is None or value is None:
        return {
            "available": False,
            "reason": f"Gauge {gauge.gauge_id} ({gauge.site_name}) found but its forecast/thresholds are unavailable",
            "gauge_id": gauge.gauge_id,
            "site_name": gauge.site_name,
        }

    risk = _normalize_risk(value, thresholds)
    if risk is None:
        return {
            "available": False,
            "reason": f"Gauge {gauge.gauge_id} ({gauge.site_name}) has no usable warning/danger thresholds",
            "gauge_id": gauge.gauge_id,
            "site_name": gauge.site_name,
        }

    return {
        "available": True,
        "flood_hub_risk": risk,
        "gauge_id": gauge.gauge_id,
        "site_name": gauge.site_name,
        "river": gauge.river,
        "raw_value": value,
        "source": "Google Flood Hub",
    }
