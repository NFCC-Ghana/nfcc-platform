"""Regression tests for src/verification/outcome_verifier.py - combines
four real, independent confirmation sources via "any real confirmation
is sufficient", mirroring the same causal-independence reasoning used
for live risk fusion (src/models/multi_source_confidence.py)."""

from unittest.mock import patch

from src.verification.outcome_verifier import verify_outcome


def _unavailable(reason="not configured"):
    return {"available": False, "reason": reason}


def _patched(
    reliefweb=None, gdelt=None, citizen_count=0, satellite=None
):
    """Context manager stack for the four real sources verify_outcome
    checks - keeps each test focused on the one signal it's exercising."""
    reliefweb = reliefweb if reliefweb is not None else _unavailable()
    gdelt = gdelt if gdelt is not None else _unavailable()
    satellite = satellite if satellite is not None else {"source": "Sentinel-1 (simulated)"}
    return (
        patch("src.verification.outcome_verifier.search_flood_reports", return_value=reliefweb),
        patch("src.verification.outcome_verifier.search_flood_news", return_value=gdelt),
        patch(
            "src.verification.outcome_verifier.community_memory.get_validated_report_count_in_window",
            return_value=citizen_count,
        ),
        patch(
            "src.verification.outcome_verifier.sentinel_processor.detect_flood",
            return_value=satellite,
        ),
    )


def test_reliefweb_alone_confirms_outcome():
    p1, p2, p3, p4 = _patched(
        reliefweb={"available": True, "count": 1, "matched_reports": [{}]}
    )
    with p1, p2, p3, p4:
        result = verify_outcome("Tamale", "2026-01-01T00:00:00")

    assert result["outcome"] == "flood_confirmed"
    assert "ReliefWeb" in result["outcome_source"]


def test_no_signals_gives_honest_no_evidence_found_not_no_flood():
    """Absence of evidence across all four sources must never be
    reported as a confident 'no flood' - a real, distinct, more honest
    label is used instead."""
    p1, p2, p3, p4 = _patched()
    with p1, p2, p3, p4:
        result = verify_outcome("Kumasi", "2026-01-01T00:00:00")

    assert result["outcome"] == "no_evidence_found"
    assert result["outcome"] != "no_flood_confirmed"


def test_verified_citizen_reports_alone_confirm():
    p1, p2, p3, p4 = _patched(citizen_count=5)
    with p1, p2, p3, p4:
        result = verify_outcome("Ho", "2026-01-01T00:00:00")

    assert result["outcome"] == "flood_confirmed"
    assert "verified_citizen_reports" in result["outcome_source"]


def test_below_threshold_citizen_reports_do_not_confirm():
    p1, p2, p3, p4 = _patched(citizen_count=2)  # below the real threshold of 3
    with p1, p2, p3, p4:
        result = verify_outcome("Ho", "2026-01-01T00:00:00")

    assert result["outcome"] == "no_evidence_found"


def test_real_satellite_confirmation_alone_confirms():
    p1, p2, p3, p4 = _patched(
        satellite={"source": "Sentinel-1 SAR", "water_detected": True}
    )
    with p1, p2, p3, p4:
        result = verify_outcome("Tema", "2026-01-01T00:00:00")

    assert result["outcome"] == "flood_confirmed"
    assert "Sentinel-1 SAR" in result["outcome_source"]


def test_simulated_satellite_never_counts_as_confirmation():
    """A simulated (Earth-Engine-unavailable) satellite reading must
    never be mistaken for a real confirmation, even if it happens to
    say water_detected=True."""
    p1, p2, p3, p4 = _patched(
        satellite={"source": "Sentinel-1 (simulated)", "water_detected": True}
    )
    with p1, p2, p3, p4:
        result = verify_outcome("Tema", "2026-01-01T00:00:00")

    assert result["outcome"] == "no_evidence_found"


def test_window_dates_computed_from_predicted_at():
    p1, p2, p3, p4 = _patched()
    with p1 as mock_rw, p2, p3, p4:
        result = verify_outcome("Tamale", "2026-01-01T00:00:00", window_days=10)

    assert result["window_start"] == "2026-01-01"
    assert result["window_end"] == "2026-01-11"
    mock_rw.assert_called_once_with("Tamale", "2026-01-01", "2026-01-11")


def test_satellite_check_never_queries_a_future_date():
    """Real bug caught by live production testing: for a recent
    prediction, window_end (predicted_at + window_days) can land in the
    future - asking a real satellite for future imagery trivially finds
    nothing, which looks identical to "Earth Engine unavailable" but
    means something different. The satellite check must be capped at
    today."""
    from datetime import date, timedelta

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    p1, p2, p3, p4 = _patched()
    with p1, p2, p3, patch(
        "src.verification.outcome_verifier.sentinel_processor.detect_flood",
        return_value={"source": "Sentinel-1 (simulated)"},
    ) as mock_detect:
        # predicted "today" with a 1-day window -> window_end is tomorrow
        verify_outcome("Tamale", date.today().isoformat() + "T00:00:00", window_days=1)

    called_date = mock_detect.call_args.kwargs.get("date") or mock_detect.call_args.args[1]
    assert called_date != tomorrow
    assert called_date <= date.today().isoformat()


def test_multiple_confirmations_all_listed():
    p1, p2, p3, p4 = _patched(
        reliefweb={"available": True, "count": 1, "matched_reports": [{}]},
        citizen_count=4,
    )
    with p1, p2, p3, p4:
        result = verify_outcome("Tamale", "2026-01-01T00:00:00")

    assert result["outcome"] == "flood_confirmed"
    assert "ReliefWeb" in result["confirmations"]
    assert "verified_citizen_reports" in result["confirmations"]
