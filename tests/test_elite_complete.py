"""Elite resilience tests.

Previously these ran under names like "chaos engineering", "security
injection", "DoS resilience", and "latency injection" while actually
just posting 2-3 fixed payloads and asserting status_code in [200, 422]
- real, scheduled CI (.github/workflows/elite-resilience.yml), but test
bodies that didn't deliver what their names implied. One
(test_state_corruption) was a bare pytest.skip(). Rewritten below to
actually exercise what each name claims; anything genuinely out of
scope for this test file says so in its own docstring rather than
skipping silently.
"""

import concurrent.futures
import json
import sys
import time
from unittest.mock import patch

import pytest
import requests
from fastapi.testclient import TestClient

# src/hydrology/__init__.py does `from .weather_forecast import
# weather_forecast`, which - because the imported name matches the
# submodule's own name - overwrites src.hydrology's "weather_forecast"
# package attribute with the singleton WeatherForecastEngine instance
# instead of leaving it as the actual module. `import
# src.hydrology.weather_forecast as x` then resolves `x` to that
# instance, not the module, so `x.requests` doesn't exist. Going through
# sys.modules directly sidesteps the shadowing and gets the real module
# (which does have its own `requests` import to patch).
import src.hydrology.weather_forecast  # noqa: F401  (registers it in sys.modules)

_weather_forecast_module = sys.modules["src.hydrology.weather_forecast"]


