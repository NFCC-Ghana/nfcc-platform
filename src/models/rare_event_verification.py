"""Rare-event verification: does the live alert threshold have real
discriminative skill, or does it just get crossed by ordinary wet-
season rain regardless of whether a flood follows?

historical_backtest.py already disclosed it could not honestly compute
FAR/CSI from only 8 documented events, correctly - a flat POD/FAR needs
a complete day-by-day negative-event ground truth this platform's
historical record doesn't have. A real production run of that backtest
then showed *why* this matters: same-day POD=1.0 (7/7), but the
triggering rainfall values were 10-18mm - ordinary wet-season days, not
extreme rainfall (calculate_score(10) == 30, exactly the alert
threshold, so any single day >=10mm already "detects"). That result is
consistent with a threshold with zero real discriminative skill, not
evidence of genuine predictive skill.

This module doesn't invent the missing ground truth. It applies the
standard real-world answer to exactly this problem, used by every
operational verification system reviewed while researching this
(NOAA Storm Prediction Center's "practically perfect" hindcasts, the
WMO Flash Flood Guidance System, ECMWF/Copernicus GloFAS):

1. Treat "no documented flood within a short response window" as the
best-available negative-day label. This is explicitly an assumption,
disclosed rather than hidden: Ghana's flood record is real but not
exhaustive, so it can only ever OVERSTATE false alarms (an
undocumented real flood mislabeled as a false alarm), never
understate them - a conservative bias, not an inflated one.

2. Score rare-event skill with SEDI - the Symmetric Extremal
Dependence Index (Ferro & Stephenson 2011, "Extremal Dependence
Indices: Improved Verification Measures for Deterministic Forecasts
of Rare Binary Events", Weather and Forecasting 26(5)) - instead of
raw POD/FAR/CSI. Those standard scores are known to degenerate toward
trivial values (POD -> 1, CSI -> base rate) as an event gets rarer or
the sample gets smaller, which is exactly what the naive n=7 POD=1.0
result looks like. SEDI is purpose-built to stay meaningful
(non-degenerating, base-rate independent) in this regime and is the
literature's recommended score for it.

3. Report the plain-English number underneath the skill score: how
many independent multi-day "warning episodes" the current threshold
produces per year of real CHIRPS record - the actual operational cost
of this threshold (false-alarm burden on responders), not just an
abstract score.

4. Compare against a real, standard alternative: a per-district
percentile-of-local-climatology threshold - the actual method GloFAS
and the WMO Flash Flood Guidance System use to set warning thresholds
(reference thresholds tied to each location's own rainfall
distribution, not one flat mm value applied everywhere) - to test,
with the same real rainfall record, whether it reduces the warning-
episode rate while still catching the real documented events with
useful lead time.

Bootstrap confidence intervals are reported alongside every SEDI value
because the underlying event count is tiny (as few as 2-5 documented
events per district) - a point estimate alone would misrepresent how
uncertain that number really is. A moving-block bootstrap (not a
plain day-by-day resample) is used because daily rainfall is strongly
autocorrelated - resampling individual days independently would
understate the true uncertainty.
"""

import logging
import math
import random
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from src.alerts.formatter import calculate_score
from src.exposure.districts import get_district
from src.hydrology.flood_polygons import flood_polygons
from src.models.historical_backtest import (
    _ALERT_THRESHOLD,
    _rolling_3d_sums,
    fetch_historical_chirps_series,
)

logger = logging.getLogger("nfcc.models.rare_event_verification")

# How many days before (and including) a documented flood a threshold
# crossing counts as a "hit" rather than an unrelated false alarm.
# Deliberately short: the naive backtest found "lead times" of 47-58
# days, but those were driven by ordinary rain crossing a trivially low
# threshold, not a real flood-response relationship. 7 days is a
# conservative window for urban/riverine response lag in these basins,
# chosen so long antecedent-rainfall coincidences can't inflate hits.
_EVENT_WINDOW_DAYS = 7

