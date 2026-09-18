"""
Automated flood risk assessment for NFCC.

Runs on a schedule (.github/workflows/automated_risk_assessment.yml) and,
for every district this platform tracks, assesses TWO independent real
rainfall signals and posts each to the deployed API's POST /alerts/assess:

1. forecast_next_24h - Open-Meteo's next-24h forecast (anticipatory:
   what's coming).
2. antecedent_3d_accumulation - a real 3-day rolling SUM of observed
   CHIRPS rainfall (retrospective: what's already fallen and already
   accumulating in soil/rivers), fetched via GET
   /v1/districts/{district}/antecedent-rainfall since Earth Engine auth
   only works inside the API's own Cloud Run identity, not this GitHub
   Actions runner.

Both signals matter and neither replaces the other - but they're not
interchangeable, and this second signal isn't decorative: real
backtesting against 36.7 years of CHIRPS data
(src/models/rare_event_verification.py) found it has meaningfully
better rare-event skill (SEDI) than same-day/forecast-only scoring in
every backtested district, roughly doubling probability of detection
at the same false-alarm rate. Before this, the automated pipeline only
ever looked forward.

/alerts/assess computes a real score/tier per signal and - if at least
MODERATE - queues it in the pending_alerts review table
(src/api/routes/alert_review.py), tagged with which signal triggered
it, for a human to review in the dashboard's Alert Review Queue.
Nothing gets sent to real people from this script; AlertEngine.process()
is only ever called when a human clicks Approve.

Also records a risk_history snapshot for every district on every run
(POST /v1/districts/{district}/risk/history, src/api/v1/risk_history.py)
- the orchestration that keeps GET /v1/districts/{district}/risk/history
populated with a real, periodic time series, since this script (running
outside the API container) has no direct database access. Uses the
forecast value for this, unchanged from before.

Usage:
    python scripts/automated_risk_assessment.py
    python scripts/automated_risk_assessment.py --api-url https://...
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional

import requests

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s"
)
logger = logging.getLogger("automated-risk-assessment")

DEFAULT_API_URL = "https://nfcc-platform-355353600602.europe-west1.run.app"

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
    return data["rolling_3d_mm"]


def _assess(
    api_url: str, district: str, precipitation: float, basis: str
) -> Optional[dict]:
    try:
        resp = requests.post(
            f"{api_url}/alerts/assess",
            json={"location": district, "precipitation": precipitation, "basis": basis},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Assessment POST failed for {district} ({basis}): {e}")
        return None


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

        if forecast_precip is None and antecedent_precip is None:
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
            result = _assess(
                api_url, district, antecedent_precip, "antecedent_3d_accumulation"
            )
            if result is None:
                failures += 1
            elif result.get("queued"):
                district_queued = True
                logger.warning(
                    f"QUEUED FOR REVIEW: {district} | antecedent 3d {antecedent_precip}mm -> "
                    f"score={result['score']} tier={result['risk_tier']} "
                    f"(id={result['id']})"
                )
            else:
                logger.info(
                    f"{district} | antecedent 3d {antecedent_precip}mm -> "
                    f"score={result.get('score')} - {result.get('reason')}"
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
                ).raise_for_status()
            except Exception as e:
                logger.warning(f"risk_history POST failed for {district}: {e}")

    logger.info(
        f"Done. {queued_count} district(s) queued for human review, "
        f"{failures} failure(s) out of {len(DISTRICT_COORDS)} checked."
    )
    return 1 if failures >= len(DISTRICT_COORDS) * 2 else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    args = parser.parse_args()
    return run(args.api_url)


if __name__ == "__main__":
    sys.exit(main())
