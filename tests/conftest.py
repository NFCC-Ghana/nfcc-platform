"""Pytest configuration and fixtures for NFCC platform."""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.alert_db import init_db


@pytest.fixture(scope="session", autouse=True)
def initialize_database():
    """Initialize the database before any tests run."""
    # Use a temporary database for testing
    os.environ["NFCC_ENV"] = "testing"
    init_db()
    print("✅ Test database initialized")
    yield
    # Cleanup after tests
    db_path = Path("data/alerts.db")
    if db_path.exists():
        db_path.unlink()


def _new_api_test_client():
    from fastapi.testclient import TestClient
    from src.api.main import app

    # Ensure database is initialized
    init_db()

    with TestClient(app) as client:
        yield client


@pytest.fixture
def test_client():
    """Create a test client for API tests."""
    yield from _new_api_test_client()


@pytest.fixture
def api_client():
    """Create a test client for API tests.

    Same thing as test_client (a plain fastapi.testclient.TestClient
    against the real app, with the database initialized) under the
    fixture name a large fraction of tests/ was actually written
    against - about 40 tests across test_endpoints.py, test_subscriptions.py,
    test_elite_complete.py, test_elite_simple.py, test_forecast_api.py,
    test_pipeline.py, test_openapi_contract.py, and test_engine_edge_cases.py
    request `api_client` and errored with "fixture 'api_client' not found"
    before this existed - invisible in CI because pytest.ini's
    --maxfail=5 stopped every run long before reaching most of them.
    """
    yield from _new_api_test_client()


# Skip provider tests in CI if needed
def pytest_configure(config):
    config.addinivalue_line("markers", "ci_skip: skip test in CI environment")


def pytest_collection_modifyitems(items):
    """Skip provider tests in CI environment."""
    if os.environ.get("CI"):
        for item in items:
            if "provider" in item.nodeid.lower() or "mock" in item.nodeid.lower():
                item.add_marker(pytest.mark.skip(reason="Skipping in CI environment"))
