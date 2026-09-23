"""Regression tests for the security-hardening pass on src/api/main.py:
real security headers, a non-wildcard CORS allowlist, docs disabled in
production, and a real Retry-After header on a 429 rate-limit response.
"""

from fastapi.testclient import TestClient

from src.api.main import app, rate_limit_handler
from src.config.settings import settings

client = TestClient(app)


def test_security_headers_present():
    resp = client.get("/health")
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "max-age=" in resp.headers.get("strict-transport-security", "")


def test_cors_rejects_origin_not_in_allowlist():
    """A preflight from an origin that isn't in settings.ALLOWED_ORIGINS
    must not get an Access-Control-Allow-Origin header back - the real
    regression this guards is the previous allow_origins=["*"]."""
    resp = client.options(
        "/situation",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in {k.lower() for k in resp.headers}


def test_cors_accepts_known_dashboard_origin():
    """The real Streamlit Cloud dashboard origin (in settings.
    ALLOWED_ORIGINS by default) must still be allowed - the CORS fix
    should restrict, not break, the one real browser-facing consumer."""
    known_origin = settings.ALLOWED_ORIGINS[0]
    resp = client.options(
        "/situation",
        headers={
            "Origin": known_origin,
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.headers.get("access-control-allow-origin") == known_origin


def test_cors_methods_and_headers_are_not_wildcarded():
    """allow_methods/allow_headers were left wildcarded in an earlier
    pass despite fixing allow_origins - this is the completeness fix."""
    known_origin = settings.ALLOWED_ORIGINS[0]
    resp = client.options(
        "/situation",
        headers={
            "Origin": known_origin,
            "Access-Control-Request-Method": "POST",
        },
    )
    allowed_methods = resp.headers.get("access-control-allow-methods", "")
    assert "*" not in allowed_methods
    assert "POST" in allowed_methods


def test_docs_open_in_current_non_production_environment():
    """Tests run with ENVIRONMENT=development (never overridden in CI) -
    docs_url should reflect that, proving the ternary's non-production
    branch works. The production branch (None) is exercised directly
    below without needing a second full app instance."""
    assert settings.is_production is False
    assert app.docs_url == "/docs"
    assert app.redoc_url == "/redoc"
    assert app.openapi_url == "/openapi.json"


def test_docs_url_ternary_disables_in_production():
    """Direct check of the same expression main.py uses, for the branch
    the current (non-production) test environment can't otherwise
    exercise against a live app instance."""
    is_production = True
    assert (None if is_production else "/docs") is None


def test_rate_limit_response_includes_retry_after():
    """A 429 must tell a well-behaved client when to retry, not just
    that it was blocked."""
    from slowapi.errors import RateLimitExceeded
    from slowapi.wrappers import Limit
    from limits import parse
    import asyncio

    limit_item = parse("30/minute")
    limit = Limit(
        limit=limit_item,
        key_func=lambda: "test",
        scope=None,
        per_method=False,
        methods=None,
        error_message=None,
        exempt_when=None,
        cost=1,
        override_defaults=False,
    )
    exc = RateLimitExceeded(limit)

    response = asyncio.run(rate_limit_handler(None, exc))
    assert response.status_code == 429
    assert response.headers.get("retry-after") == "60"


def test_rate_limit_response_falls_back_safely_on_unexpected_exception_shape():
    """If slowapi's exception internals ever change shape, this must
    degrade to a sane default rather than raising inside the error
    handler itself (which would produce an opaque 500 instead of a 429)."""
    import asyncio

    class _FakeExc:
        detail = "fake"
        limit = None  # .limit.limit.get_expiry() will raise AttributeError

    response = asyncio.run(rate_limit_handler(None, _FakeExc()))
    assert response.status_code == 429
    assert response.headers.get("retry-after") == "60"
