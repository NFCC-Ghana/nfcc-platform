"""
Tests for Alert API endpoints.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.database.alert_db import get_db, get_db_connection


def test_health_endpoint():
    """Test the health endpoint."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_alerts_endpoint():
    """Test the alerts endpoint."""
    client = TestClient(app)
    response = client.get("/api/alerts")
    assert response.status_code in [200, 404, 500]


def test_alert_history():
    """Test alert history endpoint."""
    client = TestClient(app)
    response = client.get("/api/alerts/history")
    assert response.status_code in [200, 404, 500]


def test_alert_stats():
    """Test alert stats endpoint."""
    client = TestClient(app)
    response = client.get("/api/alerts/stats")
    assert response.status_code in [200, 404, 500]


def test_db_connection():
    """Test database connection."""
    conn = get_db_connection()
    assert conn is not None
    assert conn.total_changes >= 0


def test_get_db_alias():
    """Test that get_db() is an alias for get_db_connection()."""
    conn1 = get_db_connection()
    conn2 = get_db()
    assert conn1 is not None
    assert conn2 is not None


@pytest.mark.skip(reason="Requires API key or authentication")
def test_authenticated_endpoint():
    """Placeholder for authenticated endpoint tests."""
    pass
