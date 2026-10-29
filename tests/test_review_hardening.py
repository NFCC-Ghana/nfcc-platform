"""Regression tests for the 2026-10-29 review fixes:

- POST /score and /score/batch are pure scoring - they must never reach
  AlertEngine.process(), since they're unauthenticated and used to let
  anyone trigger a real WhatsApp/Telegram broadcast.
- Approve/cancel/dismiss claim their status transition atomically, so a
  double-click (possibly across uvicorn workers) can't send a real alert
  twice, and a send that raises hands the alert back for retry.
- Inbound webhooks fail closed in production when their verifying
  secret is missing.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from src.alerts.engine import AlertEngine
from src.api.main import app
from src.config.settings import settings
from src.database.alert_db import get_pending_alert, transition_pending_alert_status
from tests.test_alert_approval_key import _api_headers, _queue_real_alert


def test_score_never_dispatches_an_alert():
    with patch.object(AlertEngine, "process") as process, TestClient(app) as client:
        resp = client.post(
            "/score", json={"location": "Accra Central", "precipitation": 500}
        )
        batch = client.post(
            "/score/batch",
            json={"requests": [{"location": "Accra Central", "precipitation": 500}]},
        )
    assert resp.status_code == 200
    assert resp.json()["risk_tier"] in ("CRITICAL", "EXTREME")
    assert resp.json()["alert_sent"] is False
    assert batch.status_code == 200
    process.assert_not_called()


def test_score_batch_is_bounded():
    with TestClient(app) as client:
        resp = client.post(
            "/score/batch",
            json={"requests": [{"location": "Accra", "precipitation": 1}] * 101},
        )
    assert resp.status_code == 422


def test_transition_is_compare_and_set():
    with TestClient(app) as client:
        alert_id = _queue_real_alert(client)
    assert transition_pending_alert_status(alert_id, "pending", "dismissed", "a")
    # Second claimant loses - the row is no longer 'pending'.
    assert not transition_pending_alert_status(alert_id, "pending", "approved", "b")
    assert get_pending_alert(alert_id)["status"] == "dismissed"


def test_double_approve_sends_once():
    with TestClient(app) as client:
        alert_id = _queue_real_alert(client)
        with patch.object(
            AlertEngine, "process", return_value={"alert_sent": True}
        ) as process:
            first = client.post(
                f"/v1/alerts/pending/{alert_id}/approve",
                json={"reviewed_by": "reviewer-1"},
                headers=_api_headers(),
            )
            second = client.post(
                f"/v1/alerts/pending/{alert_id}/approve",
                json={"reviewed_by": "reviewer-2"},
                headers=_api_headers(),
            )
    assert first.status_code == 200
    assert second.status_code == 409
    assert process.call_count == 1
    assert get_pending_alert(alert_id)["reviewed_by"] == "reviewer-1"


def test_failed_send_returns_alert_to_queue():
    with TestClient(app, raise_server_exceptions=False) as client:
        alert_id = _queue_real_alert(client)
        with patch.object(AlertEngine, "process", side_effect=RuntimeError("boom")):
            resp = client.post(
                f"/v1/alerts/pending/{alert_id}/approve",
                json={"reviewed_by": "reviewer-1"},
                headers=_api_headers(),
            )
    assert resp.status_code == 500
    assert get_pending_alert(alert_id)["status"] == "pending"


def test_webhooks_fail_closed_in_production_without_secret(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", None)
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", None)
    with TestClient(app) as client:
        tg = client.post("/webhooks/telegram", json={"message": {}})
        wa = client.post("/webhooks/whatsapp", data={"Body": "Alajo flooding"})
    assert tg.status_code == 503
    assert wa.status_code == 503
