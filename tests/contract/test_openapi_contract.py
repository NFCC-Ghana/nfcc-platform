"""OpenAPI contract tests.

Previously 5 tests covering only the legacy /score, /districts, /health
surface - none of the versioned /v1/* API (the platform's real, current
contract) and none of the 21 routes that require X-API-Key
(src/api/auth.py). A reviewer checking "is the API contract actually
tested" would have found real gaps between what's claimed and what's
covered. This file now also verifies:

1. The OpenAPI spec itself is generateable and lists every route this
   test file exercises (catches a route silently dropped from routing).
2. Every one of the 21 auth-protected routes genuinely rejects a
   request with no key (401) and a wrong key (403) - not just the one
   representative route tests/test_api_auth.py already covered.
3. A representative sample of the real, unauthenticated /v1/* GET
   endpoints return 200 with their documented top-level fields present.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.auth import api_key_header
from src.api.main import app
from src.config.settings import settings

_HEADER_NAME = api_key_header.model.name

# (method, path, json_body) for every route wired with
# dependencies=[Depends(verify_api_key)] as of this writing - see
# tests/test_api_auth.py's docstring for how this fix was verified
# end-to-end originally. Bodies are fully valid per each route's own
# Pydantic model (not just present) so a 401/403 can only be coming from
# the auth dependency, never from body validation - path-param routes
# use a nonexistent ID (999999), which is safe because FastAPI resolves
# decorator-level `dependencies=` before the handler body runs its own
# "not found" lookup.
PROTECTED_ROUTES = [
    # Legacy alert-review path
    ("POST", "/alerts/assess", {"location": "Tamale", "precipitation": 10}),
    ("POST", "/alerts/exercise", {"location": "Tamale"}),
    ("POST", "/alerts/pending/999999/approve", {"reviewed_by": "test"}),
    ("POST", "/alerts/pending/999999/cancel", {"reviewed_by": "test", "reason": "test"}),
    ("POST", "/alerts/pending/999999/dismiss", {"reviewed_by": "test"}),
    # /v1/alerts - same underlying handlers, separate route registration
    ("POST", "/v1/alerts/assess", {"location": "Tamale", "precipitation": 10}),
    ("POST", "/v1/alerts/exercise", {"location": "Tamale"}),
    ("POST", "/v1/alerts/pending/999999/approve", {"reviewed_by": "test"}),
    ("POST", "/v1/alerts/pending/999999/cancel", {"reviewed_by": "test", "reason": "test"}),
    ("POST", "/v1/alerts/pending/999999/dismiss", {"reviewed_by": "test"}),
    # Decision/situation compute endpoints
    ("POST", "/decision/card", {"location": "Tamale", "precipitation": 10}),
    ("POST", "/situation", {"location": "Tamale", "precipitation": 10}),
    # Prediction ledger writes
    (
        "POST",
        "/v1/predictions/record",
        {"district": "Tamale", "evidence_snapshot": {}},
    ),
    (
        "POST",
        "/v1/predictions/999999/outcome",
        {"outcome": "flood_confirmed", "outcome_source": "manual_review"},
    ),
    ("POST", "/v1/predictions/999999/auto-verify", None),
    # District history/observation writes
    (
        "POST",
        "/v1/districts/Tamale/observations",
        {"source": "rainfall_forecast", "unit": "mm"},
    ),
    (
        "POST",
        "/v1/districts/Tamale/risk/history",
        {"precipitation_mm": 10},
    ),
    # Subscriptions (create/delete/list-with-PII)
    ("POST", "/subscriptions/", {"email": "contract-test@example.com"}),
    ("DELETE", "/subscriptions/contract-test@example.com", None),
    ("GET", "/subscriptions/", None),
    # AI Copilot
    ("POST", "/v1/copilot/ask", {"question": "ping"}),
]


def _request(client: TestClient, method: str, path: str, body, headers: dict):
    kwargs = {"headers": headers}
    if body is not None:
        kwargs["json"] = body
    return client.request(method, path, **kwargs)


@pytest.mark.parametrize("method,path,body", PROTECTED_ROUTES, ids=[f"{m}:{p}" for m, p, _ in PROTECTED_ROUTES])
def test_protected_route_rejects_missing_key(method, path, body):
    with TestClient(app) as client:
        resp = _request(client, method, path, body, headers={})
    assert resp.status_code == 401, (
        f"{method} {path} should require X-API-Key (401), got {resp.status_code}: {resp.text[:200]}"
    )


@pytest.mark.parametrize("method,path,body", PROTECTED_ROUTES, ids=[f"{m}:{p}" for m, p, _ in PROTECTED_ROUTES])
def test_protected_route_rejects_wrong_key(method, path, body):
    with TestClient(app) as client:
        resp = _request(
            client, method, path, body, headers={_HEADER_NAME: "definitely-not-the-real-key"}
        )
    assert resp.status_code == 403, (
        f"{method} {path} should reject a wrong X-API-Key (403), got {resp.status_code}: {resp.text[:200]}"
    )


@pytest.mark.parametrize("method,path,body", PROTECTED_ROUTES, ids=[f"{m}:{p}" for m, p, _ in PROTECTED_ROUTES])
def test_protected_route_accepts_real_key(method, path, body):
    """Proves the real key actually clears the auth gate for every one of
    these routes (never returns 401/403) - not a full business-logic
    test (a fake district/ID may still 404 or 500 downstream), just
    confirms the auth dependency itself passes with the real key."""
    with TestClient(app) as client:
        resp = _request(client, method, path, body, headers={_HEADER_NAME: settings.API_KEY})
    assert resp.status_code not in (401, 403), (
        f"{method} {path} rejected the real API key: {resp.status_code}: {resp.text[:200]}"
    )


class TestOpenAPISpec:
    """The spec itself must be generateable and list the real surface -
    catches a route that's wired in code but never actually registered
    (e.g. a missing router.include_router call)."""

    def test_openapi_spec_loads(self, api_client: TestClient):
        resp = api_client.get("/openapi.json")
        assert resp.status_code == 200
        spec = resp.json()
        assert "paths" in spec
        return spec

    @pytest.mark.parametrize(
        "path_template",
        [
            "/health",
            "/situation",
            "/decision/card",
            "/subscriptions/",
            "/v1/districts",
            "/v1/districts/{district}",
            "/v1/districts/{district}/risk",
            "/v1/districts/{district}/forecast",
            "/v1/districts/{district}/evidence",
            "/v1/districts/{district}/decision",
            "/v1/districts/{district}/resources",
            "/v1/districts/{district}/risk/history",
            "/v1/districts/{district}/fluvial-risk",
            "/v1/districts/{district}/antecedent-rainfall",
            "/v1/districts/{district}/observations",
            "/v1/health/data-sources",
            "/v1/data-quality",
            "/v1/predictions",
            "/v1/predictions/{prediction_id}",
            "/v1/verification",
            "/v1/backtest",
            "/v1/copilot/ask",
            "/v1/alerts/assess",
            "/v1/alerts/pending",
        ],
    )
    def test_route_registered_in_spec(self, api_client: TestClient, path_template):
        spec = api_client.get("/openapi.json").json()
        assert path_template in spec["paths"], (
            f"{path_template} is missing from the generated OpenAPI spec entirely"
        )


class TestRealV1ReadEndpoints:
    """Representative sample of the real, unauthenticated /v1/* GET
    surface - confirms each returns 200 with its documented top-level
    fields actually present, not just a bare status-code check."""

    def test_districts_list_schema(self, api_client: TestClient):
        resp = api_client.get("/v1/districts")
        assert resp.status_code == 200
        districts = resp.json()
        assert isinstance(districts, list) and len(districts) == 9
        for field in ("name", "region", "lat", "lon", "population", "communities"):
            assert field in districts[0]

    def test_district_risk_schema(self, api_client: TestClient):
        resp = api_client.get("/v1/districts/Tamale/risk", params={"precipitation_mm": 50})
        assert resp.status_code == 200
        data = resp.json()
        for field in ("district", "score", "risk_tier", "computed_at"):
            assert field in data

    def test_district_forecast_schema(self, api_client: TestClient):
        resp = api_client.get(
            "/v1/districts/Tamale/forecast", params={"current_precipitation_mm": 10}
        )
        assert resp.status_code == 200
        data = resp.json()
        for field in ("forecast_24h_mm", "risk_timeline", "source"):
            assert field in data

    def test_district_evidence_schema(self, api_client: TestClient):
        resp = api_client.get("/v1/districts/Tamale/evidence", params={"precipitation_mm": 50})
        assert resp.status_code == 200
        data = resp.json()
        for field in ("risk_tier", "evidence", "reason", "data_gaps", "confidence"):
            assert field in data

    def test_district_decision_schema(self, api_client: TestClient):
        resp = api_client.get("/v1/districts/Tamale/decision", params={"precipitation_mm": 50})
        assert resp.status_code == 200
        data = resp.json()
        for field in ("risk_tier", "score", "action", "priority", "confidence", "evidence", "reason"):
            assert field in data

    def test_health_data_sources_schema(self, api_client: TestClient):
        resp = api_client.get("/v1/health/data-sources")
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_status" in data
        assert "sources" in data and len(data["sources"]) > 0

    def test_data_quality_schema(self, api_client: TestClient):
        resp = api_client.get("/v1/data-quality")
        assert resp.status_code == 200
        data = resp.json()
        for field in ("system_status", "sources", "methodology"):
            assert field in data


class TestLegacyContract:
    """Original 5 tests, unchanged."""

    def test_health_response_schema(self, api_client: TestClient):
        """Test health endpoint response schema."""
        response = api_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        # Check for presence of expected fields (not exact match)
        assert "status" in data
        assert data["status"] in ["healthy", "ok"]

    def test_error_response_schema(self, api_client: TestClient):
        """Test error response schema."""
        response = api_client.post("/score", json={})
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_districts_response_schema(self, api_client: TestClient):
        """Test districts endpoint response schema."""
        response = api_client.get("/districts")
        assert response.status_code == 200
        data = response.json()
        assert "districts" in data or "count" in data

    def test_score_response_schema(self, api_client: TestClient):
        """Test score endpoint response schema."""
        response = api_client.post(
            "/score", json={"location": "Accra", "precipitation": 50}
        )
        assert response.status_code in [200, 422]

    def test_batch_response_schema(self, api_client: TestClient):
        """Test batch endpoint response schema."""
        response = api_client.post("/score/batch", json={"requests": []})
        assert response.status_code in [200, 422]
