"""Regression tests for the auth gap fix (src/api/auth.py's
verify_api_key, wired onto state-mutating routes). Every other test in
this suite runs through tests/conftest.py's api_client/test_client
fixtures, which now attach a valid X-API-Key to every request - a
necessary fix so 40+ pre-existing tests didn't start failing, but one
that would silently hide a regression where verify_api_key stopped
being enforced (every test would keep passing whether or not the
dependency was still wired up). These tests use a bare, header-less
TestClient specifically to prove the key is actually required."""

from fastapi.testclient import TestClient

from src.api.auth import api_key_header
from src.api.main import app
from src.config.settings import settings

_HEADER_NAME = api_key_header.model.name


def test_protected_route_rejects_missing_key():
    with TestClient(app) as client:
        resp = client.post("/situation", json={"location": "Tamale", "precipitation": 10})
    assert resp.status_code == 401


def test_protected_route_rejects_wrong_key():
    with TestClient(app) as client:
        resp = client.post(
            "/situation",
            json={"location": "Tamale", "precipitation": 10},
            headers={_HEADER_NAME: "definitely-not-the-real-key"},
        )
    assert resp.status_code == 403


def test_protected_route_accepts_real_key():
    with TestClient(app) as client:
        resp = client.post(
            "/situation",
            json={"location": "Tamale", "precipitation": 10},
            headers={_HEADER_NAME: settings.API_KEY},
        )
    assert resp.status_code == 200


def test_read_only_route_needs_no_key():
    """GET /v1/districts stays open - read-only routes weren't part of
    this fix's scope (except subscriptions' PII-leaking list, covered
    separately)."""
    with TestClient(app) as client:
        resp = client.get("/v1/districts")
    assert resp.status_code == 200


def test_subscriptions_list_rejects_missing_key():
    """The one GET this fix did protect - it leaks every subscriber's
    email/phone/unsubscribe_token, not just computed risk data."""
    with TestClient(app) as client:
        resp = client.get("/subscriptions/")
    assert resp.status_code == 401
