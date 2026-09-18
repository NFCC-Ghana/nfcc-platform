"""Automated outcome verification for the prediction ledger
(src/database/prediction_ledger_db.py) - the piece that was still
manual: confirming whether a past prediction's real flood risk
actually materialized, without a human looking it up by hand.

Researched globally before building this (not assumed): real disaster-
monitoring systems never rely on one confirmation source. GDACS (the
UN/EU Global Disaster Alert and Coordination System) combines media
monitoring with satellite-based automatic flood detection precisely
because neither alone is reliable; published research on automated
geohazard extraction from news explicitly still recommends a
verification step because NLP-based news mining alone has real,
measured error rates (one study: 82.4% precision - not good enough to
trust blindly). This module applies the same principle already used
for real-time risk fusion (src/models/multi_source_confidence.py):
independent sources are combined via "any real confirmation is
sufficient" (a noisy-OR-style OR, not requiring all sources to agree),
because absence of evidence in one source (a news outlet that never
covered a real local flood) doesn't cancel real evidence in another
(a verified citizen report).

Four independent, real, automatable sources:
1. ReliefWeb (src/verification/reliefweb_client.py) - UN OCHA's curated
   humanitarian report archive. Most precise; requires a real approved
   appname (not yet configured - see that module's docstring).
2. GDELT (src/verification/gdelt_client.py) - broad global news
   monitoring, free and keyless, real-time-ish, noisier.
3. Verified citizen reports (src/community/community_memory.py) - real,
   independently verified ground reports, the same PetaBencana-style
   trust model already used for live confidence fusion.
4. Sentinel-1 SAR (src/hydrology/sentinel_processor.py), re-run against
   the REAL historical date window after the prediction (it already
   accepts a `date` parameter) - direct physical satellite evidence of
   standing water, not a report about one.

If NONE of the four confirms within the check window, this reports
"no_evidence_found" - deliberately NOT "no_flood_confirmed": absence of
detected evidence across four real sources is meaningful, but it is
not logically equivalent to certainty a flood didn't happen (a real
flood in an area no source covered is possible, if less likely with
four independent checks) - the same epistemic honesty this platform
applies to every other absent signal.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple

from src.community.community_memory import community_memory
from src.hydrology.sentinel_processor import sentinel_processor
from src.verification.gdelt_client import search_flood_news
from src.verification.reliefweb_client import search_flood_reports

logger = logging.getLogger("nfcc.verification.outcome_verifier")

_DEFAULT_WINDOW_DAYS = 14
_VERIFIED_REPORTS_THRESHOLD = 3


def verify_outcome(district: str, predicted_at: str, window_days: int = _DEFAULT_WINDOW_DAYS) -> Dict:
    """Checks all four real, independent sources for confirmation that
    a real flood happened in `district` within `window_days` after
    `predicted_at`. Returns a dict with `outcome`
    ("flood_confirmed"/"no_evidence_found"), `outcome_source` (which
    real source(s) confirmed, comma-joined), and the raw per-source
    results for full transparency - never a black-box verdict."""
    predicted_date = date.fromisoformat(predicted_at[:10])
    start_date = predicted_date.isoformat()
    end_date = (predicted_date + timedelta(days=window_days)).isoformat()

    confirmations: List[Tuple[str, Dict]] = []
    checks: Dict[str, Dict] = {}

    reliefweb = search_flood_reports(district, start_date, end_date)
    checks["reliefweb"] = reliefweb
    if reliefweb.get("available") and reliefweb.get("count", 0) > 0:
        confirmations.append(("ReliefWeb", reliefweb))

    gdelt = search_flood_news(district, start_date, end_date)
    checks["gdelt"] = gdelt
    if gdelt.get("available") and gdelt.get("count", 0) > 0:
        confirmations.append(("GDELT", gdelt))

    try:
        start_iso = f"{start_date}T00:00:00"
        end_iso = f"{end_date}T23:59:59"
        verified_count = community_memory.get_validated_report_count_in_window(
            district, start_iso, end_iso
        )
        checks["citizen_reports"] = {"available": True, "verified_count": verified_count}
        if verified_count >= _VERIFIED_REPORTS_THRESHOLD:
            confirmations.append(("verified_citizen_reports", checks["citizen_reports"]))
    except Exception as e:
        logger.warning(f"Citizen report check failed for {district}: {e}")
        checks["citizen_reports"] = {"available": False, "reason": str(e)}

    try:
        # Real bug caught by live production testing: end_date (predicted
        # date + window_days) can land in the future relative to today
        # for a recently-made prediction, and asking a real satellite
        # for imagery of a date that hasn't happened yet trivially finds
        # nothing - which looks identical to "Earth Engine unavailable"
        # (both fall back to simulated) but means something completely
        # different. Capping at today ensures this checks real, already-
        # captured imagery, never a future date.
        satellite_check_date = min(end_date, date.today().isoformat())
        satellite = sentinel_processor.detect_flood(district, date=satellite_check_date)
        checks["satellite"] = satellite
        if satellite.get("source") == "Sentinel-1 SAR" and satellite.get("water_detected"):
            confirmations.append(("Sentinel-1 SAR", satellite))
    except Exception as e:
        logger.warning(f"Satellite check failed for {district}: {e}")
        checks["satellite"] = {"available": False, "reason": str(e)}

    if confirmations:
        outcome = "flood_confirmed"
        outcome_source = ",".join(name for name, _ in confirmations)
    else:
        outcome = "no_evidence_found"
        outcome_source = "automated_check_no_signal"

    return {
        "district": district,
        "window_start": start_date,
        "window_end": end_date,
        "outcome": outcome,
        "outcome_source": outcome_source,
        "confirmations": [name for name, _ in confirmations],
        "checks": checks,
        "checked_at": datetime.utcnow().isoformat(),
    }
