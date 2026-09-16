"""
Automated flood risk assessment for NFCC.

Runs on a schedule (.github/workflows/automated_risk_assessment.yml) and,
for every district this platform tracks, pulls real near-term rainfall
from Open-Meteo (the same source src/hydrology/weather_forecast.py already
uses) and posts it to the deployed API's POST /alerts/assess. That
endpoint computes a real score/tier and - if it's at least MODERATE -
queues it in the pending_alerts review table
(src/api/routes/alert_review.py) for a human to review in the dashboard's
Alert Review Queue. Nothing gets sent to real people from this script;
AlertEngine.process() is only ever called when a human clicks Approve.

Usage:
    python scripts/automated_risk_assessment.py
    python scripts/automated_risk_assessment.py --api-url https://...
"""

from __future__ import annotations

import argparse
import logging
import sys

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
        timeout=15,
    )
    resp.raise_for_status()
    rain = resp.json().get("hourly", {}).get("rain", [])
    return round(sum(rain[:24]), 1) if rain else 0.0


def run(api_url: str) -> int:
    queued_count = 0
    failures = 0

    for district, (lat, lon) in DISTRICT_COORDS.items():
        try:
            precipitation = get_forecast_precipitation(lat, lon)
        except Exception as e:
            logger.error(f"Forecast fetch failed for {district}: {e}")
            failures += 1
            continue

        try:
            resp = requests.post(
                f"{api_url}/alerts/assess",
                json={"location": district, "precipitation": precipitation},
                timeout=20,
            )
            resp.raise_for_status()
            result = resp.json()
        except Exception as e:
            logger.error(f"Assessment POST failed for {district}: {e}")
            failures += 1
            continue

        if result.get("queued"):
            queued_count += 1
            logger.warning(
                f"QUEUED FOR REVIEW: {district} | {precipitation}mm -> "
                f"score={result['score']} tier={result['risk_tier']} "
                f"(id={result['id']})"
            )
        else:
            logger.info(
                f"{district} | {precipitation}mm -> "
                f"score={result.get('score')} - {result.get('reason')}"
            )

    logger.info(
        f"Done. {queued_count} district(s) queued for human review, "
        f"{failures} failure(s) out of {len(DISTRICT_COORDS)} checked."
    )
    return 1 if failures == len(DISTRICT_COORDS) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    args = parser.parse_args()
    return run(args.api_url)


if __name__ == "__main__":
    sys.exit(main())