# Real full CHIRPS archive coverage starts 1981; 1990 keeps requests
# smaller while still covering every documented event with room for a
# full-record contingency table (not just each event's lookback window).
_FULL_RECORD_START = "1990-01-01"

_BOOTSTRAP_BLOCK_DAYS = 30
_BOOTSTRAP_ITERATIONS = 500
_BOOTSTRAP_CI = 0.90
_EPSILON = 1e-9


def _flag_days(values: List[float], threshold: float) -> List[bool]:
    """Which days' calculate_score(value) crosses the real alert
    threshold - the exact same function every live endpoint uses."""
    return [calculate_score(v) >= threshold for v in values]


def _flag_days_raw_mm(values: List[float], mm_threshold: float) -> List[bool]:
    """Which days' raw rainfall (not run through calculate_score())
    crosses a percentile-derived mm threshold - used for the
    alternative, locally-calibrated threshold comparison."""
    return [v >= mm_threshold for v in values]


def _label_flood_days(series_dates: List[str], event_dates: List[date]) -> List[bool]:
    """A day is labeled a real flood-risk day if it falls within
    _EVENT_WINDOW_DAYS before, or on, any documented event date for
    this district. See module docstring: absence of a documented event
    is the best available "no flood" label, not a certainty."""
    windows = [(ev - timedelta(days=_EVENT_WINDOW_DAYS), ev) for ev in event_dates]
    labels = []
    for d_str in series_dates:
        d = date.fromisoformat(d_str)
        labels.append(any(start <= d <= end for start, end in windows))
    return labels


def contingency_table(flags: List[bool], labels: List[bool]) -> Dict[str, int]:
    """Real hits/misses/false_alarms/correct_negatives counts across
    every day in the series - not just the documented event days."""
    hits = sum(1 for f, l in zip(flags, labels) if f and l)
    misses = sum(1 for f, l in zip(flags, labels) if not f and l)
    false_alarms = sum(1 for f, l in zip(flags, labels) if f and not l)
    correct_negatives = sum(1 for f, l in zip(flags, labels) if not f and not l)
    return {
        "hits": hits,
        "misses": misses,
        "false_alarms": false_alarms,
        "correct_negatives": correct_negatives,
    }


def compute_sedi(
    hits: int, misses: int, false_alarms: int, correct_negatives: int
) -> Optional[float]:
    """Symmetric Extremal Dependence Index (Ferro & Stephenson 2011).
    Ranges -1 to 1 (1 = perfect discrimination, 0 = no better than a
    random/climatological guess); unlike POD/FAR/CSI it does not
    degenerate toward a trivial value as the event gets rarer or the
    sample shrinks, which is why it's used here instead of POD alone.
    Clamped away from 0/1 with a small epsilon (same fix used by the
    reference implementations) since H or F can be exactly 0 or 1 with
    a tiny real sample, which would otherwise make log() undefined."""
    total_pos = hits + misses
    total_neg = false_alarms + correct_negatives
    if total_pos == 0 or total_neg == 0:
        return None

    h = hits / total_pos
    f = false_alarms / total_neg
    h = min(max(h, _EPSILON), 1 - _EPSILON)
    f = min(max(f, _EPSILON), 1 - _EPSILON)

    numerator = math.log(f) - math.log(h) - math.log(1 - f) + math.log(1 - h)
    denominator = math.log(f) + math.log(h) + math.log(1 - f) + math.log(1 - h)
    if denominator == 0:
        return None
    return round(numerator / denominator, 3)


def compute_edi(
    hits: int, misses: int, false_alarms: int, correct_negatives: int
) -> Optional[float]:
    """Extremal Dependence Index - SEDI's non-symmetric predecessor
    (same paper). Reported alongside SEDI for reference; SEDI is the
    headline score since the literature recommends it as the more
    robust of the two."""
    total_pos = hits + misses
    total_neg = false_alarms + correct_negatives
    if total_pos == 0 or total_neg == 0:
        return None

    h = hits / total_pos
    f = false_alarms / total_neg
    h = min(max(h, _EPSILON), 1 - _EPSILON)
    f = min(max(f, _EPSILON), 1 - _EPSILON)

    denominator = math.log(f) + math.log(h)
    if denominator == 0:
        return None
    return round((math.log(f) - math.log(h)) / denominator, 3)


