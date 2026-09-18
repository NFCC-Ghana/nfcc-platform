"""Regression tests for GET /v1/districts/{district}/evidence
(src/api/v1/evidence.py)."""


def test_evidence_matches_decision_card_evidence(api_client):
    """The evidence endpoint and POST /decision/card call the exact same
    build_evidence() - for the same inputs, their evidence/reason/
    data_gaps must be identical, proving there's one implementation, not
    two that could drift."""
    params = {"location": "Tamale", "precipitation": 90}

    card_resp = api_client.post("/decision/card", json=params)
    evidence_resp = api_client.get(
        "/v1/districts/Tamale/evidence", params={"precipitation_mm": 90}
    )
    assert card_resp.status_code == 200
    assert evidence_resp.status_code == 200

    card = card_resp.json()
    evidence = evidence_resp.json()
    assert evidence["reason"] == card["reason"]
    assert evidence["data_gaps"] == card["data_gaps"]
    assert evidence["risk_tier"] == card["risk_tier"]
    assert len(evidence["evidence"]) == len(card["evidence"])
    # Same real fusion engine, called with the same inputs -> identical
    # confidence, not two independently-drifting implementations.
    assert evidence["confidence"] == card["confidence"]


def test_evidence_includes_confidence_block(api_client):
    """Previously this endpoint had no confidence field at all, forcing
    a caller who only wanted evidence to also call /decision/card."""
    resp = api_client.get(
        "/v1/districts/Accra%20Central/evidence", params={"precipitation_mm": 60}
    )
    assert resp.status_code == 200
    confidence = resp.json()["confidence"]
    for key in ("value", "basis", "coverage", "agreement", "degraded", "explanation"):
        assert key in confidence


def test_evidence_unknown_district_404(api_client):
    resp = api_client.get(
        "/v1/districts/Atlantis/evidence", params={"precipitation_mm": 50}
    )
    assert resp.status_code == 404


def test_evidence_missing_precipitation_422(api_client):
    resp = api_client.get("/v1/districts/Tamale/evidence")
    assert resp.status_code == 422
