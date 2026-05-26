#!/usr/bin/env python3
"""Strict environment validation - handles empty values correctly."""

import re
import sys
from pathlib import Path


def validate_env_file():
    """Validate .env.production syntax without executing."""
    env_file = Path(".env.production")

    if not env_file.exists():
        print("❌ .env.production not found!")
        return False

    # Valid pattern: KEY=value (value can be empty)
    valid_pattern = re.compile(r"^[A-Z0-9_]+=.*$")
    bad_lines = []

    for idx, line in enumerate(env_file.read_text().splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if not valid_pattern.match(line):
            bad_lines.append((idx, line))

    if bad_lines:
        print("❌ Invalid .env.production syntax:\n")
        for line_no, content in bad_lines:
            print(f"   Line {line_no}: {content[:80]}")
        return False

    print("✅ Environment syntax validation passed")
    return True


def validate_required_vars():
    """Check required variables exist (empty values are OK for optional vars)."""
    from dotenv import load_dotenv
    import os

    load_dotenv(".env.production")

    # Required variables (must have non-empty values)
    required = [
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_WHATSAPP_FROM",
        "ALERT_WHATSAPP_RECIPIENTS",
        "API_KEY",
    ]

    # Optional variables (can be empty)
    optional_with_defaults = [
        "TWILIO_SMS_FROM",
        "ALERT_SMS_RECIPIENTS",
        "ENABLE_WHATSAPP",
        "ENABLE_SMS",
        "ENABLE_EMAIL",
    ]

    missing = []
    for var in required:
        value = os.getenv(var)
        if not value or value.strip() == "":
            missing.append(var)

    if missing:
        print(f"❌ Missing required variables: {', '.join(missing)}")
        return False

    # Check optional variables (warn but don't fail)
    for var in optional_with_defaults:
        value = os.getenv(var)
        if not value or value.strip() == "":
            print(f"⚠️  Optional variable {var} not set (using default)")

    print("✅ Required variables present")
    return True


def validate_twilio_format():
    """Validate Twilio credential formats."""
    from dotenv import load_dotenv
    import os

    load_dotenv(".env.production")

    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    whatsapp_from = os.getenv("TWILIO_WHATSAPP_FROM", "")
    whatsapp_to = os.getenv("ALERT_WHATSAPP_RECIPIENTS", "")

    issues = []

    if account_sid and not account_sid.startswith("AC"):
        issues.append("TWILIO_ACCOUNT_SID should start with 'AC'")

    if auth_token and len(auth_token) < 30:
        issues.append("TWILIO_AUTH_TOKEN seems too short")

    if whatsapp_from and not whatsapp_from.startswith("whatsapp:"):
        issues.append("TWILIO_WHATSAPP_FROM should start with 'whatsapp:'")

    if whatsapp_to and not whatsapp_to.startswith("whatsapp:"):
        issues.append("ALERT_WHATSAPP_RECIPIENTS should start with 'whatsapp:'")

    if issues:
        print("⚠️  Format suggestions (not blocking):")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("✅ Twilio credentials format looks good")

    return True


if __name__ == "__main__":
    print("=" * 60)
    print("NFCC Environment Validation")
    print("=" * 60)

    # Run validations
    if not validate_env_file():
        sys.exit(1)

    if not validate_required_vars():
        sys.exit(1)

    validate_twilio_format()

    print("\n✅ Environment is ready for production")
    sys.exit(0)
