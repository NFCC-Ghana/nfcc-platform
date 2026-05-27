#!/usr/bin/env python3
"""Test email with new app password."""

import smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

# Load environment
load_dotenv(".env.production")

SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
RECIPIENT = os.getenv("ALERT_EMAIL_RECIPIENTS")

print("=" * 50)
print("Testing Gmail SMTP with New App Password")
print("=" * 50)
print(f"From: {SMTP_USER}")
print(f"To: {RECIPIENT}")
print(f"Password: {'*' * 8}{SMTP_PASSWORD[-4:] if SMTP_PASSWORD else 'NOT SET'}")
print("")

# Create message
msg = MIMEText("""
🧪 NFCC TEST MESSAGE

This is a test from your NFCC Flood Alert Platform.

If you receive this, your Gmail app password is working correctly!

Time: Test Message
""")

msg["Subject"] = "NFCC Test - App Password Working"
msg["From"] = SMTP_USER
msg["To"] = RECIPIENT

try:
    print("📧 Connecting to Gmail SMTP...")
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        print("🔐 Logging in...")
        server.login(SMTP_USER, SMTP_PASSWORD)
        print("📤 Sending email...")
        server.send_message(msg)

    print("\n✅ SUCCESS! Email sent!")
    print("📱 Check your phone - you should receive an SMS in 30-60 seconds")

except smtplib.SMTPAuthenticationError as e:
    print(f"\n❌ Authentication Failed: {e}")
    print("\nPossible causes:")
    print("1. App password is incorrect (copy exactly with spaces)")
    print("2. 2-Step Verification is not enabled")
    print("3. App password was revoked")
    print("\nSolution: Generate a new app password at:")
    print("https://myaccount.google.com/apppasswords")

except Exception as e:
    print(f"\n❌ Error: {e}")

print("\n" + "=" * 50)
