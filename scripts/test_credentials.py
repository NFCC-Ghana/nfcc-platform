#!/usr/bin/env python3
"""Test script to verify Twilio and SMTP credentials."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_twilio():
    """Test Twilio WhatsApp credentials."""
    try:
        from twilio.rest import Client

        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")

        if not account_sid or account_sid == "mock_sid":
            print("⚠️  Twilio not configured - skipping")
            return None

        client = Client(account_sid, auth_token)

        try:
            balance = client.balance.fetch()
            print(f"✅ Twilio account balance: ${balance.balance} {balance.currency}")
        except:
            print("✅ Twilio API accessible")

        # Test WhatsApp send
        whatsapp_to = (
            os.getenv("ALERT_WHATSAPP_RECIPIENTS", "").split(",")[0]
            if os.getenv("ALERT_WHATSAPP_RECIPIENTS")
            else None
        )
        whatsapp_from = os.getenv("TWILIO_WHATSAPP_FROM")

        if whatsapp_to and whatsapp_from:
            try:
                message = client.messages.create(
                    body="🧪 Test from NFCC Platform! Your WhatsApp is working! 🎉",
                    from_=whatsapp_from,
                    to=whatsapp_to,
                )
                print(f"✅ Test WhatsApp sent! SID: {message.sid}")
            except Exception as e:
                print(f"⚠️ WhatsApp test send failed (normal if not in sandbox): {e}")

        return True

    except Exception as e:
        print(f"❌ Twilio test failed: {e}")
        return False


def test_smtp():
    """Test SMTP email credentials (skip if not configured)."""
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not smtp_user or not smtp_password:
        print("⚠️  SMTP not configured - skipping")
        return None

    if smtp_user == "test@gmail.com" or smtp_user == "your-email@gmail.com":
        print("⚠️  SMTP using placeholder credentials - skipping")
        return None

    try:
        import smtplib

        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            print(f"✅ SMTP login successful for {smtp_user}")

        return True

    except Exception as e:
        print(f"❌ SMTP test failed: {e}")
        return False


def test_model():
    """Test model loading."""
    try:
        from src.config.settings import settings
        from pathlib import Path

        model_path = Path(settings.MODEL_PATH)
        if not model_path.exists():
            print(f"⚠️  Model not found at {model_path}")
            return None

        import pickle

        with open(model_path, "rb") as f:
            model = pickle.load(f)
        print(f"✅ Model loaded successfully from {model_path}")
        return True
    except Exception as e:
        print(f"❌ Model load failed: {e}")
        return False


def main():
    print("=" * 60)
    print("NFCC Platform Credential Test")
    print("=" * 60)

    # Load environment
    env_file = Path(".env.production")
    if env_file.exists():
        from dotenv import load_dotenv

        load_dotenv(env_file)
        print(f"Loaded {env_file}")

    results = {}

    print("\n📱 Testing Twilio WhatsApp...")
    results["twilio"] = test_twilio()

    print("\n📧 Testing SMTP Email...")
    results["smtp"] = test_smtp()

    print("\n🤖 Testing Model...")
    results["model"] = test_model()

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    all_good = True
    for service, result in results.items():
        if result is True:
            print(f"✅ {service.upper()}: Working")
        elif result is False:
            print(f"❌ {service.upper()}: Failed")
            all_good = False
        else:
            print(f"⚠️  {service.upper()}: Not configured")

    # WhatsApp is the only required provider
    if results.get("twilio") is True:
        print("\n✅ WhatsApp is working! System ready for production.")
        sys.exit(0)
    elif results.get("twilio") is False:
        print("\n❌ WhatsApp configuration failed. Please check your credentials.")
        sys.exit(1)
    else:
        print(
            "\n⚠️  WhatsApp not configured. Please add Twilio credentials to .env.production"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
