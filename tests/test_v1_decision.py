"""Regression tests for GET /v1/districts/{district}/decision
(src/api/v1/decision.py)."""


def test_v1_decision_matches_legacy_post_decision_card(api_client):
    """Both call the exact same get_decision_card() - for the same
    inputs they must produce identical decisions (aside from the
    randomly-generated decision_id/generated_at fields)."""
    legacy = api_client.post(
        "/decision/card", json={"location": "Tamale", "precipitation": 90}
    )
    v1 = api_client.get(
        "/v1/districts/Tamale/decision", params={"precipitation_mm": 90}
    )
    assert legacy.status_code == 200
    assert v1.status_code == 200

    legacy_data = legacy.json()
    v1_data = v1.json()
    for key in ("risk_tier", "score", "action", "priority", "reason", "data_gaps"):
        assert legacy_data[key] == v1_data[key]


def test_v1_decision_unknown_district_404(api_client):
    resp = api_client.get(
        "/v1/districts/Atlantis/decision", params={"precipitation_mm": 50}
    )
    assert resp.status_code == 404


def test_v1_decision_missing_precipitation_422(api_client):
    resp = api_client.get("/v1/districts/Tamale/decision")
    assert resp.status_code == 422
