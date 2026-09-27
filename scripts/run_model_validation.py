"""
Periodic model-validation report for NFCC's real rule-based risk score.

Runs on a schedule (.github/workflows/model_validation.yml, monthly) and
calls the deployed API's two real, tested, but previously never-called
analysis endpoints:

1. GET /v1/backtest (src/models/historical_backtest.py) - replays
   calculate_score() against real historical CHIRPS rainfall for every
   documented real flood event (src/hydrology/flood_polygons.py, 8
   events). Cheap: one real Earth Engine query per event. Reports
   aggregate probability-of-detection and lead-time for both the
   same-day and rolling-3-day scoring variants.

2. GET /v1/verification (src/models/rare_event_verification.py) -
   real multi-decade CHIRPS rare-event skill (SEDI, Ferro & Stephenson
   2011) for the live alert threshold, per district with a documented
   event, with bootstrap confidence intervals. Expensive: real
   multi-decade Earth Engine queries per district - this is exactly why
   this script runs monthly, not daily like verify_predictions.py. The
   statistical question it answers ("does the live threshold still have
   real discriminative skill against the full historical record") moves
   slowly; there is no real value in checking it more often than the
   record itself meaningfully grows, and running it more often would
   waste real Earth Engine quota for no benefit.

Both endpoints already existed, real and fully tested, with zero real
callers anywhere before this script - a 2026-09-27 audit found them
built but never wired into anything that would actually run them
periodically. This is that wiring, not new analysis logic - every field
this script reads is copied from the real response shapes in
src/models/historical_backtest.py's run_full_backtest() and
src/models/rare_event_verification.py's run_full_verification()/
_threshold_report(), not guessed.

Read-only against the API (neither endpoint has side effects - no
AlertEngine call, no DB write); this script's own job is only to fetch,
log, and fail loudly (non-zero exit) on an HTTP failure, so a real
outage of either analysis path surfaces as a failed CI run instead of
silently going unnoticed. It does NOT fail the build on a low SEDI score
itself - that is a real finding for a human to interpret (see the
printed methodology caveats), not something with an agreed pass/fail
bar yet.

Usage:
    python scripts/run_model_validation.py
    python scripts/run_model_validation.py --api-url https://...
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

import requests

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s"
)
logger = logging.getLogger("model-validation")

DEFAULT_API_URL = "https://nfcc-platform-355353600602.europe-west1.run.app"

# Both endpoints are real analysis/reporting routes with no side effects
# and no API-key requirement (src/api/v1/backtest.py, verification.py) -
# unlike /v1/alerts/assess or /v1/predictions/record, nothing here writes
# to the platform's real state. Long timeout: verification runs real
# multi-decade Earth Engine queries per district.
_TIMEOUT_SECONDS = 300


def _log_backtest(backtest: dict) -> None:
    events = backtest.get("events", [])
    logger.info(f"Backtest: {len(events)} historical event(s) replayed")
    for event in events:
        if not event.get("available"):
            logger.info(f"  {event.get('district', '?')} ({event.get('date', '?')}): {event.get('reason')}")
            continue
        same_day = event.get("same_day", {})
        crossing = same_day.get("first_crossing") or {}
        logger.info(
            f"  {event['district']} ({event['date']}): "
            f"same-day {'detected' if same_day.get('detected') else 'MISSED'}"
            + (f", lead time {crossing.get('lead_time_days')}d" if crossing else "")
        )

    for variant in ("same_day", "rolling_3d"):
        agg = backtest.get("aggregate", {}).get(variant, {})
        lead = agg.get("lead_time_days", {})
        logger.info(
            f"  [{variant}] POD={agg.get('probability_of_detection')} "
            f"({agg.get('events_detected')}/{agg.get('events_evaluated')} events), "
            f"mean lead time={lead.get('mean')}d"
        )


def _log_verification(verification: dict) -> None:
    districts = verification.get("districts", {})
    logger.info(f"Verification: {len(districts)} district(s) scored")
    for name, d in districts.items():
        if not d.get("available"):
            logger.info(f"  {name}: {d.get('reason')}")
            continue
        same_day = (
            d.get("reports", {})
            .get("current_absolute_threshold", {})
            .get("same_day", {})
        )
        logger.info(
            f"  {name}: current-threshold SEDI={same_day.get('sedi')} "
            f"(90% CI={same_day.get('sedi_90pct_confidence_interval')}), "
            f"POD={same_day.get('probability_of_detection')}, "
            f"FAR={same_day.get('false_alarm_ratio')}, "
            f"{d.get('years_of_record')} years of record"
        )


def run(api_url: str) -> int:
    failures = 0

    try:
        resp = requests.get(f"{api_url}/v1/backtest", timeout=_TIMEOUT_SECONDS)
        resp.raise_for_status()
        _log_backtest(resp.json())
    except Exception as e:
        logger.error(f"GET /v1/backtest failed: {e}")
        failures += 1

    try:
        resp = requests.get(f"{api_url}/v1/verification", timeout=_TIMEOUT_SECONDS)
        resp.raise_for_status()
        _log_verification(resp.json())
    except Exception as e:
        logger.error(f"GET /v1/verification failed: {e}")
        failures += 1

    logger.info(f"Done. {failures} endpoint failure(s) out of 2 checked.")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default=os.getenv("NFCC_API_URL", DEFAULT_API_URL))
    args = parser.parse_args()
    return run(args.api_url)


if __name__ == "__main__":
    sys.exit(main())