def count_warning_episodes(series_dates: List[str], flags: List[bool]) -> int:
    """Distinct warning episodes (runs of consecutive flagged days
    collapsed into one), not raw flagged-day count - a 5-day rain spell
    is one warning to a responder, not five. This is the plain-English
    "how often would this threshold have cried wolf" number."""
    episodes = 0
    prev_flagged = False
    for f in flags:
        if f and not prev_flagged:
            episodes += 1
        prev_flagged = f
    return episodes


def _years_covered(series_dates: List[str]) -> float:
    if len(series_dates) < 2:
        return 0.0
    start = date.fromisoformat(series_dates[0])
    end = date.fromisoformat(series_dates[-1])
    return max((end - start).days / 365.25, 1e-9)


def percentile_threshold_mm(values: List[float], percentile: float) -> float:
    """This district's own local-climatology rainfall percentile - the
    real method GloFAS and the WMO Flash Flood Guidance System use to
    set warning thresholds (a location-specific reference value tied to
    that location's own rainfall distribution), rather than one flat mm
    figure used everywhere regardless of local climate."""
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round((percentile / 100) * (len(ordered) - 1))))
    return ordered[idx]


def _bootstrap_sedi_ci(
    flags: List[bool], labels: List[bool], seed: int = 42
) -> Optional[Tuple[float, float]]:
    """Moving-block bootstrap confidence interval on SEDI. Daily
    rainfall is strongly autocorrelated, so resampling individual days
    independently would understate real uncertainty; resampling
    contiguous _BOOTSTRAP_BLOCK_DAYS-day blocks preserves that
    structure. With as few as 2-5 real documented events per district,
    a bare point estimate would misrepresent how uncertain SEDI here
    really is."""
    n = len(flags)
    if n < _BOOTSTRAP_BLOCK_DAYS * 2:
        return None

    rng = random.Random(seed)
    n_blocks = n // _BOOTSTRAP_BLOCK_DAYS
    scores = []
    for _ in range(_BOOTSTRAP_ITERATIONS):
        resampled_flags: List[bool] = []
        resampled_labels: List[bool] = []
        for _ in range(n_blocks):
            start = rng.randint(0, n - _BOOTSTRAP_BLOCK_DAYS)
            resampled_flags.extend(flags[start : start + _BOOTSTRAP_BLOCK_DAYS])
            resampled_labels.extend(labels[start : start + _BOOTSTRAP_BLOCK_DAYS])
        table = contingency_table(resampled_flags, resampled_labels)
        sedi = compute_sedi(**table)
        if sedi is not None:
            scores.append(sedi)

    if len(scores) < _BOOTSTRAP_ITERATIONS // 2:
        return None
    scores.sort()
    lower_idx = int((1 - _BOOTSTRAP_CI) / 2 * len(scores))
    upper_idx = int((1 - (1 - _BOOTSTRAP_CI) / 2) * len(scores)) - 1
    return round(scores[lower_idx], 3), round(
        scores[min(upper_idx, len(scores) - 1)], 3
    )


def _threshold_report(
    name: str, flags: List[bool], labels: List[bool], series_dates: List[str]
) -> Dict:
    table = contingency_table(flags, labels)
    sedi = compute_sedi(**table)
    edi = compute_edi(**table)
    ci = _bootstrap_sedi_ci(flags, labels)
    episodes = count_warning_episodes(series_dates, flags)
    years = _years_covered(series_dates)

    total_pos = table["hits"] + table["misses"]
    total_neg = table["false_alarms"] + table["correct_negatives"]
    return {
        "threshold_name": name,
        "contingency_table": table,
        "probability_of_detection": (
            round(table["hits"] / total_pos, 2) if total_pos else None
        ),
        "false_alarm_ratio": (
            round(table["false_alarms"] / (table["hits"] + table["false_alarms"]), 2)
            if (table["hits"] + table["false_alarms"])
            else None
        ),
        "sedi": sedi,
        "sedi_90pct_confidence_interval": ci,
        "edi": edi,
        "warning_episodes": episodes,
        "years_of_record": round(years, 1),
        "implied_warnings_per_year": round(episodes / years, 1) if years else None,
    }


