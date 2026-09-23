"""Inbound WhatsApp citizen flood-reporting webhook (Twilio).

Citizen reporting (src/community/community_memory.py) has existed since
early in this project but had zero real intake path - the only way a row
ever landed in reports.db was a manual API call or the disabled Streamlit
form (hackathon/app/pages_disabled/04_community_report.py). This is the
first real, always-on intake channel: a citizen messages the project's
Twilio WhatsApp number, and the message becomes a row here without any
human operator involved.

No new billing required: Twilio's WhatsApp Sandbox (and a production
WhatsApp sender once approved) charges for messages the platform SENDS,
not for inbound messages received or the same-request TwiML reply sent
back in response to them - both are free regardless of account funding
status. This was confirmed against a real account: a first Twilio
account showed 0 free units for everything (Ghana isn't eligible for
Twilio trials at all), but a second account's WhatsApp Sandbox - a
shared Twilio developer testing number every account can join via a
join-code text, requiring no payment or WhatsApp Business approval -
worked normally. TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN are reused here
(from whichever account is actually wired up) for inbound signature
verification only - no new secret needed.

Message parsing (district/community/report-type/depth/urgency) lives in
src/community/report_parsing.py, shared with
src/api/routes/telegram_webhook.py - a second, always-free intake
channel added alongside this one so citizen reporting doesn't depend on
Twilio's billing status at all.

This replaces an earlier prototype (src/chatbot/whatsapp_bot.py +
scripts/civisenti_handler.py + .github/workflows/civisenti.yml, removed)
that was never actually wired to a live endpoint - only ever invoked
manually or by a daily cron summarizing an always-empty JSONL file with
no real intake path of its own. Its two genuinely useful ideas - GPS
capture and urgency-keyword detection ("trapped"/"rescue" language) -
were folded into report_parsing.py; its separate, non-Litestream-
replicated JSONL storage was not, since community_memory.py's SQLite
table is the one every other real consumer (situation.py's report
stats, the outcome verifier) already reads.
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from src.community.alert_subscription_commands import handle_subscription_command
from src.community.community_memory import community_memory
from src.community.report_parsing import build_report_data, to_float
from src.config.settings import settings

logger = logging.getLogger("nfcc-api.whatsapp-webhook")

router = APIRouter(prefix="/webhooks", tags=["whatsapp"])


def _twiml(message: str) -> Response:
    resp = MessagingResponse()
    resp.message(message)
    return Response(content=str(resp), media_type="application/xml")


@router.post("/whatsapp")
async def whatsapp_inbound(request: Request) -> Response:
    form = await request.form()
    form_dict = dict(form)

    if settings.TWILIO_AUTH_TOKEN:
        signature = request.headers.get("X-Twilio-Signature", "")
        # Cloud Run terminates TLS at its edge and forwards to this
        # container over plain HTTP, so request.url reports scheme
        # "http" even though Twilio only ever calls the public https://
        # URL - force https so validation checks the URL Twilio signed.
        validation_url = str(request.url).replace("http://", "https://", 1)
        validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
        if not validator.validate(validation_url, form_dict, signature):
            logger.warning("Rejected WhatsApp webhook: invalid Twilio signature")
            raise HTTPException(status_code=403, detail="Invalid signature")
    else:
        logger.warning(
            "TWILIO_AUTH_TOKEN not configured - accepting WhatsApp webhook "
            "WITHOUT signature verification (dev-mode only)"
        )

    from_number = str(form_dict.get("From", "")).replace("whatsapp:", "")
    body = str(form_dict.get("Body", "")).strip()
    profile_name = form_dict.get("ProfileName") or None
    num_media = int(form_dict.get("NumMedia", 0) or 0)
    photo_url = form_dict.get("MediaUrl0") if num_media > 0 else None
    # Twilio's real field names when a WhatsApp user shares their live
    # location (not just typed text) - a far more reliable signal than
    # text district-matching when present.
    latitude = to_float(form_dict.get("Latitude"))
    longitude = to_float(form_dict.get("Longitude"))

    if not body:
        return _twiml(
            "We didn't receive any text. Please reply with your community "
            "name and what you're seeing, e.g. 'Alajo - water rising on "
            "the main road, knee-deep'."
        )

    if body.lower() in ("help", "menu", "info"):
        return _twiml(
            "NFCC Flood Reporting. Reply with your community name and what "
            "you're seeing, e.g.:\n'Kaneshie - flooding on market road, "
            "cars can't pass'.\nYou can attach a photo.\nReply 'ALERTS ON' "
            "to receive flood warnings for your area."
        )

    subscription_reply = handle_subscription_command("whatsapp", from_number, body)
    if subscription_reply is not None:
        return _twiml(subscription_reply)

    report_data = build_report_data(
        body=body,
        reporter_phone=from_number,
        reporter_name=profile_name,
        photo_url=photo_url,
        latitude=latitude,
        longitude=longitude,
    )
    district = (
        report_data["district"]
        if report_data["district"] != "Unclassified - needs triage"
        else None
    )
    community = (
        report_data["community"] if report_data["community"] != "Unspecified" else None
    )
    urgency = report_data["urgency"]

    try:
        result = community_memory.submit_report(report_data)
    except Exception:
        logger.exception("Failed to save WhatsApp community report")
        return _twiml(
            "Sorry, we couldn't save your report right now. Please try again shortly."
        )

    log_level = logger.warning if urgency == "CRITICAL" else logger.info
    log_level(
        "WhatsApp report saved: id=%s district=%s community=%s urgency=%s gps=%s from=%s",
        result.get("report_id"),
        report_data["district"],
        report_data["community"],
        urgency,
        bool(latitude and longitude),
        from_number,
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

    return _twiml(confirmation)
