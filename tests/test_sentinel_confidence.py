"""Direct tests for src/hydrology/sentinel_processor.py's
_confidence_from_sar_margins - the real, standalone arithmetic behind
Sentinel-1 detection confidence, extracted specifically so it can be
tested without mocking Earth Engine's real call chain (detect_flood()
itself has no test coverage in this codebase - a pre-existing gap - and
would need a long, fragile mock to exercise end-to-end)."""

import pytest

from src.hydrology.sentinel_processor import (
    _VH_THRESHOLD_DB,
    _VV_THRESHOLD_DB,
    _confidence_from_sar_margins,
)


def test_missing_means_return_honest_floor():
    """Can't compute a real margin without both means - don't guess."""
    assert _confidence_from_sar_margins(None, None) == 0.55
    assert _confidence_from_sar_margins(5.0, None) == 0.55
    assert _confidence_from_sar_margins(None, 1.0) == 0.55


def test_exactly_at_threshold_is_least_confident():
    """Right at the classification boundary (margin=0 for both bands) -
    the most ambiguous case, so confidence should sit at the real floor."""
    result = _confidence_from_sar_margins(_VH_THRESHOLD_DB, _VV_THRESHOLD_DB)
    assert result == pytest.approx(0.55)


def test_far_above_threshold_is_confident_water():
    """Both bands well above threshold - a clear, decisive water
    classification should score near the ceiling."""
    result = _confidence_from_sar_margins(
        _VH_THRESHOLD_DB * 3, _VV_THRESHOLD_DB * 3
    )
    assert result == pytest.approx(0.90)


def test_far_below_threshold_is_confident_no_water():
    """Both bands well below threshold - a clear, decisive no-water
    classification deserves the same confidence boost as a clear
    detection, by design (this measures decisiveness, not water volume)."""
    result = _confidence_from_sar_margins(
        -_VH_THRESHOLD_DB * 3, -_VV_THRESHOLD_DB * 3
    )
    assert result == pytest.approx(0.90)


def test_confidence_never_exceeds_ceiling():
    """An extreme, physically-implausible margin still clips to 0.90 -
    the function never claims more certainty than its own real ceiling."""
    result = _confidence_from_sar_margins(1000.0, 1000.0)
    assert result == 0.90


def test_confidence_symmetric_around_threshold():
    """Equal distance above vs. below the threshold should produce
    identical confidence - the function measures decisiveness in either
    direction, not "how much water," which is what makes it valid for
    both a real detection and a real non-detection."""
    above = _confidence_from_sar_margins(
        _VH_THRESHOLD_DB * 2, _VV_THRESHOLD_DB * 2
    )
    below = _confidence_from_sar_margins(0.0, 0.0)
    # 0.0 is exactly one full threshold-width below the threshold on each
    # band (margin=-1), the same distance 2x threshold is above it
    # (margin=+1) - both should land at the same confidence.
    assert above == pytest.approx(below)
