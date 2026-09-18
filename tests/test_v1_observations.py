"""Regression tests for GET/POST /v1/districts/{district}/observations
(src/api/v1/observations.py)."""


def test_unknown_district_404(api_client):
    resp = api_client.get("/v1/districts/Atlantis/observations")
    assert resp.status_code == 404


def test_record_then_retrieve_observation(api_client):
    resp = api_client.post(
        "/v1/districts/Tema/observations",
        json={
            "source": "dam_akosombo",
            "value": 84.2,
            "unit": "m",
            "quality_flag": "pass",
            "observation_date": "2026-09-01T00:00:00",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["district"] == "Tema"

    listed = api_client.get("/v1/districts/Tema/observations", params={"source": "dam_akosombo"})
    assert listed.status_code == 200
    data = listed.json()
    assert data["count"] >= 1
    assert any(o["value"] == 84.2 for o in data["observations"])


def test_missing_reading_recorded_honestly(api_client):
    resp = api_client.post(
        "/v1/districts/Ho/observations",
        json={"source": "dam_kompienga", "value": None, "unit": "risk_0_100", "quality_flag": "missing"},
    )
    assert resp.status_code == 200
    assert resp.json()["value"] is None
    assert resp.json()["quality_flag"] == "missing"
