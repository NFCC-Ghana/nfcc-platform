"""Real ReliefWeb API client - UN OCHA's curated humanitarian report
archive (reliefweb.int), the most PRECISE of this platform's automated
outcome-confirmation sources: unlike general news search, every report
here is already editorially tagged by country and disaster type, and
ReliefWeb already has real, confirmed coverage of Ghana's actual flood
history (directly verified this session: "Ghana: Floods - Oct 2023"
for the real Akosombo spillage, "Ghana: Floods - Jun 2015" for the
real Accra flood - the same two events already in
src/hydrology/flood_polygons.py).

Real, confirmed constraint (found only by making a live call, not from
the docs, which suggested any string would work): ReliefWeb's API
requires a PRE-APPROVED appname, not an arbitrary string - a live test
call during this module's development returned:
'AccessDeniedHttpException: You are not using an approved appname.'
Request one at https://apidoc.reliefweb.int/parameters#appname (a
real, one-time registration step, reportedly fast/free per their own
docs) and set RELIEFWEB_APPNAME. Honestly reports available=False
with that exact instruction until it's set, rather than silently
never checking this source - the same disclosed-configuration-gap
pattern already used for DAHITI_API_KEY elsewhere in this platform.
"""

import logging
import os
from typing import Dict, List

import requests

logger = logging.getLogger("nfcc.verification.reliefweb")

_BASE_URL = "https://api.reliefweb.int/v2/reports"


def search_flood_reports(district: str, start_date: str, end_date: str) -> Dict:
    """Real ReliefWeb reports mentioning Ghana + flood, filtered to a
    real date window - used to check whether a documented humanitarian
    report corroborates a past prediction for this district. district
    is included in the free-text query (ReliefWeb's editorial tagging
    is at country/region level, not Ghana-district level, so an exact
    district-field filter isn't available - the query text is the best
    real precision achievable)."""
    appname = os.getenv("RELIEFWEB_APPNAME")
    if not appname:
        return {
            "available": False,
            "reason": (
                "RELIEFWEB_APPNAME not configured - request a real "
                "approved appname at "
                "https://apidoc.reliefweb.int/parameters#appname"
            ),
        }

    try:
        resp = requests.get(
            _BASE_URL,
            params={
                "appname": appname,
                "query[value]": f"Ghana flood {district}",
                "filter[field]": "date.created",
                "filter[value][from]": start_date,
                "filter[value][to]": end_date,
                "limit": 10,
            },
            timeout=20,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        logger.warning(f"ReliefWeb request failed: {e}")
        return {"available": False, "reason": f"ReliefWeb request failed: {e}"}

    reports: List[Dict] = []
    for item in payload.get("data") or []:
        fields = item.get("fields") or {}
        reports.append(
            {
                "title": fields.get("title"),
                "url": item.get("href") or fields.get("url"),
                "date": (fields.get("date") or {}).get("created"),
            }
        )

    return {
        "available": True,
        "matched_reports": reports,
        "count": len(reports),
        "source": "ReliefWeb (UN OCHA humanitarian report archive)",
    }