class TestEliteComprehensive:
    """Comprehensive elite resilience tests."""

    def test_replay_debugger(self, api_client: TestClient):
        """Test replay debugger functionality."""
        payload = {"location": "Accra", "precipitation": 50}
        response1 = api_client.post("/score", json=payload)
        response2 = api_client.post("/score", json=payload)
        assert response1.status_code == response2.status_code

    def test_observability_complete(self, api_client: TestClient):
        """Test observability features."""
        response = api_client.post(
            "/score", json={"location": "Accra", "precipitation": 50}
        )
        assert response.status_code in [200, 422]

    def test_chaos_all_strategies(self, api_client: TestClient):
        """Malformed/unexpected shapes a real chaotic client could send -
        wrong types, missing fields, out-of-range values, extra unknown
        fields - asserting each is handled as a clean 422/200, never a
        raw 500 traceback leaking to the caller."""
        test_cases = [
            {"location": "Accra", "precipitation": 100},
            {"location": "Accra", "precipitation": 0},
            {"location": "Accra", "precipitation": -50},  # out of range
            {"location": "Accra", "precipitation": "not-a-number"},  # wrong type
            {"location": "", "precipitation": 50},  # empty required field
            {"location": "Accra"},  # missing precipitation
            {"location": "Accra", "precipitation": 50, "unexpected_field": True},
            {"location": None, "precipitation": 50},  # null for required field
            {"precipitation": 50},  # missing location entirely
            {},  # empty body
        ]
        for payload in test_cases:
            response = api_client.post("/score", json=payload)
            assert response.status_code in [200, 422], (
                f"Payload {payload!r} caused an unhandled failure: "
                f"{response.status_code} {response.text[:200]}"
            )

    def test_determinism_idempotent(self, api_client: TestClient):
        """Test idempotent behavior."""
        payload = {"location": "Accra", "precipitation": 75}
        responses = [api_client.post("/score", json=payload).json() for _ in range(3)]
        scores = [r.get("score", 0) for r in responses if "score" in r]
        if scores:
            assert all(s == scores[0] for s in scores)

    def test_security_injection(self, api_client: TestClient):
        """SQL/XSS-shaped strings must round-trip as inert data, never as
        executed content. For a JSON API the real safety property isn't
        "the string vanished" (calculate_score doesn't use `location` in
        any query at all, so it round-trips unchanged by design) - it's
        (a) the response is genuinely application/json, not text/html
        (the actual precondition for XSS execution in a browser), and
        (b) the payload appears back only inside a properly JSON-encoded
        string value, never as raw unescaped markup or a broken JSON
        document (which would indicate the input escaped its string
        context)."""
        payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert(1)>",
        ]
        for location in payloads:
            response = api_client.post(
                "/score", json={"location": location, "precipitation": 50}
            )
            assert response.status_code in [200, 422]
            assert response.headers["content-type"].startswith("application/json")
            if response.status_code == 200:
                data = response.json()  # raises if the JSON body is malformed
                assert data["location"] == location  # round-tripped verbatim, not executed

    def test_abuse_resilience(self, api_client: TestClient):
        """Genuinely concurrent requests, not a sequential loop - a
        sequential burst can't surface shared-state/locking issues (e.g.
        the SQLite writes behind AlertEngine.process() for score > 50)
        the way real concurrent traffic can."""
        payload = {"location": "Accra", "precipitation": 65}  # > 50: exercises alert_engine path

        def _fire():
            return api_client.post("/score", json=payload)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            responses = list(pool.map(lambda _: _fire(), range(20)))

        statuses = [r.status_code for r in responses]
        assert all(s in (200, 422, 429) for s in statuses), statuses
        # slowapi's Limiter (src/api/auth.py) is currently never applied
        # via @limiter.limit anywhere in src/ - confirmed by grep before
        # writing this test - so 429 cannot actually occur today. Kept
        # in the allowed set above rather than asserted-impossible, so
        # this test doesn't start failing the moment someone wires rate
        # limiting in; the real assertion is "no 500s under concurrency".
        assert all(s != 500 for s in statuses)

    def test_coverage_comprehensive(self, api_client: TestClient):
        """Test comprehensive coverage."""
        endpoints = ["/", "/health", "/districts", "/alerts"]
        for endpoint in endpoints:
            response = api_client.get(endpoint)
            assert response.status_code in [200, 404]

    def test_state_corruption(self, api_client: TestClient):
        """Fires concurrent requests with DIFFERENT inputs and confirms
        each response matches its OWN request rather than another
        in-flight request's - the actual failure mode "state corruption"
        implies (a shared mutable variable leaking one request's data
        into another's response), which a single-input test can never
        catch regardless of how many times it's repeated."""
        locations = [f"District-{i}" for i in range(15)]

        def _fire(location):
            precipitation = hash(location) % 100
            resp = api_client.post(
                "/score", json={"location": location, "precipitation": precipitation}
            )
            return location, precipitation, resp

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(_fire, locations))

        for location, precipitation, resp in results:
            assert resp.status_code == 200
            data = resp.json()
            assert data["location"] == location, (
                f"Response for {location!r} came back with location "
                f"{data['location']!r} - cross-request state leak"
            )

    def test_graceful_degradation(self, api_client: TestClient):
        """Test graceful degradation."""
        # Test with invalid JSON
        response = api_client.post("/score", data="invalid json")
        assert response.status_code == 422

    def test_latency_injection(self, api_client: TestClient):
        """Injects latency into the Open-Meteo call inside
        src.hydrology.weather_forecast and confirms the endpoint still
        completes successfully rather than timing out or raising - the
        actual property "latency injection" testing implies, not just
        confirming a fast path works.

        Fully mocks the response (never delegates to the real network)
        for two reasons found while writing this: a real call makes the
        test's pass/fail depend on genuine internet reachability from
        wherever CI happens to run, and WeatherForecastEngine caches by
        (lat, lon, hours) for an hour (weather_forecast.py's
        forecast_cache) - the module-level singleton persists for the
        whole pytest session, so if an earlier test already warmed the
        cache for these exact coordinates, requests.get is never called
        at all and the injected delay silently never happens. Using a
        district (Sunyani) unlikely to be touched by other tests plus an
        explicit cache clear makes this deterministic regardless of
        what ran before it or network conditions.
        """
        cache = _weather_forecast_module.weather_forecast.forecast_cache
        cache.clear()

        fake_response = requests.models.Response()
        fake_response.status_code = 200
        fake_response._content = json.dumps(
            {"hourly": {"time": [], "rain": [0.0] * 72}}
        ).encode("utf-8")

        def _slow_get(*args, **kwargs):
            time.sleep(1.5)
            return fake_response

        with patch.object(_weather_forecast_module.requests, "get", side_effect=_slow_get):
            start = time.monotonic()
            response = api_client.post(
                "/situation",
                json={"location": "Sunyani", "precipitation": 50},
                timeout=15,
            )
            elapsed = time.monotonic() - start

        cache.clear()  # don't leak this test's fake forecast into later tests

        assert response.status_code == 200
        assert elapsed >= 1.5  # the injected delay genuinely happened, not skipped

    def test_security_dos(self, api_client: TestClient):
        """Large/pathological payloads must be rejected or handled
        cleanly, never crash the process. No rate limiter is actually
        wired to this endpoint today (confirmed by grep for
        @limiter.limit across src/), so this only asserts graceful
        handling, not throttling."""
        for size in (10_000, 100_000, 1_000_000):
            response = api_client.post(
                "/score", json={"location": "X" * size, "precipitation": 50}
            )
            assert response.status_code in [200, 422, 413], (
                f"payload size {size} produced {response.status_code}"
            )
