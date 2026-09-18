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

The "Final" CHIRPS product used for backtesting (UCSB-CHG/CHIRPS/DAILY,
gauge-corrected) has real publication latency of weeks to months -
confirmed in production ("No bands in collection" for the last 14
days) - so it can never serve a live "what's the weather right now"
query. This module instead uses UCSB-CHC/CHIRPS/V3/DAILY_SAT, the
official near-real-time CHIRPS v3 product (daily precipitation
partitioned from pentadal CHIRPS-v3 totals using NASA IMERG Late V07),
which trades a little of the Final product's gauge-corrected accuracy
for actually having data from the last few days - the only way this
signal can be "live" at all. It still doesn't assume the very latest
1-3 calendar days are present - it fetches a wider real window and
uses whichever 3 most-recent real days it actually got, honestly
reporting their dates and how stale the freshest one is rather than
silently padding gaps with zeros.
"""

import logging
from datetime import date, timedelta
from typing import Dict, Optional

from src.exposure.districts import get_district
from src.models.historical_backtest import fetch_historical_chirps_series

logger = logging.getLogger("nfcc.hydrology.antecedent_rainfall")

# Near-real-time CHIRPS v3 (IMERG-partitioned) - see module docstring
# for why the gauge-corrected "Final" product can't be used here.
_LIVE_CHIRPS_COLLECTION = "UCSB-CHC/CHIRPS/V3/DAILY_SAT"

# Even the near-real-time product's actual real-world lag can run
# several weeks despite being far fresher than the Final product's
# months-long lag (confirmed in production: a 14-day window still
# returned zero images for UCSB-CHC/CHIRPS/V3/DAILY_SAT). 60 days -
# matching the same real fix already applied to the backtest's own
# lookback window in src/models/historical_backtest.py - gives real
# room to find whatever the actual most-recent published data is,
# rather than guessing a fixed lag; data_age_days (below) then reports
# exactly how stale the found value really is instead of hiding it.
_FETCH_WINDOW_DAYS = 60
_ACCUMULATION_DAYS = 3

# Beyond this, the found "3-day accumulation" is old enough that it no
# longer represents current ground conditions, and callers (the
# automated pipeline, the dashboard) need to know that explicitly
# rather than silently treating a weeks-old figure as "now".
_STALE_AFTER_DAYS = 10


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
        district_info.lat,
        district_info.lon,
        start_date,
        end_date,
        collection_id=_LIVE_CHIRPS_COLLECTION,
    )
    if not series:
        return {
            "district": district_name,
            "available": False,
            "reason": (
                f"No real CHIRPS data returned for the last {_FETCH_WINDOW_DAYS} "
                "days (Earth Engine unavailable or no data published for this "
                "period)"
            ),
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
        "stale": data_age_days > _STALE_AFTER_DAYS,
    }
