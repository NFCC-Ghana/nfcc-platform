"""Regression tests for POST /decision/card (src/api/routes/decision_card.py).

These specifically guard against the fabrication bug this endpoint (and
the AI Decision Center it's meant to replace) was built to eliminate:
hackathon/app/pages/dashboard.py's render_ai_decision_center() used to
assert "Multiple citizen reports verified" for every EXTREME/CRITICAL
alert even when verified_reports was 0, and "Roads becoming inaccessible"
with no data source for it anywhere. A test that only checks the schema
shape would not have caught either bug - these assert on the actual
claim text.
"""


def test_decision_card_schema(api_client):
    resp = api_client.post(
        "/decision/card", json={"location": "Accra Central", "precipitation": 60}
    )
    assert resp.status_code == 200
    card = resp.json()
    for key in (
        "decision_id",
        "generated_at",
        "risk_tier",
        "score",
        "location",
        "action",
        "priority",
        "confidence",
        "evidence",
        "expected_impact",
        "reason",
        "data_gaps",
        "status",
    ):
        assert key in card
    assert card["status"] == "DRAFT"
    assert isinstance(card["evidence"], list) and len(card["evidence"]) > 0
    for item in card["evidence"]:
        assert "field" in item and "available" in item and "source" in item


def test_decision_card_never_claims_verified_reports_when_zero(api_client):
    """No community reports exist for a fresh test district/scenario, so
    verified_reports is 0 - the reason text must say so honestly, never
    claim reports were verified."""
    resp = api_client.post(
        "/decision/card", json={"location": "Kumasi", "precipitation": 90}
    )
    assert resp.status_code == 200
    card = resp.json()
    verified_evidence = next(
        e for e in card["evidence"] if e["field"] == "verified_reports"
    )
    if verified_evidence["value"] == 0:
        assert "verified" not in card["reason"].lower() or "no verified" in card[
            "reason"
        ].lower()
        assert "reports verified" not in card["reason"].lower()


def test_decision_card_confidence_never_exceeds_95(api_client):
    """Confidence must never claim near-certainty (100%) from a single
    rainfall-driven score - see decision_card.py's ConfidenceBlock.method
    for why overconfidence here is treated as a real risk (Google Flood
    Hub's documented >90% false positive/negative rate once independently
    reassessed in data-sparse regions)."""
    resp = api_client.post(
        "/decision/card", json={"location": "Kumasi", "precipitation": 150}
    )
    assert resp.status_code == 200
    card = resp.json()
    assert card["confidence"]["value"] <= 95


def test_decision_card_bagre_data_gap_for_tamale(api_client):
    """Tamale is downstream of Bagre Dam (Burkina Faso) - a documented,
    unresolved cross-border notification gap - this must always appear
    as an explicit data gap, never silently omitted."""
    resp = api_client.post(
        "/decision/card", json={"location": "Tamale", "precipitation": 90}
    )
    assert resp.status_code == 200
    card = resp.json()
    assert any("Bagre" in gap for gap in card["data_gaps"])


def test_decision_card_no_dam_gap_for_unexposed_district(api_client):
    """Accra Central isn't downstream of any dam this platform tracks -
    data_gaps must not mention a dam here."""
    resp = api_client.post(
        "/decision/card", json={"location": "Accra Central", "precipitation": 90}
    )
    assert resp.status_code == 200
    card = resp.json()
    assert card["data_gaps"] == [] or not any(
        "Dam" in gap or "dam" in gap for gap in card["data_gaps"]
    )


def test_decision_card_satellite_claim_requires_real_confirmation(api_client):
    """A satellite evidence item with available=False must never be used
    to justify a 'satellite confirms' claim in the reason text, even if
    it happens to carry a truthy value (e.g. simulated data saying
    water_detected=True) - available is the guard, not the raw value."""
    resp = api_client.post(
        "/decision/card", json={"location": "Sunyani", "precipitation": 90}
    )
    assert resp.status_code == 200
    card = resp.json()
    sat_evidence = next(
        e for e in card["evidence"] if e["field"] == "satellite_water_detected"
    )
    if not sat_evidence["available"]:
        assert "satellite" not in card["reason"].lower()
