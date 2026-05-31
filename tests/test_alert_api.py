"""Pytest tests for alert API router endpoints."""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sqlite3

from src.api.main import app
from src.database.alert_db import get_db


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def in_memory_db():
    """
    Create an in-memory SQLite database for testing.
    
    This fixture sets up a complete alerts table with test data,
    avoiding writes to the real data/alerts.db file during tests.
    """
    # Create in-memory connection
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Create alerts table schema (matches production)
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        location TEXT NOT NULL,
        risk_score REAL NOT NULL,
        risk_tier TEXT NOT NULL,
        alert_sent BOOLEAN NOT NULL,
        provider TEXT,
        message_id TEXT,
        error TEXT
    )
    """
    cursor.execute(create_table_sql)
    
    # Create indexes for consistency with production
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_location ON alerts(location)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON alerts(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_risk_tier ON alerts(risk_tier)")
    
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def db_with_test_data(in_memory_db):
    """
    Populate in-memory database with test alert data.
    
    Creates diverse test records across different locations, risk tiers,
    timestamps, and provider statuses.
    """
    conn = in_memory_db
    cursor = conn.cursor()
    
    # Test data: mix of successful and failed alerts across different locations
    test_alerts = [
        # Accra - multiple alerts
        ("2026-05-31T10:00:00Z", "Accra", 45.5, "MODERATE", True, "email", "msg-001", None),
        ("2026-05-31T10:15:00Z", "Accra", 55.0, "HIGH", True, "sms", "msg-002", None),
        ("2026-05-31T10:30:00Z", "Accra", 75.5, "CRITICAL", True, "whatsapp", "msg-003", None),
        ("2026-05-31T10:45:00Z", "Accra", 35.0, "MODERATE", False, "email", None, "Failed to send"),
        
        # Tema - multiple alerts
        ("2026-05-31T11:00:00Z", "Tema", 52.0, "MODERATE", True, "sms", "msg-004", None),
        ("2026-05-31T11:15:00Z", "Tema", 65.5, "HIGH", True, "email", "msg-005", None),
        ("2026-05-31T11:30:00Z", "Tema", 42.0, "MODERATE", False, "whatsapp", None, "Provider error"),
        
        # Kumasi - fewer alerts
        ("2026-05-31T12:00:00Z", "Kumasi", 48.5, "MODERATE", True, "email", "msg-006", None),
        ("2026-05-31T12:15:00Z", "Kumasi", 70.0, "CRITICAL", True, "sms", "msg-007", None),
        
        # Cape Coast - single alert
        ("2026-05-31T12:30:00Z", "Cape Coast", 38.0, "MODERATE", True, "whatsapp", "msg-008", None),
        
        # Critical and extreme tier counts
        ("2026-05-31T13:00:00Z", "Accra", 82.0, "CRITICAL", True, "email", "msg-009", None),
        ("2026-05-31T13:15:00Z", "Tema", 92.5, "EXTREME", True, "sms", "msg-010", None),
    ]
    
    insert_sql = """
    INSERT INTO alerts 
    (timestamp, location, risk_score, risk_tier, alert_sent, provider, message_id, error)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    cursor.executemany(insert_sql, test_alerts)
    conn.commit()
    
    return conn


@pytest.fixture
def test_client(db_with_test_data):
    """
    Create FastAPI TestClient with mocked database.
    
    Patches the get_db context manager to return the in-memory database
    instead of connecting to the real SQLite file.
    """
    # Patch get_db to return in-memory database
    def mock_get_db():
        class MockContext:
            def __init__(self, conn):
                self.conn = conn
            
            def __enter__(self):
                return self.conn
            
            def __exit__(self, *args):
                pass
        
        return MockContext(db_with_test_data)
    
    with patch("src.database.alert_db.get_db", side_effect=mock_get_db):
        client = TestClient(app)
        yield client


# ============================================================
# Test Cases
# ============================================================

