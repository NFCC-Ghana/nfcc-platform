#!/usr/bin/env python3
import os

from dotenv import load_dotenv

# Load .env.production
load_dotenv(".env.production")

print("=" * 50)
print("Environment Variable Check")
print("=" * 50)

vars_to_check = [
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_SMS_FROM",
    "TWILIO_WHATSAPP_FROM",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "ALERT_EMAIL_RECIPIENTS",
    "ALERT_WHATSAPP_RECIPIENTS",
    "ENVIRONMENT",
]

for var in vars_to_check:
    value = os.getenv(var)
    if value:
        # Mask sensitive values
        if "TOKEN" in var or "PASSWORD" in var:
            print(f"✅ {var}: {'*' * 8}{value[-4:]}")
        else:
            print(f"✅ {var}: {value}")
    else:
        print(f"❌ {var}: NOT SET")

print("=" * 50)

# Check if real credentials (not mock)
if os.getenv("SMTP_USER") and os.getenv("SMTP_USER") != "test@gmail.com":
    print("✅ Real Gmail credentials detected")
else:
    print("⚠️  Using mock email credentials")

if os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_ACCOUNT_SID").startswith("AC"):
    print("✅ Real Twilio credentials detected")
else:
    print("⚠️  Using mock Twilio credentials")
