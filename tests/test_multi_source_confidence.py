"""Regression tests for src/models/multi_source_confidence.py - the
real skill-weighted, coverage+agreement confidence engine that replaces
decision_card.py's old fixed `60 + 20·sat + 15·reports` heuristic."""

from src.models.multi_source_confidence import (
    RIVER_GAUGE_WEIGHT,
    SATELLITE_CONFIRMED_WEIGHT,
    Pathway,
    SourceReading,
    combine_pathways,
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


# ============================================================
# combine_pathways() - independent causal pathways (pluvial rainfall
# vs. fluvial dam/river vs. direct observation), combined via noisy-OR,
# NOT weighted-mean-with-agreement-penalty. See module docstring for
# the real-world causal reasoning (rain alone, dam alone, or both
# together can each independently cause flooding).
# ============================================================


def _pathway(name, sources):
    return Pathway(name=name, display_name=name, sources=sources)


def test_dam_alone_high_risk_is_not_averaged_down_by_low_rainfall():
    """The exact scenario the user described: a dam overflowing with no
    local rainfall must still produce a HIGH overall risk - not a
    diluted middle-of-the-road number from averaging with calm
    rainfall."""
    pathways = [
        _pathway("rainfall", [_reading("rainfall", 5.0, weight=1.0)]),
        _pathway("dam_river", [_reading("dam", 90.0, weight=RIVER_GAUGE_WEIGHT)]),
    ]
    result = combine_pathways(pathways)
    assert result.unified_risk > 85  # noisy-OR: dominated by the dam pathway
    assert result.dominant_pathway == "dam_river"


def test_rainfall_alone_high_risk_with_no_dam_coverage():
    """A district with no dam/river coverage at all can still flood
    from rainfall alone - that pathway being inapplicable must not
    drag down the risk or count as a missing/degraded source."""
    pathways = [
        _pathway("rainfall", [_reading("rainfall", 88.0, weight=1.0)]),
        _pathway("dam_river", [_reading("dam", None, weight=RIVER_GAUGE_WEIGHT, applicable=False)]),
    ]
    result = combine_pathways(pathways)
    assert result.unified_risk > 80
    assert result.degraded is False
    assert result.coverage_factor == 100.0


def test_both_pathways_elevated_gives_compound_risk_higher_than_either_alone():
    pathways = [
        _pathway("rainfall", [_reading("rainfall", 60.0, weight=1.0)]),
        _pathway("dam_river", [_reading("dam", 60.0, weight=RIVER_GAUGE_WEIGHT)]),
    ]
    result = combine_pathways(pathways)
    assert result.unified_risk > 60.0  # noisy-OR: compounds, doesn't average to 60


def test_pathway_disagreement_does_not_reduce_confidence():
    """The core bug this redesign fixes: rainfall=LOW and dam=HIGH is
    not measurement noise to be penalized - it's two different real
    threats. Confidence should reflect coverage/internal-agreement, not
    cross-pathway disagreement."""
    disagreeing = combine_pathways(
        [
            _pathway("rainfall", [_reading("rainfall", 5.0, weight=1.0)]),
            _pathway("dam_river", [_reading("dam", 95.0, weight=RIVER_GAUGE_WEIGHT)]),
        ]
    )
    agreeing = combine_pathways(
        [
            _pathway("rainfall", [_reading("rainfall", 50.0, weight=1.0)]),
            _pathway("dam_river", [_reading("dam", 50.0, weight=RIVER_GAUGE_WEIGHT)]),
        ]
    )
    # Both pathways present and internally single-source in both cases -
    # confidence should be essentially the same regardless of whether
    # the two pathways happen to agree with each other.
    assert abs(disagreeing.confidence - agreeing.confidence) < 1.0


def test_pathway_genuinely_unavailable_reduces_coverage_and_confidence():
    """Unlike structural inapplicability, a pathway that SHOULD be
    checkable but isn't right now (e.g. Earth Engine down) is a real
    degradation."""
    pathways = [
        _pathway("rainfall", [_reading("rainfall", 60.0, weight=1.0)]),
        _pathway(
            "dam_river",
            [
                _reading(
                    "dam", None, weight=RIVER_GAUGE_WEIGHT, available=False, reason="EE down"
                )
            ],
        ),
    ]
    result = combine_pathways(pathways)
    assert result.coverage_factor == 50.0
    assert result.degraded is True
    assert "unavailable" in result.explanation.lower()


def test_risk_attribution_names_dominant_pathway():
    pathways = [
        _pathway("rainfall", [_reading("rainfall", 10.0, weight=1.0)]),
        _pathway("dam_river", [_reading("dam", 95.0, weight=RIVER_GAUGE_WEIGHT)]),
    ]
    result = combine_pathways(pathways)
    assert "dam_river" in result.risk_attribution
    assert "rainfall" in result.risk_attribution


def test_no_pathways_present_is_honestly_reported():
    pathways = [
        _pathway("rainfall", [_reading("rainfall", None, weight=1.0, available=False)]),
    ]
    result = combine_pathways(pathways)
    assert result.unified_risk is None
    assert result.confidence == 0.0
    assert "no independent flood-risk pathway" in result.risk_attribution.lower()
