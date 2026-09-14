#!/usr/bin/env python3
"""Create comprehensive test alerts for the NFCC platform.

This script generates realistic flood alert data for testing the alert API.
It creates alerts across multiple locations, risk tiers, and time periods.
"""

import requests
import json
import time
from datetime import datetime, timedelta
import random
import sqlite3
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
DB_PATH = Path("data/alerts.db")

# Test locations (districts in and around Accra)
LOCATIONS = [
    "Accra Central",
    "Accra East",
    "Accra West",
    "Tema",
    "Kumasi",
    "Takoradi",
    "Tamale",
    "Cape Coast",
    "Koforidua",
    "Ho",
    "Nima",
    "Dansoman",
    "Kasoa",
    "Mallam Junction",
    "Ga West",
]

# Risk tiers and their score ranges
RISK_CONFIGS = {
    "LOW": {"score_range": (0, 30), "precip_range": (0, 15), "probability": 0.35},
    "MODERATE": {
        "score_range": (30, 50),
        "precip_range": (15, 35),
        "probability": 0.30,
    },
    "HIGH": {"score_range": (50, 70), "precip_range": (35, 60), "probability": 0.20},
    "CRITICAL": {
        "score_range": (70, 85),
        "precip_range": (60, 100),
        "probability": 0.10,
    },
    "EXTREME": {
        "score_range": (85, 100),
        "precip_range": (100, 150),
        "probability": 0.05,
    },
}

# Alert providers
PROVIDERS = ["whatsapp", "sms", "email", "mock"]


def create_alert_via_api(location: str, precipitation: float) -> dict:
    """Create an alert by calling the /score endpoint."""
    payload = {"location": location, "precipitation": precipitation}

    try:
        response = requests.post(f"{BASE_URL}/score", json=payload, timeout=10)

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}", "location": location}
    except Exception as e:
        return {"error": str(e), "location": location}


def insert_alert_directly(alert_data: dict) -> int:
    """Insert an alert directly into the database (for historical data)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO alerts
        (timestamp, location, risk_score, risk_tier, alert_sent, provider, message_id, error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            alert_data["timestamp"],
            alert_data["location"],
            alert_data["risk_score"],
            alert_data["risk_tier"],
            alert_data["alert_sent"],
            alert_data.get("provider"),
            alert_data.get("message_id"),
            alert_data.get("error"),
        ),
    )

    alert_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return alert_id


def generate_historical_alerts():
    """Generate historical alerts for the past 30 days."""
    print("📊 Generating historical alerts...")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    alerts_created = 0

    current_date = start_date
    while current_date <= end_date:
        # Number of alerts per day varies (0-8)
        num_alerts = random.randint(0, 8)

        for _ in range(num_alerts):
            location = random.choice(LOCATIONS)

            # Choose risk tier based on probability
            rand = random.random()
            cumulative = 0
            selected_tier = "LOW"

            for tier, config in RISK_CONFIGS.items():
                cumulative += config["probability"]
                if rand <= cumulative:
                    selected_tier = tier
                    break

            config = RISK_CONFIGS[selected_tier]
            score_min, score_max = config["score_range"]
            risk_score = round(random.uniform(score_min, score_max), 1)

            # Determine if alert was sent successfully (90% success rate)
            alert_sent = random.random() < 0.9

            provider = random.choice(PROVIDERS) if alert_sent else None
            message_id = f"TEST_{random.randint(10000, 99999)}" if alert_sent else None
            error = None if alert_sent else "Provider temporarily unavailable"

            # Random time within the day
            random_time = current_date.replace(
                hour=random.randint(0, 23),
                minute=random.randint(0, 59),
                second=random.randint(0, 59),
            )

            alert_data = {
                "timestamp": random_time.isoformat() + "Z",
                "location": location,
                "risk_score": risk_score,
                "risk_tier": selected_tier,
                "alert_sent": alert_sent,
                "provider": provider,
                "message_id": message_id,
                "error": error,
            }

            insert_alert_directly(alert_data)
            alerts_created += 1

        current_date += timedelta(days=1)

    print(f"✅ Created {alerts_created} historical alerts across 30 days")
    return alerts_created


def create_recent_alerts():
    """Create recent alerts using the API (to test real-time flow)."""
    print("\n📱 Creating recent alerts via API...")

    # Create 10 recent alerts
    test_scenarios = [
        ("Accra Central", 95.5, "EXTREME"),
        ("Tema", 75.0, "CRITICAL"),
        ("Kumasi", 55.0, "HIGH"),
        ("Takoradi", 45.0, "MODERATE"),
        ("Tamale", 25.0, "LOW"),
        ("Accra East", 85.0, "EXTREME"),
        ("Ga West", 65.0, "HIGH"),
        ("Nima", 78.0, "CRITICAL"),
        ("Dansoman", 58.0, "HIGH"),
        ("Kasoa", 42.0, "MODERATE"),
        ("Accra West", 88.0, "EXTREME"),
        ("Cape Coast", 38.0, "MODERATE"),
        ("Koforidua", 32.0, "MODERATE"),
        ("Ho", 28.0, "LOW"),
        ("Mallam Junction", 82.0, "CRITICAL"),
    ]

    alerts_created = 0
    for location, precipitation, expected_tier in test_scenarios:
        result = create_alert_via_api(location, precipitation)
        if "error" not in result:
            alerts_created += 1
            print(
                f"  ✅ Created alert for {location}: {result.get('score', '?')} ({expected_tier})"
            )
        else:
            print(f"  ❌ Failed: {result}")

        # Small delay to avoid overwhelming the API
        time.sleep(0.1)

    print(f"✅ Created {alerts_created} recent alerts via API")
    return alerts_created


def verify_alerts():
    """Verify alerts were created successfully."""
    print("\n🔍 Verifying alerts...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM alerts")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT risk_tier, COUNT(*) FROM alerts GROUP BY risk_tier")
    by_tier = cursor.fetchall()

    cursor.execute(
        "SELECT location, COUNT(*) FROM alerts GROUP BY location ORDER BY COUNT(*) DESC LIMIT 5"
    )
    top_locations = cursor.fetchall()

    conn.close()

    print(f"📊 Total alerts in database: {total}")
    print(f"\n📈 Alerts by risk tier:")
    for tier, count in by_tier:
        print(f"   {tier}: {count}")

    print(f"\n📍 Top 5 locations:")
    for location, count in top_locations:
        print(f"   {location}: {count}")

    return total


def main():
    """Main execution function."""
    print("=" * 60)
    print("NFCC Alert Test Data Generator")
    print("=" * 60)

    # First, check if API is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ API not responding correctly. Please start the API first.")
            print("   Run: uvicorn src.api.main:app --reload")
            return
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("   Please start the API first:")
        print("   uvicorn src.api.main:app --reload")
        return

    print("✅ API is running\n")

    # Generate data
    historical = generate_historical_alerts()
    recent = create_recent_alerts()
    total = verify_alerts()

    print("\n" + "=" * 60)
    print("✅ Test data generation complete!")
    print(f"   Historical alerts: {historical}")
    print(f"   Recent alerts: {recent}")
    print(f"   Total alerts: {total}")
    print("=" * 60)

    print("\n📋 You can now test the alert API:")
    print("   curl http://localhost:8000/alerts/history?limit=10 | python -m json.tool")
    print("   curl http://localhost:8000/alerts/stats | python -m json.tool")


if __name__ == "__main__":
    main()
