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

Second real, confirmed constraint (found the same way - a live call
through the actual outcome_verifier.py code path, after the appname was
approved, not from the docs): ReliefWeb's date.created range filter
rejects a bare 'YYYY-MM-DD' value with 'UnexpectedValueException:
Invalid range from value ... It must be an ISO 8601 date' - it actually
wants a full ISO 8601 DATETIME (e.g. '2026-09-21T00:00:00+00:00').
outcome_verifier.py naturally deals in dates, not datetimes, so this
module normalizes both bounds before sending rather than pushing a
ReliefWeb-specific quirk onto every caller.
"""

import logging
import os
from typing import Dict, List

import requests

from src.verification.place_names import search_place

logger = logging.getLogger("nfcc.verification.reliefweb")


def _to_iso_datetime(value: str, end_of_day: bool = False) -> str:
    """Accepts either a bare date ('2026-09-21') or an already-full
    datetime, and returns a full ISO 8601 datetime - what ReliefWeb's
    date.created range filter actually requires (see module docstring).
    end_of_day pushes a bare date to 23:59:59 instead of midnight, so an
    inclusive 'to' bound doesn't silently exclude same-day reports."""
    if "T" in value:
        return value
    time_part = "T23:59:59+00:00" if end_of_day else "T00:00:00+00:00"
    return f"{value}{time_part}"


_BASE_URL = "https://api.reliefweb.int/v2/reports"


def search_flood_reports(district: str, start_date: str, end_date: str) -> Dict:
    """Real ReliefWeb reports tagged Ghana that mention a flood and this
    district's place name, filtered to a real date window - used to check
    whether a documented humanitarian report corroborates a past
    prediction for this district. ReliefWeb's editorial tagging is at
    country level, not Ghana-district level, so the place name has to be
    matched in the text.

    ReliefWeb's query operator defaults to OR: the previous free-text
    query "Ghana flood <district>" matched any report containing any one
    of those words (Somali river-flood advisories, Ghanaian health news)
    and marked almost every prediction "flood_confirmed". The query now
    requires every term (operator AND), quotes the place name, and
    filters on the Ghana country tag. `flood*` because the search does
    not stem ("flood" misses "Floods").

    Tested against known events: the search effectively matches titles,
    and Ghana flood reports are titled at country or region level
    ("Ghana - Floods Situation Report, 8 June 2015"), so this rarely
    confirms a district - high precision, very low recall."""
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
                "query[value]": f'flood* AND "{search_place(district)}"',
                "query[operator]": "AND",
                "filter[operator]": "AND",
                "filter[conditions][0][field]": "country.iso3",
                "filter[conditions][0][value]": "gha",
                "filter[conditions][1][field]": "date.created",
                "filter[conditions][1][value][from]": _to_iso_datetime(start_date),
                "filter[conditions][1][value][to]": _to_iso_datetime(
                    end_date, end_of_day=True
                ),
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
