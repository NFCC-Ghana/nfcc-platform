"""Regression tests for src/hydrology/river_level_intelligence.py and its
wiring into POST /situation and POST /decision/card - the fix for a
previously-undiscovered fabrication bug: river_level_m
(src/hydrology/river_intelligence.py) is entirely
np.random.seed(hash(gauge_id))-fabricated with zero connection to any
real input, but was cited as available=True unconditionally in every
Decision Card built before this fix."""

from src.hydrology.river_level_intelligence import (
    get_river_level_for_district,
    has_river_coverage,
)


def test_has_river_coverage_true_only_for_tamale():
    assert has_river_coverage("Tamale") is True
    for district in ("Accra Central", "Accra West", "Kumasi", "Cape Coast", "Sunyani", "Ho"):
        assert has_river_coverage(district) is False


def test_tamale_has_real_coverage_registered():
    """Tamale is the one tracked district with a real DAHITI target
    (White Volta, id 9087) close enough to be meaningful. Whether the
    live call succeeds depends on DAHITI_API_KEY being set in this
    environment, but it must never fall into the generic "no coverage
    within 80km" reason real for the other 8 districts - Tamale has
    coverage registered even if the key itself isn't configured here."""
    result = get_river_level_for_district("Tamale")
    if not result["available"]:
        assert "65km" not in result["reason"]


def test_other_districts_honestly_unavailable():
    for district in ("Accra Central", "Kumasi", "Cape Coast", "Sunyani", "Ho"):
        result = get_river_level_for_district(district)
        assert result["available"] is False
        assert "65km" in result["reason"]


def test_unknown_district_honestly_unavailable():
    result = get_river_level_for_district("Atlantis")
    assert result["available"] is False


def test_accra_west_has_specific_weija_reason():
    """Accra West's nearest real reservoir (Weija Dam, on the Densu
    River) was checked specifically - too small (5.5M m3) for satellite
    altimetry to resolve at all, a different and more specific reason
    than the generic "nearest target is 65km+ away" given to districts
    with no nearby reservoir at all."""
    result = get_river_level_for_district("Accra West")
    assert result["available"] is False
    assert "Weija" in result["reason"]


def test_situation_includes_river_gauge_field(api_client):
    resp = api_client.post(
        "/situation", json={"location": "Tamale", "precipitation": 60}
    )
    assert resp.status_code == 200
    assert "river_gauge" in resp.json()


def test_situation_river_level_m_none_for_unavailable_districts(api_client):
    """river_level_m used to always be a fabricated number for every
    district - it must now be explicitly None wherever real coverage
    doesn't exist, never silently falling back to a fake value."""
    resp = api_client.post(
        "/situation", json={"location": "Kumasi", "precipitation": 60}
    )
    assert resp.status_code == 200
    assert resp.json()["river_level_m"] is None


def test_situation_river_level_m_is_real_number_for_tamale_when_available(api_client):
    resp = api_client.post(
        "/situation", json={"location": "Tamale", "precipitation": 60}
    )
    data = resp.json()
    river_gauge = data["river_gauge"]
    if river_gauge["available"]:
        assert data["river_level_m"] == river_gauge["level_above_baseline_m"]
    else:
        assert data["river_level_m"] is None


def test_decision_card_never_claims_river_level_without_real_gauge(api_client):
    """For a district with no real river gauge (everything except
    Tamale), the reason text must never cite a river water level as
    evidence - the old bug cited the fabricated river_level_m
    unconditionally regardless of district."""
    resp = api_client.post(
        "/decision/card", json={"location": "Kumasi", "precipitation": 90}
    )
    assert resp.status_code == 200
    card = resp.json()
    river_evidence = next(
        e for e in card["evidence"] if e["field"] == "river_water_level"
    )
    assert river_evidence["available"] is False
    assert "water surface elevation" not in card["reason"].lower()


def test_decision_card_no_longer_has_fabricated_river_level_m_field(api_client):
    """The old evidence field name (river_level_m, sourced from the
    fabricated unified_intelligence value) must not appear in the
    evidence array anymore - it's been replaced by river_water_level,
    sourced from real DAHITI data or an honest unavailability."""
    resp = api_client.post(
        "/decision/card", json={"location": "Tamale", "precipitation": 90}
    )
    card = resp.json()
    fields = [e["field"] for e in card["evidence"]]
    assert "river_level_m" not in fields
    assert "river_water_level" in fields
