"""Inbound Telegram citizen flood-reporting webhook.

A second intake channel alongside src/api/routes/whatsapp_webhook.py,
added because Telegram's Bot API has no trial/billing restriction of any
kind, anywhere - unlike Twilio, whose Ghana-registered account had zero
free units for everything and whose second account's WhatsApp Sandbox,
while free to use, still requires a citizen to first text a join code to
a shared US number (real friction). A Telegram bot has no such step: a
citizen searches the bot's username and starts chatting immediately.

Shares its parsing logic (district/community/report-type/depth/urgency)
with whatsapp_webhook.py via src/community/report_parsing.py, so a report
saying "Kaneshie flooding, 40cm" classifies identically regardless of
which channel it arrived on.

Auth: Telegram has no request-signing scheme like Twilio's X-Twilio-
Signature. Instead, setWebhook's secret_token parameter (set once,
manually, when registering this URL with Telegram - see this module's
docstring in docs or the deploy notes) makes Telegram echo that same
string back on every webhook call via X-Telegram-Bot-Api-Secret-Token;
this app rejects any request where it doesn't match.

Replying: unlike Twilio's inline TwiML response, this makes a normal
outbound HTTPS call to Telegram's sendMessage API - Telegram has no
billing tier where this behaves differently, so there's no reason to use
Telegram's alternate "answer via webhook response body" mechanism.
"""

import logging

from fastapi import APIRouter, HTTPException, Request

from src.alerts.providers.telegram_provider import send_telegram_message
from src.community.alert_subscription_commands import handle_subscription_command
from src.community.community_memory import community_memory
from src.community.report_parsing import build_report_data, to_float
from src.config.settings import settings

logger = logging.getLogger("nfcc-api.telegram-webhook")

router = APIRouter(prefix="/webhooks", tags=["telegram"])

_HELP_TEXT = (
    "NFCC Flood Reporting. Send your community name and what you're "
    "seeing, e.g.:\n'Kaneshie - flooding on market road, cars can't "
    "pass'.\nYou can also share your location (paperclip > Location) or "
    "a photo.\nSend 'ALERTS ON' to receive flood warnings for your area."
)


def _send_message(chat_id, text: str) -> None:
    """Thin wrapper for logging only - the actual HTTP call is shared
    with the outbound alert path (src/alerts/providers/
    telegram_provider.py's send_telegram_message), one place that knows
    how to call Telegram's sendMessage API."""
    result = send_telegram_message(chat_id, text)
    if not result.get("success"):
        logger.warning("Failed to send Telegram reply to chat_id=%s: %s", chat_id, result)


@router.post("/telegram")
async def telegram_inbound(request: Request) -> dict:
    if settings.TELEGRAM_WEBHOOK_SECRET:
        secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if secret != settings.TELEGRAM_WEBHOOK_SECRET:
            logger.warning("Rejected Telegram webhook: invalid secret token")
            raise HTTPException(status_code=403, detail="Invalid secret token")
    else:
        logger.warning(
            "TELEGRAM_WEBHOOK_SECRET not configured - accepting Telegram "
            "webhook WITHOUT verification (dev-mode only)"
        )

    update = await request.json()
    message = update.get("message") or update.get("edited_message")
    if not message:
        # Non-message update (e.g. a channel post, a poll answer) - not a
        # citizen report, nothing to do, but still acknowledge so
        # Telegram doesn't retry.
        return {"ok": True}

    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    reporter_name = (
        " ".join(filter(None, [from_user.get("first_name"), from_user.get("last_name")]))
        or from_user.get("username")
        or None
    )
    reporter_id = f"telegram:{from_user.get('id', 'unknown')}"

    body = (message.get("text") or message.get("caption") or "").strip()
    location = message.get("location")
    latitude = to_float(location.get("latitude")) if location else None
    longitude = to_float(location.get("longitude")) if location else None

    photo_url = None
    if message.get("photo"):
        # Largest variant is last in Telegram's size-ordered list. This
        # is a file_id, not a public URL - resolving it to bytes requires
        # a separate getFile call, deferred until an operator actually
        # needs to view it (same deferred-resolution tradeoff as storing
        # Twilio's MediaUrl0 directly).
        photo_url = f"telegram_file_id:{message['photo'][-1]['file_id']}"

    if body.lower() in ("/start", "/help", "help", "menu"):
        _send_message(chat_id, _HELP_TEXT)
        return {"ok": True}

    subscription_reply = handle_subscription_command("telegram", str(chat_id), body)
    if subscription_reply is not None:
        _send_message(chat_id, subscription_reply)
        return {"ok": True}

    if not body and not location:
        _send_message(
            chat_id,
            "We didn't receive any text or location. Please tell us your "
            "community name and what you're seeing, e.g. 'Alajo - water "
            "rising on the main road, knee-deep'.",
        )
        return {"ok": True}

    report_data = build_report_data(
        body=body or "(location shared, no text)",
        reporter_phone=reporter_id,
        reporter_name=reporter_name,
        photo_url=photo_url,
        latitude=latitude,
        longitude=longitude,
    )
    district = report_data["district"] if report_data["district"] != "Unclassified - needs triage" else None
    community = report_data["community"] if report_data["community"] != "Unspecified" else None
    urgency = report_data["urgency"]

    try:
        result = community_memory.submit_report(report_data)
    except Exception:
        logger.exception("Failed to save Telegram community report")
        _send_message(chat_id, "Sorry, we couldn't save your report right now. Please try again shortly.")
        return {"ok": True}

    log_level = logger.warning if urgency == "CRITICAL" else logger.info
    log_level(
        "Telegram report saved: id=%s district=%s community=%s urgency=%s gps=%s from=%s",
        result.get("report_id"), report_data["district"], report_data["community"],
        urgency, bool(latitude and longitude), reporter_id,
    )

    if district:
        where = f"{community} ({district})" if community else district
        confirmation = (
            f"Report received for {where}. Thank you for helping keep "
            f"your community safe. Ref: {result.get('report_id')}"
        )
    else:
        confirmation = (
            "Report received and flagged for review - we couldn't "
            "automatically detect your district. A team member may "
            f"follow up. Ref: {result.get('report_id')}"
        )

    if urgency == "CRITICAL":
        confirmation = (
            "This sounds urgent - if anyone is in immediate danger, please "
            "also call your local emergency services now. " + confirmation
        )

    _send_message(chat_id, confirmation)
    return {"ok": True}
