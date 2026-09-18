"""Regression tests for src/hydrology/fluvial_pathway.py - the shared
real river/dam SourceReading construction used both by
POST /decision/card (via an already-fetched /situation dict) and the
standalone GET /v1/districts/{district}/fluvial-risk (fetched fresh,
independent of any rainfall input) - see module docstring for why that
independence is the whole point: a dam overflowing with zero local
rain must be checkable on its own."""

from src.hydrology.fluvial_pathway import build_fluvial_sources


def test_river_gauge_mapped_from_real_status():
    sources = build_fluvial_sources(
        river_gauge={"available": True, "status": "DANGER"},
        dam_intelligence=[],
        river_applicable=True,
    )
    river = next(s for s in sources if s.name == "river_gauge")
    assert river.available is True
    assert river.risk_0_100 == 75.0


def test_river_not_applicable_district_excluded_from_coverage():
    sources = build_fluvial_sources(
        river_gauge={"available": False, "reason": "no coverage"},
        dam_intelligence=[],
        river_applicable=False,
    )
    river = next(s for s in sources if s.name == "river_gauge")
    assert river.applicable is False


def test_dam_direct_reading_included_when_available():
    sources = build_fluvial_sources(
        river_gauge={},
        dam_intelligence=[{"dam": "Akosombo", "available": True, "status": "FLOOD"}],
        river_applicable=False,
    )
    dam = next(s for s in sources if s.name == "dam_akosombo")
    assert dam.available is True
    assert dam.risk_0_100 == 95.0


def test_dam_unavailable_still_present_as_missing_not_dropped():
    """Bagre's own status is always available=False (no live feed) -
    it must still appear so the pathway honestly reflects the gap,
    rather than silently disappearing."""
    sources = build_fluvial_sources(
        river_gauge={},
        dam_intelligence=[{"dam": "Bagre", "available": False, "reason": "no API"}],
        river_applicable=False,
    )
    dam = next(s for s in sources if s.name == "dam_bagre")
    assert dam.available is False
    assert dam.applicable is True


def test_upstream_proxy_included_as_separate_source():
    sources = build_fluvial_sources(
        river_gauge={},
        dam_intelligence=[
            {
                "dam": "Bagre",
                "available": False,
                "reason": "no API",
                "upstream_proxy": {"available": True, "status": "WARNING"},
            }
        ],
        river_applicable=False,
    )
    proxy = next(s for s in sources if s.name == "dam_bagre_upstream_proxy")
    assert proxy.available is True
    assert proxy.risk_0_100 == 45.0


def test_no_upstream_proxy_key_means_no_proxy_source():
    sources = build_fluvial_sources(
        river_gauge={},
        dam_intelligence=[{"dam": "Kompienga", "available": False, "reason": "no API"}],
        river_applicable=False,
    )
    assert not any("proxy" in s.name for s in sources)
