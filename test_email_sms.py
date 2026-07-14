#!/usr/bin/env python3
"""Test email-to-SMS with your actual credentials."""

import os
import smtplib
from email.mime.text import MIMEText

# Your credentials (loaded from .env.production)
from dotenv import load_dotenv

load_dotenv(".env.production")

SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
RECIPIENT = os.getenv("ALERT_EMAIL_RECIPIENTS")

print("=" * 50)
print("Testing Email-to-SMS System")
print("=" * 50)
print(f"From: {SMTP_USER}")
print(f"To (SMS): {RECIPIENT}")
print("")

# Create message
msg = MIMEText("""
🧪 NFCC FLOOD ALERT SYSTEM TEST

This is a test message from your NFCC platform.

If you receive this as an SMS, the email-to-SMS gateway is working!

Your flood alert system is now fully operational.

Timestamp: Test Message
""")

msg["Subject"] = "NFCC Test Alert - SMS via Email"
msg["From"] = SMTP_USER
msg["To"] = RECIPIENT

try:
    # Send email
    print("📧 Sending email to SMS gateway...")
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)

    print("✅ Email sent successfully!")
    print("📱 Check your phone - you should receive an SMS in 30-60 seconds")

except Exception as e:
    print(f"❌ Failed: {e}")
    print("\nTroubleshooting:")
    print("1. Check your email address in SMTP_USER")
    print("2. Verify app password is correct (spaces matter)")
    print("3. Ensure 2FA is enabled on your Gmail")
