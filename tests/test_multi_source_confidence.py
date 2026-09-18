"""Regression tests for src/models/multi_source_confidence.py - the
real skill-weighted, coverage+agreement confidence engine that replaces
decision_card.py's old fixed `60 + 20·sat + 15·reports` heuristic."""

from src.models.multi_source_confidence import (
    RIVER_GAUGE_WEIGHT,
    SATELLITE_CONFIRMED_WEIGHT,
    SourceReading,
    fuse_sources,
)


def _reading(name, risk, weight=1.0, available=True, applicable=True, reason=None):
    return SourceReading(
        name=name,
        display_name=name.replace("_", " "),
        applicable=applicable,
        available=available,
        risk_0_100=risk,
        weight=weight,
        unavailable_reason=reason,
    )


def test_full_agreement_high_coverage_yields_high_confidence():
    """The exact scenario the redesign was asked to explain: several
    real sources broadly agree -> confidence should be high, not just
    a fixed number."""
    sources = [
        _reading("rainfall", 70.0, weight=1.0),
        _reading("river_gauge", 72.0, weight=RIVER_GAUGE_WEIGHT),
        _reading("satellite_sar", 68.0, weight=SATELLITE_CONFIRMED_WEIGHT),
    ]
    result = fuse_sources(sources)
    assert result.confidence > 80
    assert result.degraded is False
    assert "agree" in result.explanation.lower()
    assert "%" in result.explanation


def test_strong_disagreement_lowers_confidence_even_with_full_coverage():
    """Real ensemble spread-skill principle: coverage alone isn't
    enough - if the available sources actively disagree, confidence
    must fall, not stay high just because every source is present."""
    sources = [
        _reading("rainfall", 10.0, weight=1.0),
        _reading("river_gauge", 90.0, weight=RIVER_GAUGE_WEIGHT),
        _reading("satellite_sar", 15.0, weight=SATELLITE_CONFIRMED_WEIGHT),
    ]
    result = fuse_sources(sources)
    agree_sources = [
        _reading("rainfall", 70.0, weight=1.0),
        _reading("river_gauge", 72.0, weight=RIVER_GAUGE_WEIGHT),
        _reading("satellite_sar", 68.0, weight=SATELLITE_CONFIRMED_WEIGHT),
    ]
    agree_result = fuse_sources(agree_sources)
    assert result.confidence < agree_result.confidence
    assert result.agreement_factor < agree_result.agreement_factor


def test_missing_high_weight_sources_triggers_degraded_mode():
    """Directly matches the user's example: 'Confidence has fallen to
    54% because two major data sources are unavailable.'"""
    sources = [
        _reading("rainfall", 70.0, weight=1.0),
        _reading(
            "river_gauge",
            None,
            weight=RIVER_GAUGE_WEIGHT,
            available=False,
            reason="Earth Engine unavailable",
        ),
        _reading(
            "satellite_sar",
            None,
            weight=SATELLITE_CONFIRMED_WEIGHT,
            available=False,
            reason="no SAR pass in window",
        ),
    ]
    result = fuse_sources(sources)
    assert result.degraded is True
    assert len(result.missing) == 2
    assert "unavailable" in result.explanation.lower()
    assert "fallen" in result.explanation.lower()


def test_not_applicable_sources_excluded_from_coverage_denominator():
    """A district with no river gauge at all must not be penalized as
    if that gauge were "missing" - it was never going to be there."""
    sources = [
        _reading("rainfall", 50.0, weight=1.0),
        _reading("river_gauge", None, weight=RIVER_GAUGE_WEIGHT, applicable=False),
    ]
    result = fuse_sources(sources)
    assert result.missing == []
    assert len(result.not_applicable) == 1
    # Coverage should be 100% since the only applicable source (rainfall) is present
    assert result.coverage_factor == 100.0


def test_single_source_gets_moderate_not_extreme_agreement():
    sources = [_reading("rainfall", 80.0, weight=1.0)]
    result = fuse_sources(sources)
    assert result.agreement_factor == 55.0
    assert 0 < result.confidence < 100


def test_no_sources_available_returns_zero_confidence_honestly():
    sources = [
        _reading("rainfall", None, weight=1.0, available=False, reason="API down"),
    ]
    result = fuse_sources(sources)
    assert result.confidence == 0.0
    assert result.unified_risk is None
    assert "no real evidence" in result.explanation.lower()


def test_unified_risk_is_weight_biased_toward_higher_trust_source():
    """A real physical gauge reading disagreeing with rainfall should
    pull the fused risk toward the gauge, not split the difference
    evenly - it carries more weight for a real, cited reason."""
    sources = [
        _reading("rainfall", 20.0, weight=1.0),
        _reading("river_gauge", 80.0, weight=RIVER_GAUGE_WEIGHT),
    ]
    result = fuse_sources(sources)
    midpoint = (20.0 + 80.0) / 2
    assert result.unified_risk > midpoint


def test_explanation_lists_available_source_names_when_healthy():
    sources = [
        _reading("rainfall", 60.0, weight=1.0),
        _reading("river_gauge", 62.0, weight=RIVER_GAUGE_WEIGHT),
    ]
    result = fuse_sources(sources)
    assert "rainfall" in result.explanation.lower()
    assert "river gauge" in result.explanation.lower()


def test_confidence_never_exceeds_100_or_goes_negative():
    sources = [
        _reading("a", 50.0, weight=100.0),
        _reading("b", 50.0, weight=100.0),
    ]
    result = fuse_sources(sources)
    assert 0.0 <= result.confidence <= 100.0
