"""Regression tests for /v1/alerts/... (src/api/v1/alerts.py).

These specifically confirm the v1 layer is a thin pass-through with no
duplicated logic: an action taken through /v1/alerts must be visible
through the original /alerts routes (same underlying DB row), and vice
versa - they are two contracts over one real state, not two states.
"""


def test_v1_assess_then_visible_via_legacy_pending(api_client):
    resp = api_client.post(
        "/v1/alerts/assess", json={"location": "Kumasi", "precipitation": 90}
    )
    assert resp.status_code == 200
    assert resp.json()["queued"] is True
    alert_id = resp.json()["id"]

    legacy = api_client.get("/alerts/pending")
    assert any(a["id"] == alert_id for a in legacy.json()["alerts"])


def test_v1_exercise_creates_real_exercise_alert(api_client):
    resp = api_client.post(
        "/v1/alerts/exercise", json={"location": "Ho", "risk_tier": "HIGH"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["cap_status"] == "Exercise"
    assert "DRILL" in data["message"]


def test_v1_pending_list_schema(api_client):
    api_client.post(
        "/v1/alerts/exercise", json={"location": "Sunyani", "risk_tier": "MODERATE"}
    )
    resp = api_client.get("/v1/alerts/pending")
    assert resp.status_code == 200
    data = resp.json()
    assert "count" in data and "alerts" in data
    assert isinstance(data["alerts"], list)
    if data["alerts"]:
        alert = data["alerts"][0]
        for key in ("id", "location", "score", "risk_tier", "status", "created_at"):
            assert key in alert


def test_v1_approve_exercise_never_sends_real_alert(api_client):
    """Approving through /v1/alerts must go through the exact same
    exercise-mode safety branch as the legacy route - it must never
    reach AlertEngine."""
    created = api_client.post(
        "/v1/alerts/exercise", json={"location": "Cape Coast", "risk_tier": "EXTREME"}
    )
    alert_id = created.json()["id"]

    resp = api_client.post(
        f"/v1/alerts/pending/{alert_id}/approve", json={"reviewed_by": "test"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    assert data["send_result"]["alert_sent"] is False
    assert data["send_result"]["simulated"] is True


def test_v1_cap_xml_matches_legacy_route(api_client):
    created = api_client.post(
        "/v1/alerts/exercise", json={"location": "Tamale", "risk_tier": "HIGH"}
    )
    alert_id = created.json()["id"]

    v1_xml = api_client.get(f"/v1/alerts/pending/{alert_id}/cap.xml")
    legacy_xml = api_client.get(f"/alerts/pending/{alert_id}/cap.xml")
    assert v1_xml.status_code == 200
    assert v1_xml.text == legacy_xml.text


def test_v1_assess_basis_defaults_to_forecast(api_client):
    """basis distinguishes which real rainfall signal an assessment used
    (src/models/rare_event_verification.py found antecedent accumulation
    has meaningfully better rare-event skill than forecast/same-day
    scoring, so the automated pipeline now runs both independently) -
    existing callers that don't set it must keep working exactly as
    before, defaulting to the original forecast-based behavior."""
    resp = api_client.post(
        "/v1/alerts/assess", json={"location": "Kumasi", "precipitation": 90}
    )
    assert resp.status_code == 200
    assert resp.json()["basis"] == "forecast_next_24h"


def test_v1_assess_basis_passes_through_when_set(api_client):
    resp = api_client.post(
        "/v1/alerts/assess",
        json={
            "location": "Kumasi",
            "precipitation": 90,
            "basis": "antecedent_3d_accumulation",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["basis"] == "antecedent_3d_accumulation"

    pending = api_client.get("/v1/alerts/pending")
    row = next(a for a in pending.json()["alerts"] if a["id"] == data["id"])
    assert row["basis"] == "antecedent_3d_accumulation"


def test_v1_history_and_stats_schema(api_client):
    resp = api_client.get("/v1/alerts/history")
    assert resp.status_code == 200
    assert "data" in resp.json()

    resp = api_client.get("/v1/alerts/stats")
    assert resp.status_code == 200
    assert "by_risk_tier" in resp.json()
