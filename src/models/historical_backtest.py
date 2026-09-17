"""Historical backtesting: "what would CivicFlood have predicted before
this real flood event?"

Deliberately backtests calculate_score() (src/alerts/formatter.py) - the
exact function every live endpoint in this platform actually uses - not
the dormant models/xgboost_flood_risk.pkl. That model is loaded only for
a health check (confirmed by grep: .predict() is called nowhere in the
live pipeline) and was trained against flood_risk_score, a value that
correlates 0.92 with same-day precipitation in its own training data -
a synthetic formula derived from the same rolling-window features used
to predict it, not a real historical flood outcome. Backtesting the
function that's actually live is the only way to honestly answer what
this platform would really have said.

Two scoring variants are backtested per event, to give a real, evidence-
based answer to "do temporal features help" rather than an opinion:
- same_day: calculate_score(that day's real CHIRPS rainfall) - exactly
  replicates current live behavior (every endpoint feeds it a single
  precipitation number).
- rolling_3d: calculate_score(3-day rolling SUM of real CHIRPS rainfall)
  - the simplest real temporal feature already computed elsewhere in
    this codebase (roll_3d, in data/processed/accra_features_2024.parquet
    and rainfall_history.py) - tests whether accumulating rainfall over
    the days leading up to an event would have crossed the alert
    threshold earlier than a same-day reading does.

Honest limitation, disclosed rather than hidden: this can compute real
POD (probability of detection - did we cross the alert threshold before
each known flood?) and real lead time for the events in
src/hydrology/flood_polygons.py's database. It CANNOT honestly compute
FAR/CSI (false alarm rate, critical success index) at national scale,
because that requires knowing every day the threshold was crossed with
NO flood following - and this platform's historical flood record is
real but incomplete (8 documented events across ~18 years is nowhere
near an exhaustive day-by-day ground truth). A threshold crossing on an
undocumented day could be a genuine false alarm or an undocumented real
flood we have no record of - conflating the two would be presenting
false precision, exactly what this platform's other guardrails work has
been built to avoid.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from src.alerts.formatter import calculate_score, get_risk_tier
from src.exposure.districts import get_district
from src.hydrology.ee_auth import initialize_earth_engine
from src.hydrology.flood_polygons import flood_polygons

logger = logging.getLogger("nfcc.models.historical_backtest")

_CHIRPS_COLLECTION = "UCSB-CHG/CHIRPS/DAILY"
_ALERT_THRESHOLD = 30  # matches src/api/routes/alert_review.py's _REVIEW_THRESHOLD
_LOOKBACK_DAYS = 21  # real rainfall window fetched before each event date


def fetch_historical_chirps_series(
    lat: float, lon: float, start_date: str, end_date: str
) -> List[Dict]:
    """Real daily CHIRPS rainfall for a point over a date range, via one
    Earth Engine getRegion() call (a real per-pixel time series query,
    not N separate per-day calls) - the CHIRPS archive covers 1981-
    present, so this reaches every event in flood_polygons.py's database.
    Returns [] if Earth Engine isn't reachable, rather than raising -
    the same graceful-degradation contract every other real data source
    in this codebase follows."""
    if not initialize_earth_engine():
        logger.warning("Earth Engine unavailable - cannot fetch historical CHIRPS series")
        return []

    import ee

    try:
        point = ee.Geometry.Point(lon, lat)
        collection = (
            ee.ImageCollection(_CHIRPS_COLLECTION)
            .filterDate(start_date, end_date)
            .select("precipitation")
        )
        region_data = collection.getRegion(point, scale=5566).getInfo()
        if len(region_data) < 2:
            return []

        header = region_data[0]
        idx_time = header.index("time")
        idx_precip = header.index("precipitation")

        series = []
        for row in region_data[1:]:
            if row[idx_precip] is None:
                continue
            day = datetime.utcfromtimestamp(row[idx_time] / 1000).date()
            series.append({"date": day.isoformat(), "precipitation_mm": row[idx_precip]})
        series.sort(key=lambda r: r["date"])
        return series
    except Exception as e:
        logger.warning(f"CHIRPS historical fetch failed for ({lat},{lon}): {e}")
        return []


def _rolling_3d_sums(series: List[Dict]) -> List[float]:
    """3-day rolling SUM of real daily rainfall - the simplest temporal
    feature already used elsewhere in this codebase (roll_3d)."""
    sums = []
    for i in range(len(series)):
        window = series[max(0, i - 2) : i + 1]
        sums.append(sum(d["precipitation_mm"] for d in window))
    return sums


def _first_threshold_crossing(
    values: List[float], series_dates: List[str], event_date: date
) -> Optional[Dict]:
    """First day (in chronological order) a real rainfall-derived value
    would have crossed the live alert threshold via calculate_score() -
    a standalone function (not a closure) so it has its own direct test
    coverage without needing a real Earth Engine call."""
    for i, v in enumerate(values):
        score = calculate_score(v)
        if score >= _ALERT_THRESHOLD:
            day = date.fromisoformat(series_dates[i])
            return {
                "date": day.isoformat(),
                "value_mm": round(v, 1),
                "score": score,
                "risk_tier": get_risk_tier(score),
                "lead_time_days": (event_date - day).days,
            }
    return None


def backtest_event(event: Dict) -> Dict:
    """Backtest one real historical flood event: fetch real CHIRPS
    rainfall for _LOOKBACK_DAYS before the event, run calculate_score()
    day-by-day (both same-day and rolling-3d variants), and find the
    first day each variant would have crossed the real alert threshold -
    lead_time_days is how far before the actual flood that would have
    been."""
    event_date = date.fromisoformat(event["date"])
    lookback_start = (event_date - timedelta(days=_LOOKBACK_DAYS)).isoformat()
    lookback_end = (event_date + timedelta(days=1)).isoformat()

    district = event["districts"][0]
    district_info = get_district(district)
    if district_info is None:
        return {
            "event_id": event.get("event_id"),
            "date": event["date"],
            "district": district,
            "available": False,
            "reason": f"'{district}' is not one of the 9 districts with real coordinates registered",
        }

    series = fetch_historical_chirps_series(
        district_info.lat, district_info.lon, lookback_start, lookback_end
    )
    if not series:
        return {
            "event_id": event.get("event_id"),
            "date": event["date"],
            "district": district,
            "available": False,
            "reason": "No real CHIRPS data returned (Earth Engine unavailable or no data for this period)",
        }

    rolling_3d = _rolling_3d_sums(series)
    series_dates = [d["date"] for d in series]

    same_day_crossing = _first_threshold_crossing(
        [d["precipitation_mm"] for d in series], series_dates, event_date
    )
    rolling_crossing = _first_threshold_crossing(rolling_3d, series_dates, event_date)

    return {
        "event_id": event.get("event_id"),
        "date": event["date"],
        "district": district,
        "district_coords": {"lat": district_info.lat, "lon": district_info.lon},
        "available": True,
        "real_rainfall_series_days": len(series),
        "same_day": {
            "detected": same_day_crossing is not None,
            "first_crossing": same_day_crossing,
        },
        "rolling_3d": {
            "detected": rolling_crossing is not None,
            "first_crossing": rolling_crossing,
        },
    }


def run_full_backtest() -> Dict:
    """Backtest calculate_score() against every real event in
    src/hydrology/flood_polygons.py's database. Returns per-event
    results plus aggregate POD (probability of detection) and lead-time
    stats for both scoring variants - see module docstring for why
    FAR/CSI are not computed here."""
    events = flood_polygons.get_flood_events()
    results = [backtest_event(e) for e in events]

    def _aggregate(variant: str) -> Dict:
        evaluated = [r for r in results if r.get("available")]
        detected = [r for r in evaluated if r[variant]["detected"]]
        lead_times = [
            r[variant]["first_crossing"]["lead_time_days"] for r in detected
        ]
        return {
            "events_evaluated": len(evaluated),
            "events_detected": len(detected),
            "probability_of_detection": (
                round(len(detected) / len(evaluated), 2) if evaluated else None
            ),
            "lead_time_days": {
                "mean": round(sum(lead_times) / len(lead_times), 1) if lead_times else None,
                "min": min(lead_times) if lead_times else None,
                "max": max(lead_times) if lead_times else None,
            },
        }

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "alert_threshold": _ALERT_THRESHOLD,
        "lookback_days": _LOOKBACK_DAYS,
        "events": results,
        "aggregate": {
            "same_day": _aggregate("same_day"),
            "rolling_3d": _aggregate("rolling_3d"),
        },
        "limitations": (
            "POD (probability of detection) and lead time are real, computed "
            "from real CHIRPS rainfall against calculate_score() - the exact "
            "function every live endpoint uses. FAR (false alarm ratio) and "
            "CSI are NOT computed: they require knowing every day the "
            "threshold was crossed with no flood following, and this "
            "platform's historical flood record, while real, is not an "
            "exhaustive day-by-day ground truth - only 8 documented events "
            "across roughly two decades. A threshold crossing on an "
            "undocumented day could be a genuine false alarm or an "
            "undocumented real flood; reporting a false-alarm rate from "
            "this data would be false precision."
        ),
    }
