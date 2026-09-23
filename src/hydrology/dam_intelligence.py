"""Honest real-vs-unavailable dam/reservoir intelligence for the districts
this platform tracks - a disclosure layer, not a data source of its own.

This is NOT the same thing as src/models/dam_spillage.py or
src/hydrology/reservoir_intelligence.py / vra_telemetry.py:

- src/models/dam_spillage.py (via src/api/dam_router.py) is an honest,
  already-disclosed research prototype: it takes rainfall/reservoir_level/
  inflow as caller-supplied inputs (defaulting to the real 2023 Akosombo/
  Bagre event values when none are given) and every response explicitly
  says "Based on simulated data pending VRA partnership". Fine as-is,
  untouched here.
- src/hydrology/reservoir_intelligence.py and vra_telemetry.py are NOT
  disclosed the same way - _generate_reservoir_data()/
  _generate_realistic_telemetry() fabricate levels/inflow/outflow/
  "days_to_spill"/"trend" from np.random.seed(hash(dam_id)) and present
  them as this dam's current "DANGER"/"WARNING"/"NORMAL" status with no
  simulated-data disclosure at all. Neither module is imported by any API
  route today (confirmed before writing this file) - this module
  deliberately does NOT reuse their output, to avoid exactly the
  fabrication bug just fixed in the AI Decision Center
  (hackathon/app/pages/dashboard.py's render_ai_decision_center).

Two dams matter for this platform's 9 tracked districts:

Akosombo (Lake Volta, VRA-operated, Ghana) - downstream of Tema. No live
VRA telemetry exists: VRA has no public real-time API (confirmed by the
original team task, GitHub issue #20: "mock data pending VRA
partnership"). A REAL, independent source does exist though: DAHITI
(dahiti.dgfi.tum.de, Technical University of Munich), a free
satellite-altimetry water-level record covering Lake Volta (DAHITI target
id 97), via a real REST API requiring a free registered API key
(DAHITI_API_KEY env var - see https://dahiti.dgfi.tum.de for registration).
Real limitation, disclosed rather than hidden: altimetry revisit is
10-35 days depending on the satellite mission, with a 1-2 day processing
delay after each pass - the same "real but not instant" disclosure
pattern already used for Sentinel-1 SAR elsewhere in this app
(src/hydrology/sentinel_processor.py).

Bagre Dam (Burkina Faso, transboundary) and Kompienga Dam (Burkina Faso,
transboundary) - downstream of Tamale and Ho respectively. No automatable
data source exists for either. Ghana's Water Resources Commission
receives informal notice from Burkina Faso's dam operators and publishes
bulletins via press/radio, not a machine-readable feed. A 2026 systematic
review of Ghana's flood warning chain found this is a documented,
UNRESOLVED cross-border coordination gap - "Ghana's most advanced warning
platform is structurally blind to the flood trigger responsible for the
basin's most severe events" - not a missing API integration this platform
can quietly build its way around. get_bagre_status()/get_kompienga_status()
always report available=False with that specific reason, rather than
staying silent about the gap.
"""

import logging
import os
from datetime import datetime
from typing import Dict, List

import requests

from src.hydrology.altimetry_thresholds import classify_level, compute_relative_thresholds
from src.utils.http_errors import safe_error_message

logger = logging.getLogger("nfcc.hydrology.dam_intelligence")

_DAHITI_API_URL = "https://dahiti.dgfi.tum.de/api/v2/download-water-level/"
_LAKE_VOLTA_DAHITI_ID = 97  # dahiti.dgfi.tum.de target id for "Volta, Lake"

# Real downstream exposure (matches src/hydrology/reservoir_intelligence.py's
# static dam database, which is legitimate reference data even though that
# module's *dynamic* status generation is fabricated) - only districts this
# platform actually tracks that are genuinely downstream of one of these
# dams get a dam_intelligence entry; the other 6 tracked districts aren't
# exposed to either and correctly get none.
_DISTRICT_DAM_EXPOSURE = {
    "Tema": ["akosombo"],
    "Tamale": ["bagre"],
    "Ho": ["kompienga"],
}