class TestAlertHistory:
    """Test /alerts/history endpoint."""
    
    def test_get_history_returns_alerts(self, test_client):
        """Test that /alerts/history returns alert records."""
        response = test_client.get("/alerts/history")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["status"] == "success"
        assert "count" in data
        assert "data" in data
        assert isinstance(data["data"], list)
        
        # Should have all test alerts
        assert data["count"] > 0
        assert len(data["data"]) > 0
        
    def test_history_returns_alert_fields(self, test_client):
        """Test that returned alerts have all expected fields."""
        response = test_client.get("/alerts/history?limit=1")
        
        assert response.status_code == 200
        data = response.json()
        
        # Get first alert
        alert = data["data"][0]
        
        # Verify all required fields are present
        required_fields = {
            "id", "timestamp", "location", "risk_score", "risk_tier",
            "alert_sent", "provider", "message_id", "error"
        }
        assert all(field in alert for field in required_fields)
    
    def test_history_pagination_limit(self, test_client):
        """Test that limit parameter restricts returned records."""
        # Request with limit=3
        response = test_client.get("/alerts/history?limit=3")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return exactly 3 records
        assert data["count"] == 3
        assert len(data["data"]) == 3
        assert data["limit"] == 3
    
    def test_history_pagination_offset(self, test_client):
        """Test that offset parameter correctly skips records."""
        # Get first page
        page1 = test_client.get("/alerts/history?limit=2&offset=0").json()
        first_ids = [alert["id"] for alert in page1["data"]]
        
        # Get second page
        page2 = test_client.get("/alerts/history?limit=2&offset=2").json()
        second_ids = [alert["id"] for alert in page2["data"]]
        
        # Pages should have different alerts
        assert first_ids != second_ids
        assert page1["offset"] == 0
        assert page2["offset"] == 2
    
    def test_history_limit_max_validation(self, test_client):
        """Test that limit greater than 1000 is rejected."""
        response = test_client.get("/alerts/history?limit=2000")
        
        # Should fail validation (422 unprocessable entity)
        assert response.status_code == 422
    
    def test_history_location_filter(self, test_client):
        """Test that location filter returns only matching alerts."""
        response = test_client.get("/alerts/history?location=Accra")
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned alerts should be from Accra
        assert all(alert["location"] == "Accra" for alert in data["data"])
        assert data["location_filter"] == "Accra"
        assert data["count"] > 0
    
    def test_history_location_filter_empty(self, test_client):
        """Test location filter that matches no records."""
        response = test_client.get("/alerts/history?location=NonExistentLocation")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return success but no data
        assert data["status"] == "success"
        assert data["count"] == 0
        assert len(data["data"]) == 0
    
    def test_history_pagination_with_location_filter(self, test_client):
        """Test that pagination and location filter work together."""
        # Accra has multiple alerts, test pagination on filtered results
        response = test_client.get("/alerts/history?location=Accra&limit=2&offset=0")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should be paginated Accra results
        assert all(alert["location"] == "Accra" for alert in data["data"])
        assert data["count"] <= 2
        assert data["location_filter"] == "Accra"
    
    def test_history_newest_first(self, test_client):
        """Test that alerts are returned with newest first."""
        response = test_client.get("/alerts/history?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        
        # Extract timestamps
        timestamps = [alert["timestamp"] for alert in data["data"]]
        
        # Verify they're in descending order (newest first)
        assert timestamps == sorted(timestamps, reverse=True)


class TestAlertStats:
    """Test /alerts/stats endpoint."""
    
    def test_stats_returns_success(self, test_client):
        """Test that /alerts/stats returns successful response."""
        response = test_client.get("/alerts/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "by_risk_tier" in data
        assert "top_locations" in data
    
    def test_stats_risk_tier_counts(self, test_client):
        """Test that risk tier statistics are correct."""
        response = test_client.get("/alerts/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        # Convert to dict for easier testing
        risk_tiers = {item["tier"]: item["count"] for item in data["by_risk_tier"]}
        
        # Verify we have counts for different tiers
        assert len(risk_tiers) > 0
        
        # Check that counts are reasonable
        for tier, count in risk_tiers.items():
            assert count > 0
            assert tier in ["LOW", "MODERATE", "HIGH", "CRITICAL", "EXTREME"]
    
    def test_stats_risk_tier_structure(self, test_client):
        """Test that risk tier response has correct structure."""
        response = test_client.get("/alerts/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        # Each risk tier entry should have tier and count
        for item in data["by_risk_tier"]:
            assert "tier" in item
            assert "count" in item
            assert isinstance(item["count"], int)
            assert item["count"] > 0
    
    def test_stats_top_locations(self, test_client):
        """Test that top locations are returned correctly."""
        response = test_client.get("/alerts/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        top_locations = data["top_locations"]
        
        # Should have at most 5 locations (as per API design)
        assert len(top_locations) <= 5
        
        # Should have at least one location
        assert len(top_locations) > 0
    
    def test_stats_top_locations_structure(self, test_client):
        """Test that top locations have correct structure."""
        response = test_client.get("/alerts/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        # Each location entry should have location and alert_count
        for item in data["top_locations"]:
            assert "location" in item
            assert "alert_count" in item
            assert isinstance(item["alert_count"], int)
            assert item["alert_count"] > 0
    
    def test_stats_top_locations_ordered(self, test_client):
        """Test that top locations are ordered by count descending."""
        response = test_client.get("/alerts/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        top_locations = data["top_locations"]
        counts = [item["alert_count"] for item in top_locations]
        
        # Counts should be in descending order
        assert counts == sorted(counts, reverse=True)
    
    def test_stats_top_locations_accra_high_count(self, test_client):
        """Test that Accra (with most alerts) is in top locations."""
        response = test_client.get("/alerts/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        top_locations = data["top_locations"]
        location_names = [item["location"] for item in top_locations]
        
        # Accra should be in top locations (has the most in test data)
        assert "Accra" in location_names


class TestAlertIntegration:
    """Integration tests combining multiple endpoints."""
    
    def test_history_and_stats_consistency(self, test_client):
        """Test that history and stats data are consistent."""
        # Get all history
        history_response = test_client.get("/alerts/history?limit=1000")
        history_data = history_response.json()
        
        # Get stats
        stats_response = test_client.get("/alerts/stats")
        stats_data = stats_response.json()
        
        # Count risk tiers from history
        tier_counts = {}
        for alert in history_data["data"]:
            tier = alert["risk_tier"]
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        # Compare with stats
        stats_tiers = {item["tier"]: item["count"] for item in stats_data["by_risk_tier"]}
        
        # Should match
        assert tier_counts == stats_tiers
    
    def test_alert_successful_and_failed(self, test_client):
        """Test that both successful and failed alerts are returned."""
        response = test_client.get("/alerts/history?limit=100")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check for both successful and failed alerts
        alert_statuses = [alert["alert_sent"] for alert in data["data"]]
        
        # Should have both True and False
        assert True in alert_statuses
        assert False in alert_statuses
    
    def test_error_messages_captured(self, test_client):
        """Test that error messages are captured for failed alerts."""
        response = test_client.get("/alerts/history?limit=100")
        
        assert response.status_code == 200
        data = response.json()
        
        # Find failed alerts
        failed_alerts = [a for a in data["data"] if not a["alert_sent"]]
        
        # Failed alerts should have error messages
        assert len(failed_alerts) > 0
        for alert in failed_alerts:
            assert alert["error"] is not None or alert["message_id"] is None
