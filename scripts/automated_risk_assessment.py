"""
Automated flood risk assessment for NFCC.

Runs on a schedule (.github/workflows/automated_risk_assessment.yml) and,
for every district this platform tracks, assesses THREE independent
real signals and posts each to the deployed API's POST /alerts/assess -
two rainfall-driven (pluvial), one dam/river-driven (fluvial):

1. forecast_next_24h - Open-Meteo's next-24h forecast (anticipatory:
   what's coming).
2. a real 3-day antecedent rainfall accumulation (retrospective: what's
   already fallen and already accumulating in soil/rivers) - preferring
   real CHIRPS via GET /v1/districts/{district}/antecedent-rainfall
   (basis=antecedent_3d_accumulation; Earth Engine auth only works
   inside the API's own Cloud Run identity, not this GitHub Actions
   runner, so this fetches the already-computed value over HTTP), with
   a fallback to Open-Meteo's own past_days rainfall
   (basis=antecedent_3d_observed_fallback) when CHIRPS's real-world
   publication lag makes its value too stale (confirmed in production:
   CHIRPS's near-real-time product can lag 18+ days) - a real, lower-
   latency substitute rather than skipping the signal entirely, though
   it wasn't the exact product backtested (see get_observed_past_precipitation).

3. dam_river_pathway - real river gauge + dam/upstream-proxy levels
   (src/hydrology/fluvial_pathway.py), fetched via GET
   /v1/districts/{district}/fluvial-risk and submitted with
   score_override (it's already a 0-100 risk score, not a rainfall
   depth). Runs and can queue an alert REGARDLESS of what the rainfall
   signals above found - real flood science treats rainfall-driven
   (pluvial) and dam/river-driven (fluvial) flooding as independent
   causal pathways (src/models/multi_source_confidence.py's module
   docstring has the citations): a dam release can flood a district
   with zero local rain. Before this signal existed, a pure dam-driven
   flood - like Ghana's own real 2023 Akosombo spillage or 2021/2010
   Bagre-driven Tamale floods - could never have crossed this
   pipeline's review threshold at all.

Neither pluvial signal replaces the other, and neither replaces the
fluvial one - the antecedent signal isn't decorative: real backtesting
against 36.7 years of CHIRPS data (src/models/rare_event_verification.py)
found a real 3-day rolling accumulation has meaningfully better rare-
event skill (SEDI) than same-day/forecast-only scoring in every
backtested district, roughly doubling probability of detection at the
same false-alarm rate. Before this, the automated pipeline only ever
looked forward, and only ever looked at rainfall.

/alerts/assess computes a real score/tier per signal and - if at least
MODERATE - queues it in the pending_alerts review table
(src/api/routes/alert_review.py), tagged with which signal triggered
it, for a human to review in the dashboard's Alert Review Queue.
Nothing gets sent to real people from this script; AlertEngine.process()
is only ever called when a human clicks Approve.

Also records, on every scheduled run:

- A risk_history snapshot (POST /v1/districts/{district}/risk/history,
  src/api/v1/risk_history.py) - a real, periodic score/tier time series.
- A real observation_history row for every source actually fetched
  this run (POST /v1/districts/{district}/observations,
  src/database/observation_history_db.py) - the "Historical data"
  foundation for training/backtesting/evaluation/model comparison/
  event replay, which previously had no growing archive at all beyond
  flood_polygons.py's fixed 8-event list.
- One prediction_ledger entry per district (POST /v1/predictions/record,
  src/database/prediction_ledger_db.py) - a full real /decision/card
  snapshot (evidence, fused risk, confidence, reasoning), preserving
  what happened/predicted/why so a real outcome can be attached later
  and this platform can finally answer its own calibration question -
  not just "what did CivicFlood predict for a past documented flood"
  (src/models/rare_event_verification.py) but "was CivicFlood right",
  for every real assessment, not only the 8 historical ones.

Usage:
    python scripts/automated_risk_assessment.py
    python scripts/automated_risk_assessment.py --api-url https://...
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Optional

import requests

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s"
)
logger = logging.getLogger("automated-risk-assessment")

DEFAULT_API_URL = "https://nfcc-platform-355353600602.europe-west1.run.app"

# The write endpoints this script POSTs to (assess/observations/
# decision-card/predictions/risk-history) require X-API-Key now - see
# src/api/auth.py. Sourced from the NFCC_API_KEY GitHub Actions secret
# (.github/workflows/automated_risk_assessment.yml), the same value as
# the nfcc-api-key Cloud Run secret this script has always talked to.
_API_KEY = os.getenv("NFCC_API_KEY", "")


def _auth_headers() -> dict:
    return {"X-API-Key": _API_KEY} if _API_KEY else {}


# Matches hackathon/app/pages/dashboard.py's get_district_data and
# src/hydrology/weather_forecast.py's district_coords - the 9 districts
# this platform has real hydrology/impact data for.
DISTRICT_COORDS = {
    "Accra Central": (5.560, -0.210),
    "Accra West": (5.550, -0.230),
    "Accra East": (5.565, -0.190),
    "Tema": (5.650, -0.020),
    "Kumasi": (6.670, -1.620),
    "Tamale": (9.400, -0.840),
    "Cape Coast": (5.100, -1.250),
    "Ho": (6.601, 0.471),
    "Sunyani": (7.333, -2.333),
}


def get_forecast_precipitation(lat: float, lon: float) -> float:
    """Real next-24h forecasted rainfall for a coordinate, via Open-Meteo -
    an anticipatory signal (what's coming), not just a retrospective one,
    which is the more useful thing to assess flood risk against."""
    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "hourly": "rain",
            "forecast_days": 1,
        },
        timeout=25,
    )
    resp.raise_for_status()
    rain = resp.json().get("hourly", {}).get("rain", [])
    return round(sum(rain[:24]), 1) if rain else 0.0


def get_antecedent_precipitation(api_url: str, district: str) -> Optional[float]:
    """Real 3-day rolling sum of observed CHIRPS rainfall for a district,
    via the API's own /v1/districts/{district}/antecedent-rainfall
    (src/hydrology/antecedent_rainfall.py) - Earth Engine auth only works
    inside the API's own Cloud Run identity, so this fetches the already-
    computed real value over HTTP rather than calling Earth Engine from
    this GitHub Actions runner. Returns None (not 0.0) when unavailable,
    so callers can tell "genuinely no rain" apart from "couldn't check" -
    posting a fabricated 0.0 would silently suppress a real assessment
    that should have run."""
    try:
        resp = requests.get(
            f"{api_url}/v1/districts/{district}/antecedent-rainfall", timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"Antecedent rainfall fetch failed for {district}: {e}")
        return None

    if not data.get("available"):
        logger.info(
            f"Antecedent rainfall unavailable for {district}: {data.get('reason')}"
        )
        return None
    if data.get("stale"):
        logger.info(
            f"Antecedent rainfall for {district} is stale "
            f"({data.get('data_age_days')} days old, freshest={data.get('freshest_date')})"
            " - falling back to Open-Meteo's observed past rainfall instead"
        )
        return None
    return data["rolling_3d_mm"]


def get_observed_past_precipitation(
    lat: float, lon: float, days: int = 3
) -> Optional[float]:
    """Real observed rainfall for the past `days` days, via Open-Meteo's
    `past_days` parameter on the same forecast endpoint already used for
    get_forecast_precipitation - Open-Meteo blends real recent
    observations into this window with far lower latency than CHIRPS's
    near-real-time product currently has (confirmed in production: an
    18-day lag). Needs no Earth Engine credentials, so it runs directly
    in this script as the fallback when the CHIRPS-based antecedent
    value is stale or unavailable.

    This is a real, low-latency substitute, not a like-for-like
    replacement: the SEDI backtest (src/models/rare_event_verification.py)
    validated a 3-day rolling sum of real CHIRPS rainfall specifically,
    not Open-Meteo's ERA5-blended recent-observation estimate - it's
    tagged with a different `basis` (antecedent_3d_observed_fallback)
    precisely so this distinction isn't lost."""
    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "hourly": "rain",
            "past_days": days,
            "forecast_days": 1,
        },
        timeout=25,
    )
    resp.raise_for_status()
    rain = resp.json().get("hourly", {}).get("rain", [])
    observed_hours = days * 24
    if len(rain) < observed_hours:
        return None
    return round(sum(rain[:observed_hours]), 1)