def get_akosombo_status() -> Dict:
    """Real Lake Volta water level via DAHITI satellite altimetry, if an
    API key is configured - never fabricated when it isn't."""
    api_key = os.getenv("DAHITI_API_KEY")
    if not api_key:
        return {
            "dam": "Akosombo",
            "available": False,
            "reason": (
                "DAHITI_API_KEY not configured - free registration at "
                "https://dahiti.dgfi.tum.de gives access to real Lake "
                "Volta satellite altimetry water levels"
            ),
        }

    try:
        resp = requests.get(
            _DAHITI_API_URL,
            params={
                "api_key": api_key,
                "dahiti_id": _LAKE_VOLTA_DAHITI_ID,
                "format": "json",
            },
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()
        readings = payload.get("data") or payload.get("results") or []
        if not readings:
            return {
                "dam": "Akosombo",
                "available": False,
                "reason": "DAHITI returned no water level readings for Lake Volta",
            }
        latest = readings[-1]
        observation_date = latest.get("datetime")

        # Disclosed freshness, computed rather than left for a reviewer to
        # work out from a raw timestamp - the "timestamped" half of this
        # platform's real->traceable->validated->explainable->timestamped
        # ->actionable goal. 45 days = the disclosed worst-case revisit
        # (35 days) plus processing delay (2 days) plus an 8-day margin;
        # beyond that, treat the reading as stale enough to flag loudly
        # rather than presenting a months-old level as current.
        age_days = None
        stale = False
        if observation_date:
            try:
                obs_dt = datetime.fromisoformat(observation_date)
                age_days = (datetime.utcnow() - obs_dt).days
                stale = age_days > 45
            except ValueError:
                pass

        # Real, data-derived reservoir status - the same real percentile-
        # threshold methodology already built for river gauges
        # (src/hydrology/altimetry_thresholds.py), applied to Lake
        # Volta's own real historical DAHITI series. Without this, a
        # dam nearing/at its own historical flood-stage percentile had
        # no way to register as a real, independent flood-risk pathway
        # (src/models/multi_source_confidence.py's causal-independence
        # redesign) - it would silently look identical to a normal pool
        # level to anything consuming this data.
        elevation = latest.get("wse")
        thresholds = compute_relative_thresholds(readings)
        level_above_baseline_m = None
        status = "UNKNOWN"
        if thresholds and elevation is not None:
            classified = classify_level(elevation, thresholds)
            level_above_baseline_m = classified["level_above_baseline_m"]
            status = classified["status"]

        return {
            "dam": "Akosombo",
            "available": True,
            "water_surface_elevation_m": elevation,
            "level_above_baseline_m": level_above_baseline_m,
            "status": status,
            "uncertainty_m": latest.get("wse_u"),
            # DAHITI's real response field is "datetime" (verified against
            # the live API), not "date" as an earlier approximate summary
            # of their docs said - the wrong key silently returned None
            # here (Python dict.get(), no error) rather than failing
            # loudly, so this was live in production before being caught
            # by directly inspecting the raw response.
            "observation_date": observation_date,
            "age_days": age_days,
            "stale": stale,
            "source": "DAHITI satellite altimetry (Lake Volta)",
            "downstream_communities": ["Kpong", "Akuse", "Ada", "Tema"],
            "note": (
                "Satellite altimetry, not real-time - revisit interval "
                "depends on the satellite mission (10-35 days) with a "
                "1-2 day processing delay after each pass"
                + (
                    f". This reading is {age_days} days old, beyond the "
                    "normal revisit window - treat as an indicative "
                    "reservoir trend, not a current level."
                    if stale
                    else ""
                )
            ),
        }
    except Exception as e:
        # safe_error_message, not str(e) - see src/utils/http_errors.py's
        # docstring: this request puts the real DAHITI_API_KEY in its URL
        # query string, and requests.exceptions.HTTPError's message
        # includes that full URL - str(e) here would have put the key in
        # both Cloud Run logs and this function's live API response body.
        reason = safe_error_message(e, "DAHITI")
        logger.warning(reason)
        return {
            "dam": "Akosombo",
            "available": False,
            "reason": reason,
        }


_NAKEMBE_DAHITI_ID = 19006  # Nakembé, River - ~22.4km from Bagre Dam
_NAKEMBE_DISTANCE_KM = 22.4


def _get_bagre_upstream_proxy() -> Dict:
    """Bagre Dam sits on the Nakambé river (Burkina Faso's name for the
    White Volta, upstream of where it enters Ghana) - DAHITI has a real,
    populated satellite altimetry station on that exact river system,
    "Nakembé, River" (id 19006), only 22.4km from the dam - confirmed
    live with 98 readings, the freshest of any station this project uses
    (16 days old at the time this was found, vs. 45 for Lake Volta/White
    Volta). This is NOT official Bagre operator data (no such feed
    exists, see get_bagre_status below) - it's real upstream river level
    on the same watershed, usable as an early-warning proxy for water
    heading toward the dam and, eventually, Tamale."""
    api_key = os.getenv("DAHITI_API_KEY")
    if not api_key:
        return {"available": False, "reason": "DAHITI_API_KEY not configured"}

    try:
        resp = requests.get(
            _DAHITI_API_URL,
            params={
                "api_key": api_key,
                "dahiti_id": _NAKEMBE_DAHITI_ID,
                "format": "json",
            },
            timeout=15,
        )
        resp.raise_for_status()
        readings = resp.json().get("data") or []
        if not readings:
            return {"available": False, "reason": "No readings returned"}
        latest = readings[-1]

        elevation = latest.get("wse")
        thresholds = compute_relative_thresholds(readings)
        level_above_baseline_m = None
        status = "UNKNOWN"
        if thresholds and elevation is not None:
            classified = classify_level(elevation, thresholds)
            level_above_baseline_m = classified["level_above_baseline_m"]
            status = classified["status"]

        return {
            "available": True,
            "river": "Nakembé (upper White Volta, Burkina Faso)",
            "water_surface_elevation_m": elevation,
            "level_above_baseline_m": level_above_baseline_m,
            "status": status,
            "observation_date": latest.get("datetime"),
            "distance_km": _NAKEMBE_DISTANCE_KM,
            "source": "DAHITI satellite altimetry",
            "note": (
                "Real upstream river level, same watershed as Bagre Dam - "
                "NOT official dam operator data (none exists); a proxy "
                "signal for water conditions approaching the dam, not the "
                "reservoir's own level."
            ),
        }
    except Exception as e:
        reason = safe_error_message(e, "DAHITI (Nakembé)")
        logger.warning(reason)
        return {"available": False, "reason": reason}


def get_bagre_status() -> Dict:
    """Bagre Dam (Burkina Faso) itself has no automatable real-time data
    source - always honestly reports the dam's own status as unavailable,
    since Tamale is directly exposed to uncoordinated releases from it.
    Includes a real upstream_proxy reading where available (see
    _get_bagre_upstream_proxy) as genuinely useful supplementary
    evidence, kept structurally separate from `available` so it's never
    mistaken for official dam telemetry."""
    return {
        "dam": "Bagre",
        "available": False,
        "reason": (
            "No real-time API exists for Bagre Dam. Ghana's Water "
            "Resources Commission receives informal notice from Burkina "
            "Faso's dam operator and issues public bulletins via "
            "press/radio, not a machine-readable feed - a documented, "
            "unresolved cross-border coordination gap in Ghana's flood "
            "warning chain."
        ),
        "downstream_communities": ["Tamale", "Yendi", "Gushegu"],
        "upstream_proxy": _get_bagre_upstream_proxy(),
    }


def get_kompienga_status() -> Dict:
    """Kompienga Dam (Burkina Faso) - same cross-border gap as Bagre,
    affecting Ho."""
    return {
        "dam": "Kompienga",
        "available": False,
        "reason": (
            "No real-time API exists for Kompienga Dam. Same unresolved "
            "cross-border notification gap as Bagre Dam - Burkina Faso's "
            "dam operators do not publish a machine-readable release feed."
        ),
        "downstream_communities": ["Ho", "Jasikan"],
    }


_STATUS_FETCHERS = {
    "akosombo": get_akosombo_status,
    "bagre": get_bagre_status,
    "kompienga": get_kompienga_status,
}


def get_dam_intelligence_for_district(district: str) -> List[Dict]:
    """Real dam status entries relevant to this district's downstream
    exposure - [] for districts with no known dam exposure (6 of the 9
    tracked districts aren't downstream of any dam this platform tracks)."""
    dam_ids = _DISTRICT_DAM_EXPOSURE.get(district, [])
    return [_STATUS_FETCHERS[dam_id]() for dam_id in dam_ids]
