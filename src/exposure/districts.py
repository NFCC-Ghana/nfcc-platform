"""Canonical registry of the districts this platform tracks - the single
source of truth for "what is a tracked district," consolidating fields
that were previously scattered across (and required to independently
agree between) four separate files:

- src/hydrology/weather_forecast.py's district_coords (lat/lon)
- src/hydrology/sentinel_processor.py's _load_districts() (lat/lon/radius)
- src/exposure/impact_estimator.py's _load_district_data() (population/
  schools/hospitals/markets/area_km2/demographics) - previously also
  included a 10th entry, "Sekondi-Takoradi", not present in any of the
  other three lists and confirmed to have zero real callers anywhere;
  removed 2026-09-27 rather than left as a permanent citation gray area.
- src/exposure/community_names.py's DISTRICT_COMMUNITIES (named
  neighborhoods)
- hackathon/app/pages/dashboard.py's get_district_data() (region,
  its own separate copy of lat/lon/population/area_km2/communities)

This is the canonical source for new code going forward - starting with
GET /v1/districts (src/api/v1/districts.py). Existing call sites are
deliberately NOT migrated to import from here in this pass (that's a
separate, larger refactor); this module only adds a new, correct
registry alongside them, consistent with the additive /v1 rollout.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from src.exposure.community_names import get_affected_communities

# Real region/lat/lon/elevation (cross-checked against
# weather_forecast.py's district_coords and sentinel_processor.py's
# _load_districts(), which already agree on lat/lon for all 9).
#
# population/area_km2 (audited 2026-09-27 for manuscript accuracy): Tema,
# Kumasi, Tamale, Cape Coast, Ho, and Sunyani are now real, cited 2021
# Ghana Population and Housing Census figures for their single,
# unambiguous official administrative unit (Metropolitan/Municipal
# Assembly) - see the full citation and per-district source note in
# src/exposure/impact_estimator.py's _load_district_data() docstring,
# which this registry stays in sync with. "Accra Central"/"West"/"East"
# remain project-authored estimates, NOT official GSS units - see the
# same docstring for why a precise real split isn't available yet.
_BASE_DISTRICTS: Dict[str, dict] = {
    "Accra Central": {
        "region": "Greater Accra",
        "lat": 5.560,
        "lon": -0.210,
        "elevation_m": 12,
        "population": 187928,
        "area_km2": 45.5,
    },
    "Accra West": {
        "region": "Greater Accra",
        "lat": 5.550,
        "lon": -0.230,
        "elevation_m": 10,
        "population": 203461,
        "area_km2": 52.3,
    },
    "Accra East": {
        "region": "Greater Accra",
        "lat": 5.565,
        "lon": -0.190,
        "elevation_m": 15,
        "population": 142587,
        "area_km2": 38.2,
    },
    "Tema": {
        "region": "Greater Accra",
        "lat": 5.650,
        "lon": -0.020,
        "elevation_m": 18,
        "population": 177924,
        "area_km2": 565,
    },
    "Kumasi": {
        "region": "Ashanti",
        "lat": 6.670,
        "lon": -1.620,
        "elevation_m": 25,
        "population": 443981,
        "area_km2": 299,
    },
    "Tamale": {
        "region": "Northern",
        "lat": 9.400,
        "lon": -0.840,
        "elevation_m": 125,
        "population": 374744,
        "area_km2": 731,
    },
    "Cape Coast": {
        "region": "Central",
        "lat": 5.100,
        "lon": -1.250,
        "elevation_m": 25,
        "population": 189925,
        "area_km2": 122,
    },
    "Ho": {
        "region": "Volta",
        "lat": 6.601,
        "lon": 0.471,
        "elevation_m": 100,
        "population": 180420,
        "area_km2": 573.2,
    },
    "Sunyani": {
        "region": "Bono",
        "lat": 7.333,
        "lon": -2.333,
        "elevation_m": 300,
        "population": 193595,
        "area_km2": 1289,
    },
}

TRACKED_DISTRICT_NAMES: List[str] = list(_BASE_DISTRICTS.keys())


@dataclass(frozen=True)
class District:
    name: str
    region: str
    lat: float
    lon: float
    elevation_m: float
    population: int
    area_km2: float
    communities: List[str]


def get_district(name: str) -> Optional[District]:
    """A single tracked district's canonical data, or None if `name`
    isn't one of the real 9 this platform tracks."""
    base = _BASE_DISTRICTS.get(name)
    if base is None:
        return None
    return District(name=name, communities=get_affected_communities(name), **base)


def list_districts() -> List[District]:
    """Every tracked district, in the same canonical order everywhere
    else uses (Accra Central/West/East, Tema, Kumasi, Tamale, Cape
    Coast, Ho, Sunyani)."""
    return [get_district(name) for name in TRACKED_DISTRICT_NAMES]