def run_district_verification(district_name: str, percentile: float = 95.0) -> Dict:
    """Full rare-event verification for one district: real full-record
    CHIRPS rainfall, real documented events, both the current absolute
    alert threshold and a locally-calibrated percentile alternative,
    scored with SEDI (not just POD) plus bootstrap uncertainty."""
    district_info = get_district(district_name)
    if district_info is None:
        return {
            "district": district_name,
            "available": False,
            "reason": f"'{district_name}' is not one of the 9 districts with real coordinates registered",
        }

    events = flood_polygons.get_flood_events(district_name)
    if not events:
        return {
            "district": district_name,
            "available": False,
            "reason": "No documented historical flood events for this district",
        }
    event_dates = [date.fromisoformat(e["date"]) for e in events]

    end_date = (date.today() + timedelta(days=1)).isoformat()
    series = fetch_historical_chirps_series(
        district_info.lat, district_info.lon, _FULL_RECORD_START, end_date
    )
    if not series:
        return {
            "district": district_name,
            "available": False,
            "reason": "No real CHIRPS data returned (Earth Engine unavailable)",
        }

    series_dates = [d["date"] for d in series]
    daily_mm = [d["precipitation_mm"] for d in series]
    rolling_3d_mm = _rolling_3d_sums(series)
    labels = _label_flood_days(series_dates, event_dates)

    pct_mm = percentile_threshold_mm(daily_mm, percentile)

    reports = {
        "current_absolute_threshold": {
            "same_day": _threshold_report(
                "current_absolute_same_day",
                _flag_days(daily_mm, _ALERT_THRESHOLD),
                labels,
                series_dates,
            ),
            "rolling_3d": _threshold_report(
                "current_absolute_rolling_3d",
                _flag_days(rolling_3d_mm, _ALERT_THRESHOLD),
                labels,
                series_dates,
            ),
        },
        "local_percentile_threshold": {
            "percentile": percentile,
            "threshold_mm": round(pct_mm, 1),
            "same_day": _threshold_report(
                "percentile_same_day",
                _flag_days_raw_mm(daily_mm, pct_mm),
                labels,
                series_dates,
            ),
        },
    }

    return {
        "district": district_name,
        "available": True,
        "documented_events": len(events),
        "real_rainfall_series_days": len(series),
        "years_of_record": round(_years_covered(series_dates), 1),
        "event_window_days": _EVENT_WINDOW_DAYS,
        "reports": reports,
    }


def run_full_verification() -> Dict:
    """Rare-event verification for every district with >=1 documented
    real flood event and real registered coordinates - currently
    Tamale and Accra Central (the other 6 documented events' districts
    either lack coordinates, like North Tongu, or overlap these two)."""
    districts_with_events = sorted(
        {d for e in flood_polygons.get_flood_events() for d in e["districts"]}
    )
    results = {d: run_district_verification(d) for d in districts_with_events}
    return {
        "generated_at": date.today().isoformat(),
        "current_absolute_threshold_score": _ALERT_THRESHOLD,
        "districts": results,
        "methodology": (
            "SEDI (Symmetric Extremal Dependence Index, Ferro & Stephenson "
            "2011) scores rare-event discrimination without degenerating "
            "toward trivial values the way raw POD does at small sample "
            "sizes. 'No documented flood within a 7-day window' is used as "
            "the best-available negative-day label across the full real "
            "CHIRPS record (1990-present) - an assumption that can only "
            "overstate false alarms, never understate them, since Ghana's "
            "historical flood record, while real, is not exhaustive. The "
            "local-percentile threshold mirrors real GloFAS/WMO Flash Flood "
            "Guidance practice: a location-specific reference value from "
            "that district's own rainfall distribution, instead of one flat "
            "mm figure applied everywhere."
        ),
    }