def get_fluvial_risk(api_url: str, district: str) -> Optional[float]:
    """Real river/dam-driven risk (0-100) for a district, independent
    of any rainfall input, via the API's own GET /v1/districts/
    {district}/fluvial-risk (src/hydrology/fluvial_pathway.py) - Earth
    Engine and DAHITI calls both only work inside the API's own Cloud
    Run identity, so this fetches the already-computed value over HTTP
    rather than calling either from this GitHub Actions runner. Returns
    None (not 0.0) when no real river/dam pathway could be assessed for
    this district (e.g. no dam exposure and no river coverage) - a
    fabricated 0.0 would silently claim "checked, no risk" for a
    district this platform genuinely has no fluvial signal for."""
    try:
        resp = requests.get(
            f"{api_url}/v1/districts/{district}/fluvial-risk", timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"Fluvial risk fetch failed for {district}: {e}")
        return None
    return data.get("risk_0_100")


def _assess(
    api_url: str,
    district: str,
    precipitation: float,
    basis: str,
    score_override: Optional[float] = None,
) -> Optional[dict]:
    payload = {"location": district, "precipitation": precipitation, "basis": basis}
    if score_override is not None:
        payload["score_override"] = score_override
    try:
        resp = requests.post(
            f"{api_url}/alerts/assess",
            json=payload,
            timeout=20,
            headers=_auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Assessment POST failed for {district} ({basis}): {e}")
        return None


def _record_observation(
    api_url: str, district: str, source: str, value: Optional[float], unit: str
) -> None:
    """Best-effort: a real observation-history write failing must never
    fail this district's overall assessment - the real-time assessment
    already succeeded independently of whether its historical record
    gets saved (same principle as the existing risk_history write)."""
    quality_flag = "missing" if value is None else "not_evaluated"
    try:
        requests.post(
            f"{api_url}/v1/districts/{district}/observations",
            json={"source": source, "value": value, "unit": unit, "quality_flag": quality_flag},
            timeout=20,
            headers=_auth_headers(),
        ).raise_for_status()
    except Exception as e:
        logger.warning(f"observation-history POST failed for {district}/{source}: {e}")


def _record_prediction(api_url: str, district: str, precipitation: float) -> None:
    """Logs one full real /decision/card snapshot (evidence, fused risk,
    confidence, reasoning) into the prediction ledger
    (src/database/prediction_ledger_db.py) - best-effort, same reason as
    _record_observation above."""
    try:
        card_resp = requests.post(
            f"{api_url}/decision/card",
            json={"location": district, "precipitation": precipitation},
            timeout=30,
            headers=_auth_headers(),
        )
        card_resp.raise_for_status()
        card = card_resp.json()
        requests.post(
            f"{api_url}/v1/predictions/record",
            json={
                "district": district,
                "evidence_snapshot": card,
                "risk_score": card.get("score"),
                "risk_tier": card.get("risk_tier"),
                "fused_risk_score": card.get("fused_risk_score"),
                "fused_risk_tier": card.get("fused_risk_tier"),
                "confidence": card.get("confidence", {}).get("value"),
                "reason": card.get("reason"),
                "risk_attribution": card.get("risk_attribution"),
            },
            timeout=20,
            headers=_auth_headers(),
        ).raise_for_status()
    except Exception as e:
        logger.warning(f"prediction-ledger record failed for {district}: {e}")


def run(api_url: str) -> int:
    queued_count = 0
    failures = 0

    for district, (lat, lon) in DISTRICT_COORDS.items():
        try:
            forecast_precip = get_forecast_precipitation(lat, lon)
        except Exception as e:
            logger.error(f"Forecast fetch failed for {district}: {e}")
            forecast_precip = None
            failures += 1

        antecedent_precip = get_antecedent_precipitation(api_url, district)
        antecedent_basis = "antecedent_3d_accumulation"
        if antecedent_precip is None:
            try:
                antecedent_precip = get_observed_past_precipitation(lat, lon)
                antecedent_basis = "antecedent_3d_observed_fallback"
            except Exception as e:
                logger.warning(f"Observed-past-rainfall fallback failed for {district}: {e}")

        # Independent of both rainfall signals above - a district with
        # no dam exposure and no river coverage honestly has no fluvial
        # pathway (fluvial_risk is None), which is expected, not a
        # failure; see get_fluvial_risk's docstring.
        fluvial_risk = get_fluvial_risk(api_url, district)

        if forecast_precip is None and antecedent_precip is None and fluvial_risk is None:
            continue

        district_queued = False

        if forecast_precip is not None:
            result = _assess(api_url, district, forecast_precip, "forecast_next_24h")
            if result is None:
                failures += 1
            elif result.get("queued"):
                district_queued = True
                logger.warning(
                    f"QUEUED FOR REVIEW: {district} | forecast {forecast_precip}mm -> "
                    f"score={result['score']} tier={result['risk_tier']} "
                    f"(id={result['id']})"
                )
            else:
                logger.info(
                    f"{district} | forecast {forecast_precip}mm -> "
                    f"score={result.get('score')} - {result.get('reason')}"
                )

        if antecedent_precip is not None:
            result = _assess(api_url, district, antecedent_precip, antecedent_basis)
            if result is None:
                failures += 1
            elif result.get("queued"):
                district_queued = True
                logger.warning(
                    f"QUEUED FOR REVIEW: {district} | antecedent 3d {antecedent_precip}mm "
                    f"({antecedent_basis}) -> score={result['score']} "
                    f"tier={result['risk_tier']} (id={result['id']})"
                )
            else:
                logger.info(
                    f"{district} | antecedent 3d {antecedent_precip}mm "
                    f"({antecedent_basis}) -> score={result.get('score')} - "
                    f"{result.get('reason')}"
                )

        if fluvial_risk is not None:
            result = _assess(
                api_url,
                district,
                fluvial_risk,
                "dam_river_pathway",
                score_override=fluvial_risk,
            )
            if result is None:
                failures += 1
            elif result.get("queued"):
                district_queued = True
                logger.warning(
                    f"QUEUED FOR REVIEW: {district} | dam/river risk {fluvial_risk} "
                    f"(dam_river_pathway) -> score={result['score']} "
                    f"tier={result['risk_tier']} (id={result['id']})"
                )
            else:
                logger.info(
                    f"{district} | dam/river risk {fluvial_risk} "
                    f"(dam_river_pathway) -> score={result.get('score')} - "
                    f"{result.get('reason')}"
                )

        if district_queued:
            queued_count += 1

        # Record a risk_history snapshot on every scheduled run (priority
        # deliverable #9's orchestration - this script runs outside the
        # API container with no direct database access, so recording has
        # to go through the API the same way /alerts/assess does).
        # Uses the forecast value, unchanged from before this signal was
        # added, since risk_history is a single time series keyed on one
        # number per district. Best-effort: a failure here doesn't count
        # against this district's overall success - the real-time
        # assessment above already succeeded independently of whether
        # its historical record gets saved.
        if forecast_precip is not None:
            try:
                requests.post(
                    f"{api_url}/v1/districts/{district}/risk/history",
                    json={"precipitation_mm": forecast_precip, "source": "scheduled"},
                    timeout=20,
                    headers=_auth_headers(),
                ).raise_for_status()
            except Exception as e:
                logger.warning(f"risk_history POST failed for {district}: {e}")

        # Real observation-history archive (src/database/
        # observation_history_db.py) - every source actually checked
        # this run, real value or an honest miss, feeding the growing
        # dataset training/backtesting/model-comparison/event-replay
        # need. Best-effort, same reasoning as risk_history above.
        _record_observation(api_url, district, "forecast_next_24h", forecast_precip, "mm")
        _record_observation(api_url, district, antecedent_basis, antecedent_precip, "mm")
        _record_observation(api_url, district, "dam_river_pathway", fluvial_risk, "risk_0_100")

        # One full real /decision/card snapshot per district per run,
        # into the prediction ledger (src/database/prediction_ledger_db.py)
        # - preserves what happened/predicted/why so a real outcome can
        # be attached later. Uses the forecast value (0.0 if unavailable)
        # since /decision/card needs a precipitation input; the fluvial
        # pathway is still captured inside the card's own evidence/
        # fused_risk_score regardless of this choice.
        _record_prediction(api_url, district, forecast_precip or 0.0)

    logger.info(
        f"Done. {queued_count} district(s) queued for human review, "
        f"{failures} failure(s) out of {len(DISTRICT_COORDS)} checked."
    )
    return 1 if failures >= len(DISTRICT_COORDS) * 3 else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    args = parser.parse_args()
    return run(args.api_url)


if __name__ == "__main__":
    sys.exit(main())
