"""Regression tests for src/hydrology/flood_polygons.py - the real,
dated historical flood event database. Had zero test coverage before;
covers both the 2015 Accra fatality-count correction and the null-safety
fix needed after adding real events with honestly-undocumented fields
(rainfall_mm/population_affected/etc. = None rather than a fabricated
placeholder), which the aggregation functions did not originally handle."""

from src.hydrology.flood_polygons import flood_polygons


def test_2015_accra_fatality_count_corrected():
    events = flood_polygons.get_flood_events("Accra Central")
    event = next(e for e in events if e["event_id"] == "2015_accra")
    assert event["fatalities"] == 150
    assert "fatalities_reported_range" in event


def test_tamale_has_events_with_undocumented_fields():
    """2007_northern and 2010_10_bagre honestly have rainfall_mm=None -
    confirms the test data itself still represents this real gap,
    guarding against someone "fixing" it back to a fabricated number."""
    events = flood_polygons.get_flood_events("Tamale")
    assert any(e["rainfall_mm"] is None for e in events)


def test_flood_risk_summary_does_not_crash_on_none_fields():
    """This crashed before the fix: sum()'s default only applies when a
    key is missing, not when it's explicitly None."""
    for district in ("Tamale", "Accra Central", "Accra West", "Accra East"):
        summary = flood_polygons.get_flood_risk_summary(district)
        assert isinstance(summary["total_affected"], int)
        assert isinstance(summary["total_fatalities"], int)


def test_flood_inundation_risk_does_not_crash_on_none_rainfall():
    """This crashed before the fix: abs(None - rainfall_mm) and division
    against a None best_match rainfall value."""
    for district in ("Tamale", "Accra Central"):
        result = flood_polygons.get_flood_inundation_risk(district, 70)
        assert "risk_level" in result or "message" in result


def test_inundation_risk_excludes_events_without_real_rainfall():
    """The nearest-rainfall comparison must only match against events
    that actually recorded a real rainfall figure - matching against a
    None value would be comparing against nothing real."""
    result = flood_polygons.get_flood_inundation_risk("Tamale", 70)
    if "similar_event" in result:
        events = flood_polygons.get_flood_events("Tamale")
        matched = next(e for e in events if e["date"] == result["similar_event"])
        assert matched["rainfall_mm"] is not None


def test_eight_real_events_present():
    all_events = flood_polygons.get_flood_events()
    assert len(all_events) == 8
