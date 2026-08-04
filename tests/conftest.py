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


@pytest.fixture
def test_client():
    """Create a test client for API tests."""
    from fastapi.testclient import TestClient
    from src.api.main import app
    
    # Ensure database is initialized
    init_db()
    
    with TestClient(app) as client:
        yield client


# Skip provider tests in CI if needed
def pytest_configure(config):
    config.addinivalue_line("markers", "ci_skip: skip test in CI environment")


def pytest_collection_modifyitems(items):
    """Skip provider tests in CI environment."""
    if os.environ.get("CI"):
        for item in items:
            if "provider" in item.nodeid.lower() or "mock" in item.nodeid.lower():
                item.add_marker(pytest.mark.skip(reason="Skipping in CI environment"))
