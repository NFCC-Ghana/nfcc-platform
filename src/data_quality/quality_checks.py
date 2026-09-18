"""Real-time data quality control, implementing the core tests from
QARTOD (Quality Assurance/Quality Control of Real-Time Oceanographic
Data) - the established US IOOS/NOAA standard for exactly this
problem: detecting a stuck sensor (flat-line), an impossible reading
(gross range), a suspicious jump (spike, rate-of-change), or a data
feed that's gone stale (freshness/time-gap), applied here to
hydrometeorological data instead of oceanographic data since the
underlying failure modes are identical - a satellite altimetry reading
or a rainfall estimate can be stuck, out-of-range, or stale exactly
the way a water-quality sensor can.

QARTOD defines required tests (syntax, gross range, time gap) and
strongly recommended tests (flat line, rate of change, spike) - this
module implements the ones that apply to this platform's single-value,
periodic readings (CHIRPS rainfall, Open-Meteo forecasts, DAHITI river/
dam altimetry, SMAP soil moisture): gross_range, spike, rate_of_change,
flat_line, and freshness (QARTOD's time-gap test, reframed as "how
stale is this reading" rather than "did a new one arrive on schedule",
since every one of this platform's sources is polled, not pushed).

Aggregation follows QARTOD's own convention: the worst flag among
individual tests wins (FAIL > SUSPECT > NOT_EVALUATED > MISSING > PASS
in severity), so a single failing test can't be diluted by several
passing ones - the same reasoning already applied to fusion confidence
elsewhere in this platform (src/models/multi_source_confidence.py):
don't average away a real problem.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional, Sequence


class QCFlag(Enum):
    PASS = "pass"
    SUSPECT = "suspect"
    FAIL = "fail"
    MISSING = "missing"
    NOT_EVALUATED = "not_evaluated"


# QARTOD's own numeric flag codes (1=pass, 2=not_evaluated, 3=suspect,
# 4=fail, 9=missing) - kept alongside the enum so a report can be
# expressed either way without inventing a second incompatible scheme.
_QARTOD_CODE = {
    QCFlag.PASS: 1,
    QCFlag.NOT_EVALUATED: 2,
    QCFlag.SUSPECT: 3,
    QCFlag.FAIL: 4,
    QCFlag.MISSING: 9,
}

# Severity order for aggregation - worst flag wins.
_SEVERITY = {
    QCFlag.FAIL: 4,
    QCFlag.SUSPECT: 3,
    QCFlag.NOT_EVALUATED: 2,
    QCFlag.MISSING: 1,
    QCFlag.PASS: 0,
}


@dataclass(frozen=True)
class QCResult:
    test_name: str
    flag: QCFlag
    detail: str

    @property
    def qartod_code(self) -> int:
        return _QARTOD_CODE[self.flag]


def gross_range_test(
    value: Optional[float], valid_min: float, valid_max: float
) -> QCResult:
    """QARTOD gross range test: is the value physically/sensor-range
    plausible at all."""
    if value is None:
        return QCResult("gross_range", QCFlag.MISSING, "no value to check")
    if value < valid_min or value > valid_max:
        return QCResult(
            "gross_range",
            QCFlag.FAIL,
            f"{value} outside real plausible range [{valid_min}, {valid_max}]",
        )
    return QCResult("gross_range", QCFlag.PASS, f"{value} within [{valid_min}, {valid_max}]")


def spike_test(
    value: Optional[float],
    previous: Optional[float],
    following: Optional[float],
    threshold: float,
) -> QCResult:
    """QARTOD spike test: flags a value that jumps away from its
    neighbors and back, the signature of noise/error rather than a
    real transition. Needs a real value before AND after this one, so
    it can only run once a following reading exists (never real-time
    on the newest point) - the recommended tradeoff to avoid false
    positives on genuine fast-moving events (QARTOD manuals)."""
    if value is None or previous is None or following is None:
        return QCResult("spike", QCFlag.NOT_EVALUATED, "insufficient neighboring readings")
    spike_magnitude = abs(value - (previous + following) / 2.0) - abs(following - previous) / 2.0
    if spike_magnitude > threshold:
        return QCResult(
            "spike", QCFlag.SUSPECT, f"spike magnitude {spike_magnitude:.2f} > {threshold}"
        )
    return QCResult("spike", QCFlag.PASS, "no spike detected")


def rate_of_change_test(
    value: Optional[float],
    previous_value: Optional[float],
    hours_elapsed: float,
    max_rate_per_hour: float,
) -> QCResult:
    """QARTOD rate-of-change test: is this transition physically
    plausible given how much time passed."""
    if value is None or previous_value is None or hours_elapsed <= 0:
        return QCResult("rate_of_change", QCFlag.NOT_EVALUATED, "insufficient data")
    rate = abs(value - previous_value) / hours_elapsed
    if rate > max_rate_per_hour:
        return QCResult(
            "rate_of_change",
            QCFlag.SUSPECT,
            f"{rate:.3f}/hr exceeds {max_rate_per_hour}/hr",
        )
    return QCResult("rate_of_change", QCFlag.PASS, f"{rate:.3f}/hr is plausible")


def flat_line_test(
    recent_values: Sequence[Optional[float]], tolerance: float, min_repeats: int
) -> QCResult:
    """QARTOD flat-line test: N consecutive near-identical readings is
    the classic signature of a stuck sensor or a cached/frozen feed,
    not a genuinely unchanging real quantity."""
    values = [v for v in recent_values if v is not None]
    if len(values) < min_repeats:
        return QCResult("flat_line", QCFlag.NOT_EVALUATED, "not enough history")
    window = values[-min_repeats:]
    spread = max(window) - min(window)
    if spread <= tolerance:
        return QCResult(
            "flat_line",
            QCFlag.SUSPECT,
            f"last {min_repeats} readings vary by only {spread:.4f} (tolerance {tolerance})",
        )
    return QCResult("flat_line", QCFlag.PASS, "varying normally")


def freshness_test(
    observation_time: Optional[datetime], now: datetime, max_age_hours: float
) -> QCResult:
    """QARTOD's time-gap test, reframed for a polled (not pushed) data
    source: how stale is the most recent real reading, against how
    fresh this specific source is realistically expected to be (a
    satellite altimetry station's "fresh" is measured in days; an
    hourly forecast API's is measured in hours - max_age_hours is
    caller-supplied per source, not one constant for everything)."""
    if observation_time is None:
        return QCResult("freshness", QCFlag.MISSING, "no observation timestamp")
    age_hours = (now - observation_time).total_seconds() / 3600.0
    if age_hours < 0:
        return QCResult("freshness", QCFlag.SUSPECT, f"observation time is {-age_hours:.1f}h in the future")
    if age_hours > max_age_hours:
        return QCResult(
            "freshness", QCFlag.FAIL, f"{age_hours:.1f}h old exceeds {max_age_hours}h max"
        )
    return QCResult("freshness", QCFlag.PASS, f"{age_hours:.1f}h old")


def completeness_percent(expected_count: int, actual_count: int) -> float:
    """Real, simple completeness metric - percent of expected real
    readings actually present in a window (e.g. 3 of the last 3
    antecedent-rainfall days found, vs. 1 of 3)."""
    if expected_count <= 0:
        return 100.0
    return round(100.0 * min(actual_count, expected_count) / expected_count, 1)


@dataclass(frozen=True)
class QualityReport:
    source: str
    overall: QCFlag
    tests: List[QCResult]
    completeness_percent: Optional[float] = None

    @property
    def overall_qartod_code(self) -> int:
        return _QARTOD_CODE[self.overall]


def aggregate_quality(
    source: str, tests: List[QCResult], completeness: Optional[float] = None
) -> QualityReport:
    """QARTOD's own aggregation convention: the single worst flag among
    all tests wins - a real FAIL is never diluted by other tests
    passing (the same non-averaging principle already used for
    multi-source risk fusion elsewhere in this platform)."""
    if not tests:
        return QualityReport(source, QCFlag.NOT_EVALUATED, [], completeness)
    worst = max(tests, key=lambda t: _SEVERITY[t.flag])
    return QualityReport(source, worst.flag, list(tests), completeness)
