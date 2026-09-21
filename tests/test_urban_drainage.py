"""Regression tests for src/hydrology/urban_drainage.py, first wired
into a real score in this session (src/alerts/formatter.py's
calculate_score) after being imported-but-never-called since this
project's early development.

Guards a real bug found while verifying this module before wiring it
in: get_flood_risk_factor() used to return the same 0.8x multiplier for
a genuinely GOOD-drainage district and for a district this module has
zero real data on (UNKNOWN) - silently LOWERING the risk estimate for
missing data, backwards for a life-safety system.
"""

from src.hydrology.urban_drainage import urban_drainage


def test_accra_central_has_real_matching_drainage_data():
    """Accra Central's area_map entries (Central Accra, Kaneshie, Ring
    Road Central) genuinely match named entries in drainage_network -
    the one case this module's real data actually applies."""
    status = urban_drainage.get_drainage_status("Accra Central")
    assert status["overall_status"] != "UNKNOWN"
    assert len(status["primary_drainage"]) > 0 or len(status["urban_drainage"]) > 0


def test_district_with_no_area_map_entry_is_unknown():
    status = urban_drainage.get_drainage_status("Cape Coast")
    assert status["overall_status"] == "UNKNOWN"


def test_district_with_area_map_entry_but_no_real_match_is_still_unknown():
    """Tema/Kumasi/Tamale have area_map entries, but none of their named
    areas ("Community 1", "Atwima", "Gushegu") match anything in
    drainage_network - confirms they resolve to UNKNOWN, not a fabricated
    match."""
    for district in ("Tema", "Kumasi", "Tamale"):
        status = urban_drainage.get_drainage_status(district)
        assert status["overall_status"] == "UNKNOWN", district


def test_unknown_district_gets_neutral_risk_factor_not_reduced():
    """The exact bug this session found: UNKNOWN must never resolve to
    the same 0.8x multiplier as genuinely GOOD drainage."""
    factor = urban_drainage.get_flood_risk_factor("Cape Coast", rainfall_mm=20)
    assert factor == 1.0


def test_known_poor_drainage_district_increases_risk_factor():
    factor = urban_drainage.get_flood_risk_factor("Accra Central", rainfall_mm=20)
    assert factor > 1.0


def test_higher_rainfall_increases_risk_factor_for_known_district():
    low_rain = urban_drainage.get_flood_risk_factor("Accra Central", rainfall_mm=20)
    high_rain = urban_drainage.get_flood_risk_factor("Accra Central", rainfall_mm=90)
    assert high_rain > low_rain


def test_unknown_district_risk_factor_ignores_rainfall():
    """No data means no adjustment at all, regardless of how much rain -
    the module should not pretend to know anything about this district."""
    low_rain = urban_drainage.get_flood_risk_factor("Ho", rainfall_mm=10)
    high_rain = urban_drainage.get_flood_risk_factor("Ho", rainfall_mm=150)
    assert low_rain == high_rain == 1.0
