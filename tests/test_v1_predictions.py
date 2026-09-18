"""Regression tests for /v1/predictions (src/api/v1/predictions.py) -
the prediction ledger: what happened, predicted, why, and (eventually)
what happened."""

from unittest.mock import patch


def test_unknown_district_404(api_client):
    resp = api_client.post(
        "/v1/predictions/record",
        json={"district": "Atlantis", "evidence_snapshot": {}},
    )
    assert resp.status_code == 404


def test_record_then_list_prediction(api_client):
    resp = api_client.post(
        "/v1/predictions/record",
        json={
            "district": "Kumasi",
            "evidence_snapshot": {"rainfall_mm": 55.0},
            "risk_score": 62.0,
            "risk_tier": "HIGH",
            "fused_risk_score": 62.0,
            "fused_risk_tier": "HIGH",
            "confidence": 74.0,
            "reason": "Rainfall driving this assessment: 55mm",
            "risk_attribution": "Risk is driven by the pluvial pathway",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["district"] == "Kumasi"
    assert data["outcome"] is None
    pred_id = data["id"]

    listed = api_client.get("/v1/predictions", params={"district": "Kumasi"})
    assert listed.status_code == 200
    assert listed.json()["count"] >= 1

    fetched = api_client.get(f"/v1/predictions/{pred_id}")
    assert fetched.status_code == 200
    assert fetched.json()["evidence_snapshot"]["rainfall_mm"] == 55.0


def test_outcome_lifecycle(api_client):
    created = api_client.post(
        "/v1/predictions/record",
        json={"district": "Sunyani", "evidence_snapshot": {}, "risk_score": 10.0},
    )
    pred_id = created.json()["id"]

    resp = api_client.post(
        f"/v1/predictions/{pred_id}/outcome",
        json={"outcome": "no_flood_confirmed", "outcome_source": "manual_review"},
    )
    assert resp.status_code == 200
    assert resp.json()["outcome"] == "no_flood_confirmed"
    assert resp.json()["outcome_recorded_at"] is not None


def test_outcome_unknown_prediction_404(api_client):
    resp = api_client.post(
        "/v1/predictions/999999999/outcome",
        json={"outcome": "flood_confirmed", "outcome_source": "manual_review"},
    )
    assert resp.status_code == 404


def test_pending_outcome_filter(api_client):
    pending_created = api_client.post(
        "/v1/predictions/record",
        json={"district": "Cape Coast", "evidence_snapshot": {}, "risk_score": 5.0},
    )
    resolved_created = api_client.post(
        "/v1/predictions/record",
        json={"district": "Cape Coast", "evidence_snapshot": {}, "risk_score": 90.0},
    )
    api_client.post(
        f"/v1/predictions/{resolved_created.json()['id']}/outcome",
        json={"outcome": "flood_confirmed", "outcome_source": "news_report"},
    )

    resp = api_client.get(
        "/v1/predictions", params={"district": "Cape Coast", "outcome": "__pending__"}
    )
    ids = [p["id"] for p in resp.json()["predictions"]]
    assert pending_created.json()["id"] in ids
    assert resolved_created.json()["id"] not in ids


def test_auto_verify_records_real_outcome(api_client):
    created = api_client.post(
        "/v1/predictions/record",
        json={"district": "Tamale", "evidence_snapshot": {}, "risk_score": 40.0},
    )
    pred_id = created.json()["id"]

    with patch(
        "src.api.v1.predictions.verify_outcome",
        return_value={
            "outcome": "flood_confirmed",
            "outcome_source": "ReliefWeb",
            "confirmations": ["ReliefWeb"],
            "checks": {},
        },
    ):
        resp = api_client.post(f"/v1/predictions/{pred_id}/auto-verify")

    assert resp.status_code == 200
    data = resp.json()
    assert data["verification"]["outcome"] == "flood_confirmed"
    assert data["prediction"]["outcome"] == "flood_confirmed"
    assert data["prediction"]["outcome_source"] == "ReliefWeb"


def test_auto_verify_unknown_prediction_404(api_client):
    resp = api_client.post("/v1/predictions/999999999/auto-verify")
    assert resp.status_code == 404
