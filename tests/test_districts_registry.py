"""Regression tests for src/exposure/districts.py - the canonical
district registry behind GET /v1/districts.

This registry exists specifically because district facts (name/lat/lon/
population/communities) were previously scattered across four
independently-maintained files. These tests actively cross-check the
registry against those other real sources rather than trusting it to
stay in sync by convention - the same "no drift" discipline this
platform applies to risk tiers, lead time tables, and CAP vocabulary
elsewhere.
"""

from src.exposure.districts import TRACKED_DISTRICT_NAMES, get_district, list_districts
from src.exposure.community_names import DISTRICT_COMMUNITIES
from src.hydrology.weather_forecast import weather_forecast


def test_registry_matches_weather_forecast_coordinates():
    """src/hydrology/weather_forecast.py's district_coords is the
    coordinate set actually used to fetch real Open-Meteo forecasts -
    if this registry's lat/lon ever drifted from it, GET /v1/districts
    would show a location the platform doesn't actually forecast for."""
    for name in TRACKED_DISTRICT_NAMES:
        district = get_district(name)
        coords = weather_forecast.district_coords[name]
        assert district.lat == coords["lat"], name
        assert district.lon == coords["lon"], name


def test_registry_matches_community_names():
    """src/exposure/community_names.py is what /situation and
    /decision/card actually use for geotargeting - the registry's
    communities must be the exact same list, not a re-typed copy that
    could diverge."""
    for name in TRACKED_DISTRICT_NAMES:
        district = get_district(name)
        assert district.communities == DISTRICT_COMMUNITIES[name]


def test_registry_excludes_sekondi_takoradi():
    """impact_estimator.py's _load_district_data() has a 10th entry,
    "Sekondi-Takoradi", not present in any other real tracked-district
    list - the registry must not surface it as a tracked district."""
    assert "Sekondi-Takoradi" not in TRACKED_DISTRICT_NAMES
    assert get_district("Sekondi-Takoradi") is None


def test_unknown_district_returns_none():
    assert get_district("Nonexistent District") is None


def test_list_districts_returns_all_nine_in_canonical_order():
    names = [d.name for d in list_districts()]
    assert names == [
        "Accra Central",
        "Accra West",
        "Accra East",
        "Tema",
        "Kumasi",
        "Tamale",
        "Cape Coast",
        "Ho",
        "Sunyani",
    ]


def test_v1_districts_endpoint(api_client):
    resp = api_client.get("/v1/districts")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 9
    names = {d["name"] for d in data}
    assert "Sekondi-Takoradi" not in names
    assert "Tamale" in names


def test_v1_districts_by_name_endpoint(api_client):
    resp = api_client.get("/v1/districts/Tamale")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Tamale"
    assert "Tamale Central" in data["communities"]


def test_v1_districts_unknown_district_404(api_client):
    resp = api_client.get("/v1/districts/Atlantis")
    assert resp.status_code == 404
