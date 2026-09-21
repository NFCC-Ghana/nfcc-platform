"""Regression tests for calculate_score()'s optional district parameter
(src/alerts/formatter.py) - real urban drainage data
(src/hydrology/urban_drainage.py) wired into the live score for the
first time this session, after sitting imported-but-never-called since
early development.

The core guarantee these tests protect: every existing caller that
doesn't pass district must be byte-for-byte unaffected - this function
is also used by historical backtesting/rare-event verification, which
need the pure precipitation-only curve to stay valid against real past
events.
"""

from src.alerts.formatter import calculate_score


def test_no_district_is_completely_unaffected():
    """The backward-compatibility guarantee itself."""
    for precipitation in (0, 5, 15, 25, 40, 60, 100):
        assert calculate_score(precipitation) == calculate_score(precipitation, district=None)


def test_district_with_no_real_drainage_data_matches_no_district():
    """UNKNOWN districts get a neutral 1.0x - score must be identical to
    not passing a district at all."""
    for precipitation in (10, 30, 50, 80):
        assert calculate_score(precipitation) == calculate_score(precipitation, district="Ho")
        assert calculate_score(precipitation) == calculate_score(precipitation, district="Cape Coast")


def test_known_poor_drainage_district_increases_score():
    """Accra Central has real, known-poor drainage data - the score
    must be strictly higher than the plain precipitation curve for the
    same rainfall, for any rainfall high enough to produce a nonzero
    base score."""
    plain = calculate_score(40)
    with_drainage = calculate_score(40, district="Accra Central")
    assert with_drainage > plain


def test_score_never_exceeds_100_even_with_drainage_multiplier():
    result = calculate_score(200, district="Accra Central")
    assert result <= 100


def test_zero_precipitation_stays_zero_regardless_of_district():
    assert calculate_score(0, district="Accra Central") == 0.0


def test_situation_endpoint_actually_applies_drainage_adjustment(api_client):
    """Confirms the wiring reaches the real /situation endpoint, not
    just the underlying calculate_score() function in isolation."""
    accra = api_client.post(
        "/situation", json={"location": "Accra Central", "precipitation": 40}
    ).json()
    no_data_district = api_client.post(
        "/situation", json={"location": "Ho", "precipitation": 40}
    ).json()

    assert accra["score"] > no_data_district["score"]
    assert no_data_district["score"] == calculate_score(40)
