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
from typing import Dict, List

import requests

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
        return {
            "dam": "Akosombo",
            "available": True,
            "water_surface_elevation_m": latest.get("wse"),
            "uncertainty_m": latest.get("wse_u"),
            "observation_date": latest.get("date"),
            "source": "DAHITI satellite altimetry (Lake Volta)",
            "downstream_communities": ["Kpong", "Akuse", "Ada", "Tema"],
            "note": (
                "Satellite altimetry, not real-time - revisit interval "
                "depends on the satellite mission (10-35 days) with a "
                "1-2 day processing delay after each pass"
            ),
        }
    except Exception as e:
        logger.warning(f"DAHITI request failed: {e}")
        return {
            "dam": "Akosombo",
            "available": False,
            "reason": f"DAHITI request failed: {e}",
        }


def get_bagre_status() -> Dict:
    """Bagre Dam (Burkina Faso) has no automatable real-time data source -
    always honestly reports unavailable, since Tamale is directly exposed
    to uncoordinated releases from it."""
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
