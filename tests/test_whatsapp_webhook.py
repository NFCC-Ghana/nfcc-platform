"""Regression tests for POST /webhooks/whatsapp (src/api/routes/
whatsapp_webhook.py) and GET/POST /v1/community-reports
(src/api/v1/community_reports.py) - the first real intake path for
citizen flood reports, activating previously-unused infrastructure
(src/community/community_memory.py).

Specifically guards against two real bugs caught while building this:
1. Naive substring location matching false-positived "Ho" (a tracked
   district) inside the word "house" - test_no_false_positive_substring_
   match guards the word-boundary fix.
2. community_memory.CommunityMemoryEngine.submit_report() generated
   report_id from a second-precision timestamp with no uniqueness
   guarantee, so two reports in the same second (realistic under
   WhatsApp traffic) raised sqlite3.IntegrityError and, worse, leaked
   the open connection on that exception path and left the database
   locked for the next caller - test_rapid_reports_do_not_collide
   guards the fix (uuid suffix + try/finally connection cleanup).
"""

import pytest
from twilio.request_validator import RequestValidator

from src.community.community_memory import community_memory
from src.config.settings import settings


@pytest.fixture(autouse=True)
def _isolated_reports_db(tmp_path, monkeypatch):
    """Point the community_memory singleton at a throwaway DB file so
    these tests never touch data/community_reports.db."""
    db_path = tmp_path / "test_community_reports.db"
    monkeypatch.setattr(community_memory, "db_path", db_path)
    community_memory._init_db()
    yield


@pytest.fixture(autouse=True)
def _no_twilio_auth_token(monkeypatch):
    """Most tests exercise the parsing/storage logic, not signature
    verification - run them in the documented dev-mode (no
    TWILIO_AUTH_TOKEN configured -> signature check skipped)."""
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", None)


def _post_whatsapp(api_client, body: str, from_number: str = "whatsapp:+233241234567", **extra):
    form = {"From": from_number, "Body": body, "NumMedia": "0", **extra}
    return api_client.post("/webhooks/whatsapp", data=form)


def test_recognized_community_maps_to_correct_district(api_client):
    resp = _post_whatsapp(api_client, "Kaneshie flooding, cars can't pass, about 40cm")
    assert resp.status_code == 200
    assert "Kaneshie" in resp.text
    assert "Accra Central" in resp.text

    reports = api_client.get("/v1/community-reports?limit=10").json()["reports"]
    assert reports[0]["district"] == "Accra Central"
    assert reports[0]["community"] == "Kaneshie"
    assert reports[0]["flood_depth_m"] == pytest.approx(0.40)
    assert reports[0]["report_type"] == "Active Flooding"


def test_no_false_positive_substring_match(api_client):
    """'house' contains 'ho' (a real tracked district) as a substring -
    a naive `if term in text` check wrongly classified this as Ho."""
    resp = _post_whatsapp(api_client, "There is heavy flooding near my house, water is rising fast")
    assert resp.status_code == 200
    assert "couldn't automatically detect" in resp.text

    reports = api_client.get("/v1/community-reports?limit=10").json()["reports"]
    assert reports[0]["district"] == "Unclassified - needs triage"


def test_genuine_short_district_name_still_matches(api_client):
    resp = _post_whatsapp(api_client, "Flooding reported in Ho near the market, about 1.2m deep")
    assert resp.status_code == 200
    reports = api_client.get("/v1/community-reports?limit=10").json()["reports"]
    assert reports[0]["district"] == "Ho"
    assert reports[0]["flood_depth_m"] == pytest.approx(1.2)


def test_rapid_reports_do_not_collide(api_client):
    """Regression test for the report_id collision + connection-leak bug
    found while building this: several reports with the same
    community-name prefix landing in the same second used to raise
    sqlite3.IntegrityError on the 2nd, then sqlite3.OperationalError
    ("database is locked") on the 3rd, because the failed connection
    was never closed."""
    for _ in range(5):
        resp = _post_whatsapp(api_client, "unclassified free text with no place name in it")
        assert resp.status_code == 200
        assert "Sorry, we couldn't save" not in resp.text

    reports = api_client.get("/v1/community-reports?limit=10").json()["reports"]
    assert len({r["report_id"] for r in reports}) == 5


def test_empty_body_prompts_for_content(api_client):
    resp = _post_whatsapp(api_client, "")
    assert resp.status_code == 200
    assert "didn't receive any text" in resp.text


def test_help_keyword_returns_instructions(api_client):
    resp = _post_whatsapp(api_client, "help")
    assert resp.status_code == 200
    assert "NFCC Flood Reporting" in resp.text


def test_photo_attachment_is_stored(api_client):
    resp = _post_whatsapp(
        api_client,
        "Dansoman drainage blocked",
        NumMedia="1",
        MediaUrl0="https://api.twilio.com/fake-media/123",
    )
    assert resp.status_code == 200
    reports = api_client.get("/v1/community-reports?limit=10").json()["reports"]
    assert reports[0]["photo_url"] == "https://api.twilio.com/fake-media/123"


def test_invalid_twilio_signature_rejected(api_client, monkeypatch):
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "test_auth_token_12345")
    resp = api_client.post(
        "/webhooks/whatsapp",
        data={"From": "whatsapp:+233241234567", "Body": "Osu flooding", "NumMedia": "0"},
        headers={"X-Twilio-Signature": "bogus"},
    )
    assert resp.status_code == 403


def test_valid_twilio_signature_accepted(api_client, monkeypatch):
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "test_auth_token_12345")
    form = {"From": "whatsapp:+233241234567", "Body": "Osu flooding, water knee deep", "NumMedia": "0"}
    validator = RequestValidator("test_auth_token_12345")
    signature = validator.compute_signature("https://testserver/webhooks/whatsapp", form)

    resp = api_client.post(
        "/webhooks/whatsapp", data=form, headers={"X-Twilio-Signature": signature}
    )
    assert resp.status_code == 200
    assert "Osu" in resp.text


def test_validate_report_requires_api_key(api_client):
    """api_client attaches a real X-API-Key by default (conftest.py) so
    most tests don't have to think about auth - this one explicitly
    drops it to prove the route actually enforces verify_api_key."""
    _post_whatsapp(api_client, "Kaneshie flooding again today")
    report_id = api_client.get("/v1/community-reports?limit=1").json()["reports"][0]["report_id"]

    unauthenticated = api_client.post(
        f"/v1/community-reports/{report_id}/validate",
        json={"confidence": 0.9},
        headers={"X-API-Key": ""},
    )
    assert unauthenticated.status_code in (401, 403)


def test_validate_report_marks_validated(api_client):
    _post_whatsapp(api_client, "Kaneshie flooding again today")
    report_id = api_client.get("/v1/community-reports?limit=1").json()["reports"][0]["report_id"]

    resp = api_client.post(
        f"/v1/community-reports/{report_id}/validate",
        json={"confidence": 0.9},
        headers={"X-API-Key": settings.API_KEY},
    )
    assert resp.status_code == 200

    reports = api_client.get("/v1/community-reports?validated_only=true").json()["reports"]
    assert any(r["report_id"] == report_id for r in reports)


def test_validate_unknown_report_id_404s(api_client):
    resp = api_client.post(
        "/v1/community-reports/RPT_does_not_exist/validate",
        json={"confidence": 0.9},
        headers={"X-API-Key": settings.API_KEY},
    )
    assert resp.status_code == 404
