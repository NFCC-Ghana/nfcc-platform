"""
Automated outcome verification for NFCC's prediction ledger.

Runs on a schedule (.github/workflows/verify_predictions.yml, daily)
and, for every prediction in the ledger (src/database/
prediction_ledger_db.py) still awaiting a real outcome and old enough
to realistically have one by now, calls the API's real server-side
auto-verify (POST /v1/predictions/{id}/auto-verify -
src/api/v1/predictions.py), which checks four independent real sources
(ReliefWeb, GDELT, verified citizen reports, Sentinel-1 SAR -
src/verification/outcome_verifier.py) and records whatever it finds.

This is the automated replacement for what was previously a fully
manual curation step: before this script existed, every prediction's
outcome stayed NULL forever unless a human looked it up and called
POST /v1/predictions/{id}/outcome by hand. It still runs server-side
(this script only ever calls the API over HTTP, the same reason every
other scheduled script in this platform does) since real Earth Engine
and database access both only work inside the API's own Cloud Run
identity/filesystem.

_MIN_AGE_DAYS gives real news/citizen reports realistic time to
surface before checking - verifying an hour-old prediction would
almost always find nothing, not because nothing happened, but because
nothing's been reported yet. _MAX_AGE_DAYS bounds the daily workload
and reflects that checking a months-old prediction adds little real
value at this stage (the platform's own historical record is still
young - src/database/observation_history_db.py's module docstring).

Usage:
    python scripts/verify_predictions.py
    python scripts/verify_predictions.py --api-url https://...
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone

import requests

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s"
)
logger = logging.getLogger("verify-predictions")

DEFAULT_API_URL = "https://nfcc-platform-355353600602.europe-west1.run.app"

_MIN_AGE_DAYS = 3
_MAX_AGE_DAYS = 30


def _age_days(predicted_at: str, now: datetime) -> float:
    predicted_dt = datetime.fromisoformat(predicted_at)
    if predicted_dt.tzinfo is None:
        predicted_dt = predicted_dt.replace(tzinfo=timezone.utc)
    return (now - predicted_dt).total_seconds() / 86400.0


def run(api_url: str) -> int:
    try:
        resp = requests.get(
            f"{api_url}/v1/predictions",
            params={"outcome": "__pending__", "limit": 500},
            timeout=30,
        )
        resp.raise_for_status()
        pending = resp.json().get("predictions", [])
    except Exception as e:
        logger.error(f"Failed to fetch pending predictions: {e}")
        return 1

    now = datetime.now(timezone.utc)
    checked = 0
    confirmed = 0
    failures = 0
    skipped = 0

    for prediction in pending:
        age = _age_days(prediction["predicted_at"], now)
        if age < _MIN_AGE_DAYS or age > _MAX_AGE_DAYS:
            skipped += 1
            continue

        pred_id = prediction["id"]
        district = prediction["district"]
        try:
            resp = requests.post(
                f"{api_url}/v1/predictions/{pred_id}/auto-verify", timeout=60
            )
            resp.raise_for_status()
            result = resp.json()
        except Exception as e:
            logger.error(f"Auto-verify failed for prediction #{pred_id} ({district}): {e}")
            failures += 1
            continue

        checked += 1
        verification = result.get("verification", {})
        outcome = verification.get("outcome")
        if outcome == "flood_confirmed":
            confirmed += 1
            logger.warning(
                f"CONFIRMED: prediction #{pred_id} ({district}) - "
                f"{verification.get('outcome_source')}"
            )
        else:
            logger.info(f"prediction #{pred_id} ({district}) - no evidence found")

    logger.info(
        f"Done. {checked} checked, {confirmed} confirmed, {skipped} skipped "
        f"(outside {_MIN_AGE_DAYS}-{_MAX_AGE_DAYS} day window), {failures} failures "
        f"out of {len(pending)} pending."
    )
    return 1 if checked == 0 and failures > 0 else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    args = parser.parse_args()
    return run(args.api_url)


if __name__ == "__main__":
    sys.exit(main())
