"""Real, live antecedent rainfall accumulation for a district - the
production wiring of what src/models/rare_event_verification.py proved
against 36.7 years of real CHIRPS data: a 3-day rolling SUM of real
observed rainfall has meaningfully better rare-event skill (SEDI) than
same-day/forecast-only scoring in every backtested district (Accra
Central/East/West, Tamale), roughly doubling probability of detection
at the same false-alarm rate.

scripts/automated_risk_assessment.py (the actual scheduled production
pipeline, GitHub Actions -> POST /alerts/assess) previously only ever
looked FORWARD (Open-Meteo's next-24h forecast) - a real, useful, but
purely anticipatory signal. This module supplies the complementary
BACKWARD-looking signal - real rain that has already fallen and is
already accumulating in soil/rivers - computed here, server-side,
because Earth Engine authentication only works inside this Cloud Run
service's own identity (confirmed this session: no
GEE_SERVICE_ACCOUNT_KEY exists, auth relies on the Cloud Run service
account's ADC + IAM grant); the GitHub Actions runner that calls this
has no such credential, so it fetches this value over HTTP instead of
calling Earth Engine itself.

CHIRPS has real publication latency (the most recent 1-3 days often
aren't available yet), so this doesn't assume "the last 3 calendar
days" are actually present - it fetches a wider real window and uses
whichever 3 most-recent real days it actually got, honestly reporting
their dates and how stale the freshest one is rather than silently
padding gaps with zeros.
"""

import logging
from datetime import date, timedelta
from typing import Dict, Optional

from src.exposure.districts import get_district
from src.models.historical_backtest import fetch_historical_chirps_series

logger = logging.getLogger("nfcc.hydrology.antecedent_rainfall")

# CHIRPS "final" product typically lags several days; widening the
# fetch window well past 3 days means a real recent value is still
# found even when the latest 1-3 days aren't published yet.
_FETCH_WINDOW_DAYS = 14
_ACCUMULATION_DAYS = 3


def get_antecedent_rainfall(district_name: str) -> Dict:
    """Real sum of the most recent _ACCUMULATION_DAYS days of CHIRPS
    rainfall actually available for this district - honestly reports
    which real dates were used and how many days old the freshest one
    is, rather than assuming today's or yesterday's data exists."""
    district_info = get_district(district_name)
    if district_info is None:
        return {
            "district": district_name,
            "available": False,
            "reason": f"'{district_name}' is not one of the 9 districts with real coordinates registered",
        }

    end_date = (date.today() + timedelta(days=1)).isoformat()
    start_date = (date.today() - timedelta(days=_FETCH_WINDOW_DAYS)).isoformat()
    series = fetch_historical_chirps_series(
        district_info.lat, district_info.lon, start_date, end_date
    )
    if not series:
        return {
            "district": district_name,
            "available": False,
            "reason": "No real CHIRPS data returned (Earth Engine unavailable)",
        }

    recent = series[-_ACCUMULATION_DAYS:]
    total_mm = round(sum(d["precipitation_mm"] for d in recent), 1)
    freshest_date = date.fromisoformat(recent[-1]["date"])
    data_age_days = (date.today() - freshest_date).days

    return {
        "district": district_name,
        "available": True,
        "rolling_3d_mm": total_mm,
        "days_used": [d["date"] for d in recent],
        "freshest_date": recent[-1]["date"],
        "data_age_days": data_age_days,
    }
