"""Regression tests for the approval-tier key (src/api/auth.py's
enforce_approval_key) - a security-audit follow-up to the single-shared-
API-key model: anyone holding the one general key, used for every read
and write on this platform, could also approve/dismiss/cancel a REAL
evacuation alert. ALERT_APPROVAL_KEY is optional and strictly additive;
these tests cover both states (unset = today's behavior, set = the
stronger requirement) and confirm an exercise alert never needs it,
since the stakeholder demo's Approve/Dismiss buttons use these same
endpoints without provisioning a second secret."""

from fastapi.testclient import TestClient

from src.api.auth import api_key_header, approval_key_header
from src.api.main import app
from src.config.settings import settings

_API_HEADER = api_key_header.model.name
_APPROVAL_HEADER = approval_key_header.model.name


def _api_headers(extra: dict = None) -> dict:
    headers = {_API_HEADER: settings.API_KEY}
    if extra:
        headers.update(extra)
    return headers


def _queue_real_alert(client: TestClient, location: str = "Tamale") -> int:
    """A real (non-exercise) MODERATE+ pending alert, via score_override
    so this doesn't depend on precipitation-curve math staying the same."""
    resp = client.post(
        "/alerts/assess",
        json={"location": location, "precipitation": 0, "score_override": 60},
        headers=_api_headers(),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["queued"] is True
    assert body["cap_status"] != "Exercise"
    return body["id"]


def _queue_exercise_alert(client: TestClient, location: str = "Tamale") -> int:
    resp = client.post(
        "/alerts/exercise",
        json={"location": location, "risk_tier": "HIGH"},
        headers=_api_headers(),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["cap_status"] == "Exercise"
    return body["id"]


def test_approval_key_unset_real_alert_approves_with_just_api_key():
    """Default state (every environment today): ALERT_APPROVAL_KEY is
    unset, so the regular API key alone remains sufficient - this must
    never regress, since nothing currently provisions the second key."""
    assert settings.ALERT_APPROVAL_KEY is None
    with TestClient(app) as client:
        alert_id = _queue_real_alert(client)
        resp = client.post(
            f"/alerts/pending/{alert_id}/approve",
            json={"reviewed_by": "test-reviewer"},
            headers=_api_headers(),
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


def test_approval_key_required_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "ALERT_APPROVAL_KEY", "super-secret-approval-key")
    with TestClient(app) as client:
        alert_id = _queue_real_alert(client)

        # Missing approval key -> 401, even with a valid regular API key.
        resp = client.post(
            f"/alerts/pending/{alert_id}/approve",
            json={"reviewed_by": "test-reviewer"},
            headers=_api_headers(),
        )
        assert resp.status_code == 401

        # Wrong approval key -> 403.
        resp = client.post(
            f"/alerts/pending/{alert_id}/approve",
            json={"reviewed_by": "test-reviewer"},
            headers=_api_headers({_APPROVAL_HEADER: "wrong-key"}),
        )
        assert resp.status_code == 403

        # Correct approval key -> succeeds.
        resp = client.post(
            f"/alerts/pending/{alert_id}/approve",
            json={"reviewed_by": "test-reviewer"},
            headers=_api_headers({_APPROVAL_HEADER: "super-secret-approval-key"}),
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


def test_approval_key_not_required_for_exercise_alert(monkeypatch):
    """The stakeholder demo approves/dismisses exercise alerts through
    these same endpoints without ever sending an approval key - this
    must keep working even when ALERT_APPROVAL_KEY is configured, since
    an exercise alert can never send a real message by any other path
    (see approve_pending_alert's own exercise branch)."""
    monkeypatch.setattr(settings, "ALERT_APPROVAL_KEY", "super-secret-approval-key")
    with TestClient(app) as client:
        alert_id = _queue_exercise_alert(client)
        resp = client.post(
            f"/alerts/pending/{alert_id}/approve",
            json={"reviewed_by": "stakeholder-demo"},
            headers=_api_headers(),
        )
    assert resp.status_code == 200
    assert resp.json()["send_result"]["simulated"] is True


def test_approval_key_required_for_dismiss_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "ALERT_APPROVAL_KEY", "super-secret-approval-key")
    with TestClient(app) as client:
        alert_id = _queue_real_alert(client)
        resp = client.post(
            f"/alerts/pending/{alert_id}/dismiss",
            json={"reviewed_by": "test-reviewer"},
            headers=_api_headers(),
        )
        assert resp.status_code == 401

        alert_id_2 = _queue_real_alert(client)
        resp = client.post(
            f"/alerts/pending/{alert_id_2}/dismiss",
            json={"reviewed_by": "test-reviewer"},
            headers=_api_headers({_APPROVAL_HEADER: "super-secret-approval-key"}),
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "dismissed"


def test_exercise_dismiss_never_requires_approval_key(monkeypatch):
    monkeypatch.setattr(settings, "ALERT_APPROVAL_KEY", "super-secret-approval-key")
    with TestClient(app) as client:
        alert_id = _queue_exercise_alert(client)
        resp = client.post(
            f"/alerts/pending/{alert_id}/dismiss",
            json={"reviewed_by": "stakeholder-demo"},
            headers=_api_headers(),
        )
    assert resp.status_code == 200


def test_approval_key_required_for_cancel_when_configured(monkeypatch):
    """cancel retracts an already-approved real alert - queue, approve
    (with the approval key, since it's configured), then confirm cancel
    also demands it."""
    monkeypatch.setattr(settings, "ALERT_APPROVAL_KEY", "super-secret-approval-key")
    with TestClient(app) as client:
        alert_id = _queue_real_alert(client)
        approve_resp = client.post(
            f"/alerts/pending/{alert_id}/approve",
            json={"reviewed_by": "test-reviewer"},
            headers=_api_headers({_APPROVAL_HEADER: "super-secret-approval-key"}),
        )
        assert approve_resp.status_code == 200

        # Missing approval key on cancel -> 401.
        resp = client.post(
            f"/alerts/pending/{alert_id}/cancel",
            json={"reviewed_by": "test-reviewer", "reason": "test retraction"},
            headers=_api_headers(),
        )
        assert resp.status_code == 401

        # Correct approval key -> succeeds.
        resp = client.post(
            f"/alerts/pending/{alert_id}/cancel",
            json={"reviewed_by": "test-reviewer", "reason": "test retraction"},
            headers=_api_headers({_APPROVAL_HEADER: "super-secret-approval-key"}),
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"
