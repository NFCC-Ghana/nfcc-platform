"""Tests for alert API endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.database import alert_db
import sqlite3
from pathlib import Path
from contextlib import contextmanager

# Use a file-based test database instead of in-memory to avoid thread issues
TEST_DB_PATH = Path(__file__).parent.parent / "data" / "test_alerts.db"


@contextmanager
def get_test_db():
    """
    Get a test database connection with check_same_thread=False
    to allow usage across threads in the test client.
    """
    TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(TEST_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture(scope="function")
def db_with_test_data():
    """
    Create a fresh test database with sample data for each test.
    This ensures each test runs in isolation.
    """
    # Remove existing test database
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    
    # Initialize fresh database
    alert_db.init_db()
    
    # Insert test data
    from src.database.alert_db import save_alert
    
    test_alerts = [
        {"location": "Accra", "score": 85.0, "risk_tier": "CRITICAL", "precipitation": 75.0},
        {"location": "Accra", "score": 75.0, "risk_tier": "HIGH", "precipitation": 50.0},
        {"location": "Accra", "score": 60.0, "risk_tier": "HIGH", "precipitation": 40.0},
        {"location": "Accra", "score": 45.0, "risk_tier": "MODERATE", "precipitation": 30.0},
        {"location": "Accra", "score": 30.0, "risk_tier": "MODERATE", "precipitation": 20.0},
        {"location": "Accra", "score": 15.0, "risk_tier": "LOW", "precipitation": 10.0},
        {"location": "Tema", "score": 70.0, "risk_tier": "HIGH", "precipitation": 45.0},
        {"location": "Tema", "score": 50.0, "risk_tier": "MODERATE", "precipitation": 35.0},
        {"location": "Kumasi", "score": 55.0, "risk_tier": "MODERATE", "precipitation": 30.0},
        {"location": "Kumasi", "score": 40.0, "risk_tier": "MODERATE", "precipitation": 25.0},
    ]
    
    for alert in test_alerts:
        save_alert(**alert)
    
    yield


@pytest.fixture(scope="function")
def test_client(db_with_test_data):
    """
    Create a test client with the test database.
    Patches the get_db function to use the test database.
    """
    original_get_db = alert_db.get_db
    
    def mock_get_db():
        return get_test_db()
    
    alert_db.get_db = mock_get_db
    
    client = TestClient(app)
    yield client
    
    # Restore original
    alert_db.get_db = original_get_db


class TestAlertHistory:
    """Test the alert history endpoint."""
    
    def test_get_history_returns_alerts(self, test_client):
        response = test_client.get("/alerts/history")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert len(data["data"]) > 0
    
    def test_history_returns_alert_fields(self, test_client):
        response = test_client.get("/alerts/history?limit=1")
        assert response.status_code == 200
        data = response.json()
        alert = data["data"][0]
        assert "id" in alert
        assert "timestamp" in alert
        assert "location" in alert
        assert "risk_score" in alert
        assert "risk_tier" in alert
    
    def test_history_pagination_limit(self, test_client):
        response = test_client.get("/alerts/history?limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) <= 3
    
    def test_history_pagination_offset(self, test_client):
        page1 = test_client.get("/alerts/history?limit=2&offset=0").json()
        page2 = test_client.get("/alerts/history?limit=2&offset=2").json()
        
        if len(page1["data"]) > 0 and len(page2["data"]) > 0:
            assert page1["data"][0]["id"] != page2["data"][0]["id"]
    
    def test_history_location_filter(self, test_client):
        response = test_client.get("/alerts/history?location_filter=Accra")
        assert response.status_code == 200
        data = response.json()
        for alert in data["data"]:
            assert alert["location"] == "Accra"
    
    def test_history_location_filter_empty(self, test_client):
        response = test_client.get("/alerts/history?location_filter=Nonexistent")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 0
    
    def test_history_pagination_with_location_filter(self, test_client):
        response = test_client.get("/alerts/history?limit=2&offset=0&location_filter=Accra")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) <= 2
        for alert in data["data"]:
            assert alert["location"] == "Accra"
    
    def test_history_newest_first(self, test_client):
        response = test_client.get("/alerts/history?limit=10")
        data = response.json()
        timestamps = [alert["timestamp"] for alert in data["data"]]
        assert timestamps == sorted(timestamps, reverse=True)


class TestAlertStats:
    """Test the alert statistics endpoint."""
    
    def test_stats_returns_success(self, test_client):
        response = test_client.get("/alerts/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "by_risk_tier" in data
        assert "top_locations" in data
    
    def test_stats_risk_tier_counts(self, test_client):
        response = test_client.get("/alerts/stats")
        data = response.json()
        risk_tiers = {item["tier"]: item["count"] for item in data["by_risk_tier"]}
        assert len(risk_tiers) > 0
        for tier, count in risk_tiers.items():
            assert count > 0
            assert tier in ["LOW", "MODERATE", "HIGH", "CRITICAL", "EXTREME"]
    
    def test_stats_risk_tier_structure(self, test_client):
        response = test_client.get("/alerts/stats")
        data = response.json()
        for item in data["by_risk_tier"]:
            assert "tier" in item
            assert "count" in item
            assert isinstance(item["count"], int)
            assert item["count"] > 0
    
    def test_stats_top_locations(self, test_client):
        response = test_client.get("/alerts/stats")
        data = response.json()
        top_locations = data["top_locations"]
        assert len(top_locations) <= 5
        assert len(top_locations) > 0
    
    def test_stats_top_locations_structure(self, test_client):
        response = test_client.get("/alerts/stats")
        data = response.json()
        for item in data["top_locations"]:
            assert "location" in item
            assert "alert_count" in item
            assert isinstance(item["alert_count"], int)
            assert item["alert_count"] > 0
    
    def test_stats_top_locations_ordered(self, test_client):
        response = test_client.get("/alerts/stats")
        data = response.json()
        counts = [item["alert_count"] for item in data["top_locations"]]
        assert counts == sorted(counts, reverse=True)
    
    def test_stats_top_locations_accra_high_count(self, test_client):
        response = test_client.get("/alerts/stats")
        data = response.json()
        location_names = [item["location"] for item in data["top_locations"]]
        assert "Accra" in location_names


class TestAlertIntegration:
    """Integration tests combining multiple endpoints."""
    
    def test_history_and_stats_consistency(self, test_client):
        history_response = test_client.get("/alerts/history?limit=1000")
        history_data = history_response.json()
        stats_response = test_client.get("/alerts/stats")
        stats_data = stats_response.json()
        
        tier_counts = {}
        for alert in history_data["data"]:
            tier = alert["risk_tier"]
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        stats_tiers = {item["tier"]: item["count"] for item in stats_data["by_risk_tier"]}
        assert tier_counts == stats_tiers
