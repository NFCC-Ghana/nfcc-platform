"""Regression tests for src/database/observation_history_db.py - the
real, durable historical archive of every raw source reading. Uses the
same shared real test database every other DB test in this suite uses
(tests/conftest.py's session-scoped initialize_database fixture) -
district names chosen per test to avoid cross-test collisions, matching
the established convention elsewhere in tests/."""

from src.database.observation_history_db import (
    get_observations,
    init_observation_history_table,
    save_observation,
)

init_observation_history_table()


def test_save_and_retrieve_observation():
    result = save_observation(
        district="_TestObsHistory_River",
        source="river_gauge",
        value=82.5,
        unit="m",
        quality_flag="pass",
        observation_date="2026-09-01T00:00:00",
    )
    assert result["id"] is not None

    rows = get_observations(district="_TestObsHistory_River")
    assert len(rows) == 1
    assert rows[0]["source"] == "river_gauge"
    assert rows[0]["value"] == 82.5
    assert rows[0]["quality_flag"] == "pass"


def test_missing_reading_is_a_real_row_not_skipped():
    """value=None with quality_flag='missing' must be stored as a real,
    honest row - a documented absence, not silently dropped."""
    save_observation(
        district="_TestObsHistory_Missing",
        source="dam_river",
        value=None,
        unit="risk_0_100",
        quality_flag="missing",
    )
    rows = get_observations(district="_TestObsHistory_Missing")
    assert len(rows) == 1
    assert rows[0]["value"] is None
    assert rows[0]["quality_flag"] == "missing"


def test_filter_by_source():
    save_observation("_TestObsHistory_Filter", "dam_akosombo", 75.0, "m", "pass")
    save_observation("_TestObsHistory_Filter", "rainfall_forecast", 12.0, "mm", "pass")

    dam_only = get_observations(district="_TestObsHistory_Filter", source="dam_akosombo")
    assert len(dam_only) == 1
    assert dam_only[0]["source"] == "dam_akosombo"


def test_most_recent_first():
    save_observation("_TestObsHistory_Order", "rainfall_forecast", 1.0, "mm", "pass")
    save_observation("_TestObsHistory_Order", "rainfall_forecast", 2.0, "mm", "pass")
    rows = get_observations(district="_TestObsHistory_Order")
    assert rows[0]["value"] == 2.0
