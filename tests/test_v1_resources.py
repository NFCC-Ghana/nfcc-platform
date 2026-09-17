"""Regression tests for GET /v1/districts/{district}/resources
(src/api/v1/resources.py)."""


def test_resources_schema(api_client):
    resp = api_client.get(
        "/v1/districts/Tamale/resources", params={"precipitation_mm": 60}
    )
    assert resp.status_code == 200
    data = resp.json()
    for key in (
        "district",
        "shelters",
        "dams",
        "schools_exposed",
        "hospitals_exposed",
        "markets_exposed",
        "power_substations_affected",
    ):
        assert key in data
    assert isinstance(data["shelters"], list)


def test_resources_bagre_appears_for_tamale(api_client):
    resp = api_client.get(
        "/v1/districts/Tamale/resources", params={"precipitation_mm": 60}
    )
    dams = resp.json()["dams"]
    assert any(d["dam"] == "Bagre" and d["available"] is False for d in dams)


def test_resources_no_dams_for_unexposed_district(api_client):
    resp = api_client.get(
        "/v1/districts/Accra Central/resources", params={"precipitation_mm": 60}
    )
    assert resp.json()["dams"] == []


def test_resources_unknown_district_404(api_client):
    resp = api_client.get(
        "/v1/districts/Atlantis/resources", params={"precipitation_mm": 50}
    )
    assert resp.status_code == 404


def test_resources_does_not_invent_emergency_inventory(api_client):
    """No real inventory system exists for rescue boats/ambulances/
    pumps/rescue teams - the response must not claim to have any."""
    resp = api_client.get(
        "/v1/districts/Tamale/resources", params={"precipitation_mm": 60}
    )
    data = resp.json()
    for fake_field in ("rescue_boats", "ambulances", "pumps", "rescue_teams"):
        assert fake_field not in data
