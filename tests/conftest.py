"""Pytest configuration and global fixtures."""

import sys
import os
import pytest
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set environment variables for testing
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("TESTING", "true")

# ============================================================
# Import fixtures - using try/except for graceful degradation
# ============================================================

# Model fixtures
try:
    from tests.fixtures.model_fixtures import trained_model, mock_model
except ImportError as e:
    print(f"⚠️ Could not load model_fixtures: {e}")

# DataFrame fixtures
try:
    from tests.fixtures.dataframe_fixtures import (
        sample_rainfall_dataframe,
        sample_features_dataframe,
        empty_dataframe,
        district_rainfall_dict,
    )
except ImportError as e:
    print(f"⚠️ Could not load dataframe_fixtures: {e}")

# Provider fixtures
try:
    from tests.fixtures.provider_fixtures import (
        mock_email_config,
        mock_sms_config,
        mock_whatsapp_config,
        sample_alert_payload,
    )
except ImportError as e:
    print(f"⚠️ Could not load provider_fixtures: {e}")

# ============================================================
# Pytest configuration
# ============================================================


def pytest_configure(config):
    """Configure pytest with custom markers."""
    markers = [
        ("slow", "marks tests as slow (deselect with '-m \"not slow\"')"),
        ("integration", "marks tests as integration tests"),
        ("unit", "marks tests as unit tests"),
        ("requires_api", "marks tests that require API server"),
        ("requires_twilio", "marks tests that require Twilio credentials"),
        ("requires_db", "marks tests that require database"),
    ]

    for marker, description in markers:
        config.addinivalue_line("markers", f"{marker}: {description}")


def pytest_collection_modifyitems(config, items):
    """Modify test collection behavior."""
    # Skip slow tests by default unless --runslow is passed
    if not config.getoption("-k") and not config.getoption("--runslow"):
        skip_slow = pytest.mark.skip(reason="Slow test. Use --runslow to execute")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--runslow", action="store_true", default=False, help="Run slow tests"
    )
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests",
    )


# ============================================================
# Session-scoped fixtures
# ============================================================


@pytest.fixture(scope="session")
def test_session():
    """Provide test session information."""
    return {
        "project_root": str(PROJECT_ROOT),
        "environment": "testing",
    }


@pytest.fixture(scope="session")
def test_client():
    """Create a test client for FastAPI."""
    try:
        from fastapi.testclient import TestClient
        from src.api.main import app

        return TestClient(app)
    except ImportError:
        pytest.skip("FastAPI not available")
        return None


# ============================================================
# Cleanup
# ============================================================


def pytest_sessionfinish(session, exitstatus):
    """Clean up after test session."""
    # Clean up any temporary files or connections
    pass
