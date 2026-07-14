#!/usr/bin/env python3
"""Complete test data generator for NFCC Alert API."""

import random
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

# Configuration
BASE_URL = "http://localhost:8000"
DB_PATH = Path("data/alerts.db")

# Test locations
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

# Test scenarios (location, precipitation)
TEST_SCENARIOS = [
    ("Accra Central", 95.5),
    ("Tema", 75.0),
    ("Kumasi", 55.0),
    ("Takoradi", 45.0),
    ("Tamale", 25.0),
    ("Accra East", 85.0),
    ("Accra West", 65.0),
    ("Cape Coast", 35.0),
    ("Koforidua", 40.0),
    ("Ho", 30.0),
    ("Nima", 78.0),
    ("Dansoman", 58.0),
    ("Kasoa", 42.0),
    ("Mallam Junction", 82.0),
    ("Ga West", 68.0),
]


def create_alerts_via_api():
    """Create alerts by calling the /score API endpoint."""
    print("📱 Creating alerts via API...")
    print("-" * 40)

    success_count = 0
    fail_count = 0
    results = []

    for location, precipitation in TEST_SCENARIOS:
        try:
            response = requests.post(
                f"{BASE_URL}/score",
                json={"location": location, "precipitation": precipitation},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                results.append(data)
                success_count += 1
                print(
                    f"✅ {location}: {data.get('score', '?')} ({data.get('risk_tier', '?')})"
                )
            else:
                print(f"❌ {location}: HTTP {response.status_code}")
                fail_count += 1

            time.sleep(0.1)  # Small delay

        except Exception as e:
            print(f"❌ {location}: {e}")
            fail_count += 1

    print("-" * 40)
    print(f"✅ Created {success_count} alerts via API")
    print(f"❌ Failed: {fail_count}")
    return results


def insert_historical_alerts():
    """Insert historical alerts directly into database."""
    print("\n📊 Creating historical alerts...")
    print("-" * 40)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Risk tier configurations
    risk_configs = [
        ("LOW", 0, 30, 0.30),
        ("MODERATE", 30, 50, 0.35),
        ("HIGH", 50, 70, 0.20),
        ("CRITICAL", 70, 85, 0.10),
        ("EXTREME", 85, 100, 0.05),
    ]

    providers = ["whatsapp", "sms", "email", "mock"]
    error_messages = [
        "Twilio API timeout",
        "Invalid phone number",
        "SMTP connection failed",
        "Rate limit exceeded",
    ]

    alerts_created = 0
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    current_date = start_date
    while current_date <= end_date:
        # 0-8 alerts per day
        num_alerts = random.randint(0, 8)

        for _ in range(num_alerts):
            location = random.choice(LOCATIONS)

            # Select risk tier based on probability
            rand = random.random()
            cumulative = 0
            selected_tier = risk_configs[0]
            for tier_name, score_min, score_max, prob in risk_configs:
                cumulative += prob
                if rand <= cumulative:
                    selected_tier = (tier_name, score_min, score_max)
                    break

            tier_name, score_min, score_max = selected_tier
            risk_score = round(random.uniform(score_min, score_max), 1)

            # 85% success rate
            alert_sent = random.random() < 0.85

            provider = random.choice(providers) if alert_sent else None
            message_id = f"MSG_{random.randint(10000, 99999)}" if alert_sent else None
            error = None if alert_sent else random.choice(error_messages)

            # Random time within the day
            random_time = current_date.replace(
                hour=random.randint(0, 23),
                minute=random.randint(0, 59),
                second=random.randint(0, 59),
            )

            cursor.execute(
                """
                INSERT INTO alerts
                (timestamp, location, risk_score, risk_tier, alert_sent, provider, message_id, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    random_time.isoformat() + "Z",
                    location,
                    risk_score,
                    tier_name,
                    1 if alert_sent else 0,
                    provider,
                    message_id,
                    error,
                ),
            )
            alerts_created += 1

        current_date += timedelta(days=1)

    conn.commit()
    conn.close()
    print(f"✅ Created {alerts_created} historical alerts")
    return alerts_created


def verify_database():
    """Verify database contents."""
    print("\n🔍 Database Verification")
    print("=" * 40)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM alerts")
    total = cursor.fetchone()[0]
    print(f"Total alerts: {total}")

    cursor.execute("SELECT risk_tier, COUNT(*) FROM alerts GROUP BY risk_tier")
    by_tier = cursor.fetchall()
    print("\nAlerts by risk tier:")
    for tier, count in by_tier:
        print(f"  {tier}: {count}")

    cursor.execute(
        "SELECT location, COUNT(*) FROM alerts GROUP BY location ORDER BY COUNT(*) DESC LIMIT 5"
    )
    top_locations = cursor.fetchall()
    print("\nTop 5 locations:")
    for location, count in top_locations:
        print(f"  {location}: {count}")

    cursor.execute("SELECT COUNT(*) FROM alerts WHERE alert_sent = 1")
    successful = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM alerts WHERE alert_sent = 0")
    failed = cursor.fetchone()[0]

    print(f"\nDelivery Status:")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")

    conn.close()
    return total


def test_api_endpoints():
    """Test all alert API endpoints."""
    print("\n🌐 API Endpoint Tests")
    print("=" * 40)

    # Test history endpoint
    print("\n1. GET /alerts/history")
    response = requests.get(f"{BASE_URL}/alerts/history?limit=5")
    if response.status_code == 200:
        data = response.json()
        print(f"   Status: {data.get('status')}")
        print(f"   Count: {data.get('count')}")
        print(f"   Total available: {data.get('total_available', 'N/A')}")
    else:
        print(f"   ❌ Failed: HTTP {response.status_code}")

    # Test stats endpoint
    print("\n2. GET /alerts/stats")
    response = requests.get(f"{BASE_URL}/alerts/stats")
    if response.status_code == 200:
        data = response.json()
        print(f"   Status: {data.get('status')}")
        print(f"   Risk tiers: {len(data.get('by_risk_tier', []))}")
        print(f"   Top locations: {len(data.get('top_locations', []))}")
    else:
        print(f"   ❌ Failed: HTTP {response.status_code}")

    # Test location filter
    print("\n3. GET /alerts/history?location=Accra Central")
    response = requests.get(
        f"{BASE_URL}/alerts/history?location=Accra%20Central&limit=3"
    )
    if response.status_code == 200:
        data = response.json()
        print(f"   Status: {data.get('status')}")
        print(f"   Count: {data.get('count')}")
    else:
        print(f"   ❌ Failed: HTTP {response.status_code}")

    # Test pagination
    print("\n4. Pagination Test")
    page1 = requests.get(f"{BASE_URL}/alerts/history?limit=3&offset=0")
    page2 = requests.get(f"{BASE_URL}/alerts/history?limit=3&offset=3")

    if page1.status_code == 200 and page2.status_code == 200:
        data1 = page1.json()
        data2 = page2.json()
        print(f"   Page 1 count: {data1.get('count')}")
        print(f"   Page 2 count: {data2.get('count')}")
    else:
        print(f"   ❌ Pagination test failed")


def main():
    print("=" * 60)
    print("NFCC Alert API - Complete Test Data Generation")
    print("=" * 60)

    # Step 1: Verify API is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ API not responding. Please start the API first.")
            return
        print("✅ API is running")
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return

    # Step 2: Create alerts via API
    api_alerts = create_alerts_via_api()

    # Step 3: Insert historical alerts
    historical_alerts = insert_historical_alerts()

    # Step 4: Verify database
    total_alerts = verify_database()

    # Step 5: Test API endpoints
    test_api_endpoints()

    print("\n" + "=" * 60)
    print("✅ COMPLETE! Test data generation finished")
    print(f"   Total alerts created: {total_alerts}")
    print("=" * 60)
    print("\nYou can now test:")
    print("  curl http://localhost:8000/alerts/history | python -m json.tool")
    print("  curl http://localhost:8000/alerts/stats | python -m json.tool")


if __name__ == "__main__":
    main()
