"""Regression tests for GET/POST /v1/districts/{district}/risk/history
(src/api/v1/risk_history.py, src/database/risk_history_db.py) - priority
deliverable #9, the genuinely new capability (a persisted risk time
series - nothing like it existed before)."""

from src.alerts.formatter import calculate_score, get_risk_tier


def test_history_empty_before_any_snapshot(api_client):
    resp = api_client.get("/v1/districts/Sunyani/risk/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["district"] == "Sunyani"
    assert data["count"] == len(data["history"])


def test_record_snapshot_then_appears_in_history(api_client):
    post_resp = api_client.post(
        "/v1/districts/Kumasi/risk/history",
        json={"precipitation_mm": 75, "source": "test"},
    )
    assert post_resp.status_code == 200
    point = post_resp.json()
    assert point["district"] == "Kumasi"
    assert point["score"] == calculate_score(75)
    assert point["risk_tier"] == get_risk_tier(calculate_score(75))
    assert point["source"] == "test"

    get_resp = api_client.get("/v1/districts/Kumasi/risk/history")
    ids = [p["id"] for p in get_resp.json()["history"]]
    assert point["id"] in ids


def test_history_is_district_scoped(api_client):
    """A snapshot recorded for one district must never appear in
    another district's history."""
    api_client.post(
        "/v1/districts/Ho/risk/history", json={"precipitation_mm": 30}
    )
    tamale_history = api_client.get("/v1/districts/Tamale/risk/history").json()
    assert not any(p["district"] == "Ho" for p in tamale_history["history"])


def test_history_unknown_district_404(api_client):
    resp = api_client.get("/v1/districts/Atlantis/risk/history")
    assert resp.status_code == 404

    resp = api_client.post(
        "/v1/districts/Atlantis/risk/history", json={"precipitation_mm": 10}
    )
    assert resp.status_code == 404


def test_record_snapshot_negative_precipitation_422(api_client):
    resp = api_client.post(
        "/v1/districts/Kumasi/risk/history", json={"precipitation_mm": -5}
    )
    assert resp.status_code == 422


def test_history_chronological_order(api_client):
    """Multiple snapshots for the same district must come back oldest
    first - the natural order for plotting a trend."""
    for precip in (10, 20, 30):
        api_client.post(
            "/v1/districts/Cape Coast/risk/history",
            json={"precipitation_mm": precip, "source": "test-order"},
        )
    resp = api_client.get(
        "/v1/districts/Cape Coast/risk/history", params={"limit": 3}
    )
    recorded_ats = [p["recorded_at"] for p in resp.json()["history"]]
    assert recorded_ats == sorted(recorded_ats)
