"""Regression tests for src/database/prediction_ledger_db.py - the real
ledger preserving what happened, what was predicted, why, and (once
known) what eventually happened. Uses the same shared real test
database every other DB test in this suite uses; district names are
namespaced per test to avoid cross-test collisions."""

from src.database.prediction_ledger_db import (
    get_prediction,
    get_predictions,
    init_prediction_ledger_table,
    record_outcome,
    save_prediction,
)

init_prediction_ledger_table()


def test_save_and_retrieve_prediction():
    result = save_prediction(
        district="_TestLedger_Basic",
        evidence_snapshot={"rainfall_mm": 40.0, "river_gauge": {"available": True}},
        risk_score=60.0,
        risk_tier="HIGH",
        fused_risk_score=75.0,
        fused_risk_tier="CRITICAL",
        confidence=68.5,
        reason="Rainfall driving this assessment: 40mm",
        risk_attribution="Risk is driven by the fluvial pathway",
    )
    assert result["id"] is not None

    rows = get_predictions(district="_TestLedger_Basic")
    assert len(rows) == 1
    row = rows[0]
    assert row["risk_tier"] == "HIGH"
    assert row["fused_risk_tier"] == "CRITICAL"
    assert row["evidence_snapshot"]["rainfall_mm"] == 40.0
    assert row["outcome"] is None


def test_outcome_starts_null_and_can_be_recorded():
    result = save_prediction(
        district="_TestLedger_Outcome",
        evidence_snapshot={"rainfall_mm": 10.0},
        risk_score=20.0,
        risk_tier="LOW",
    )
    pred_id = result["id"]

    fresh = get_prediction(pred_id)
    assert fresh["outcome"] is None
    assert fresh["outcome_recorded_at"] is None

    success = record_outcome(pred_id, outcome="no_flood_confirmed", outcome_source="manual_review")
    assert success is True

    updated = get_prediction(pred_id)
    assert updated["outcome"] == "no_flood_confirmed"
    assert updated["outcome_source"] == "manual_review"
    assert updated["outcome_recorded_at"] is not None


def test_record_outcome_returns_false_for_unknown_id():
    assert record_outcome(999_999_999, "flood_confirmed", "manual_review") is False


def test_filter_by_pending_outcome():
    save_prediction(
        district="_TestLedger_Pending", evidence_snapshot={}, risk_score=30.0
    )
    result = save_prediction(
        district="_TestLedger_Pending", evidence_snapshot={}, risk_score=80.0
    )
    record_outcome(result["id"], "flood_confirmed", "news_report")

    pending = get_predictions(district="_TestLedger_Pending", outcome="__pending__")
    assert len(pending) == 1
    assert pending[0]["outcome"] is None


def test_most_recent_first():
    save_prediction(district="_TestLedger_Order", evidence_snapshot={}, risk_score=1.0)
    save_prediction(district="_TestLedger_Order", evidence_snapshot={}, risk_score=2.0)
    rows = get_predictions(district="_TestLedger_Order")
    assert rows[0]["risk_score"] == 2.0
