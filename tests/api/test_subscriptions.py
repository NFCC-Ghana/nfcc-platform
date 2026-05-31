"""Tests for subscriptions API endpoints."""

import sqlite3
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.database.alert_db import init_subscriptions_table


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for subscriptions tests."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
def test_client(in_memory_db):
    """Create a FastAPI TestClient that uses an in-memory database."""

    def mock_get_db():
        class MockContext:
            def __enter__(self):
                return in_memory_db

            def __exit__(self, exc_type, exc_value, traceback):
                return False

        return MockContext()

    with patch("src.database.alert_db.get_db", side_effect=mock_get_db):
        init_subscriptions_table()
        with TestClient(app) as client:
            yield client


class TestSubscriptionsAPI:
    """Subscription endpoint tests."""

    def test_create_subscription_and_list(self, test_client):
        payload = {
            "email": "user@example.com",
            "phone": "+233201234567",
            "preferred_provider": "sms",
            "location_filter": "Accra Central",
            "min_risk_tier": "HIGH",
        }

        response = test_client.post("/subscriptions", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["email"] == payload["email"]
        assert data["phone"] == payload["phone"]
        assert data["preferred_provider"] == payload["preferred_provider"]
        assert data["location_filter"] == payload["location_filter"]
        assert data["min_risk_tier"] == payload["min_risk_tier"]
        assert data["active"] is True

        list_response = test_client.get("/subscriptions")
        assert list_response.status_code == 200
        subscriptions = list_response.json()
        assert any(sub["email"] == payload["email"] for sub in subscriptions)

    def test_delete_subscription(self, test_client):
        payload = {
            "email": "cancel@example.com",
            "preferred_provider": "email",
        }

        create_response = test_client.post("/subscriptions", json=payload)
        assert create_response.status_code == 201

        delete_response = test_client.delete(f"/subscriptions/{payload['email']}")
        assert delete_response.status_code == 200
        delete_data = delete_response.json()
        assert delete_data["unsubscribed"] is True
        assert delete_data["email"] == payload["email"]

        list_response = test_client.get("/subscriptions")
        assert list_response.status_code == 200
        assert all(sub["email"] != payload["email"] for sub in list_response.json())

    def test_duplicate_subscription_returns_409(self, test_client):
        payload = {
            "email": "duplicate@example.com",
            "preferred_provider": "email",
        }

        response1 = test_client.post("/subscriptions", json=payload)
        assert response1.status_code == 201

        response2 = test_client.post("/subscriptions", json=payload)
        assert response2.status_code == 409
        assert response2.json()["detail"] == "A subscription already exists for this email"

    def test_list_subscriptions_includes_min_risk_tier_and_location(self, test_client):
        payload = {
            "email": "tiered@example.com",
            "preferred_provider": "whatsapp",
            "location_filter": "Tema",
            "min_risk_tier": "CRITICAL",
        }

        response = test_client.post("/subscriptions", json=payload)
        assert response.status_code == 201

        subscriptions = test_client.get("/subscriptions").json()
        found = next((sub for sub in subscriptions if sub["email"] == payload["email"]), None)
        assert found is not None
        assert found["location_filter"] == payload["location_filter"]
        assert found["min_risk_tier"] == payload["min_risk_tier"]
        assert found["preferred_provider"] == payload["preferred_provider"]

    def test_get_inactive_subscriptions_when_requested(self, test_client):
        payload = {
            "email": "inactive@example.com",
            "preferred_provider": "email",
        }

        response = test_client.post("/subscriptions", json=payload)
        assert response.status_code == 201

        delete_response = test_client.delete(f"/subscriptions/{payload['email']}")
        assert delete_response.status_code == 200

        active_response = test_client.get("/subscriptions")
        assert active_response.status_code == 200
        assert all(sub["email"] != payload["email"] for sub in active_response.json())

        all_response = test_client.get("/subscriptions?active_only=false")
        assert all_response.status_code == 200
        assert any(sub["email"] == payload["email"] for sub in all_response.json())
