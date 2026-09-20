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
status. TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN already exist as Cloud Run
secrets (added for outbound alerting) and are reused here for inbound
signature verification only - no new secret needed.

Message format is deliberately forgiving, not a rigid schema: citizens
were never told an exact format, so free text is parsed best-effort for a
known district/community name, a report type, an optional depth
("Alajo - water rising on the main road, knee-deep, about 40cm"), and an
urgency level. A message with no recognizable place name is still saved
(never silently dropped) under a district of "Unclassified - needs
triage" so a human can reclassify it via GET/POST
src/api/v1/community_reports.py - deliberately NOT guessed or fuzzy-
matched to a nearby district, since misfiling a real report to the wrong
district is worse than leaving it for a human to fix. Latitude/longitude
are captured directly from Twilio's own fields when a citizen shares
their live WhatsApp location, which is a far more reliable signal than
text matching when present.

This replaces an earlier prototype (src/chatbot/whatsapp_bot.py +
scripts/civisenti_handler.py + .github/workflows/civisenti.yml, removed)
that was never actually wired to a live endpoint - only ever invoked
manually or by a daily cron summarizing an always-empty JSONL file with
no real intake path of its own. Its two genuinely useful ideas - GPS
capture and urgency-keyword detection ("trapped"/"rescue" language) -
are folded in here; its separate, non-Litestream-replicated JSONL
storage was not, since community_memory.py's SQLite table is the one
every other real consumer (situation.py's report stats, the outcome
verifier) already reads.
"""

import logging
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from src.community.community_memory import community_memory
from src.config.settings import settings
from src.exposure.community_names import DISTRICT_COMMUNITIES

logger = logging.getLogger("nfcc-api.whatsapp-webhook")

router = APIRouter(prefix="/webhooks", tags=["whatsapp"])

# lowercase name -> canonical district, for the district names themselves
# AND every community under them (e.g. "kaneshie" -> "Accra Central").
_LOCATION_LOOKUP: dict = {}
for _district, _communities in DISTRICT_COMMUNITIES.items():
    _LOCATION_LOOKUP[_district.lower()] = _district
    for _c in _communities:
        _LOCATION_LOOKUP[_c.lower()] = _district
# Longest terms first so "tema community 1" matches before a bare "tema".
_LOCATION_TERMS = sorted(_LOCATION_LOOKUP.keys(), key=len, reverse=True)

_TYPE_KEYWORDS = [
    (("drain", "gutter", "culvert"), "Drainage Blocked"),
    (("rising", "rise", "increasing"), "Water Level Rising"),
    (("warn", "expect", "forecast"), "Weather Warning"),
    (("yesterday", "last night", "this morning", "earlier"), "Recent Flood"),
]

# Urgency keywords - folded in from an earlier, never-wired-live
# prototype (src/chatbot/whatsapp_bot.py, removed in favor of this real
# integration) whose one genuinely good idea was flagging "trapped" /
# "rescue" language as a distinct, more urgent signal than ordinary
# flooding language - worth a human reviewer seeing immediately.
_URGENCY_KEYWORDS = [
    (("trapped", "rescue", "emergency", "life", "dying", "help us"), "CRITICAL"),
    (("waist", "danger", "severe", "cannot leave", "stranded"), "HIGH"),
    (("ankle", "minor", "small", "low"), "LOW"),
]

_DEPTH_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(cm|centimet\w*|m\b|met(?:er|re)s?)", re.IGNORECASE)


def _extract_location(text: str) -> tuple:
    """Exact (case-insensitive) match only - no fuzzy guessing. Word-
    boundary matching, not substring: a raw substring check would let
    the district "Ho" match inside "house", or "Dome" (a Ho community)
    match inside "domestic" - both real false positives caught in
    testing. Returns (district, community); community is None if only a
    district matched."""
    lowered = text.lower()
    for term in _LOCATION_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", lowered):
            district = _LOCATION_LOOKUP[term]
            community = None if term == district.lower() else term.title()
            return district, community
    return None, None


def _extract_report_type(text: str) -> str:
    lowered = text.lower()
    for keywords, label in _TYPE_KEYWORDS:
        if any(k in lowered for k in keywords):
            return label
    return "Active Flooding"


def _extract_urgency(text: str) -> str:
    lowered = text.lower()
    for keywords, label in _URGENCY_KEYWORDS:
        if any(k in lowered for k in keywords):
            return label
    return "MODERATE"


def _to_float(value) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_depth_m(text: str) -> Optional[float]:
    match = _DEPTH_RE.search(text)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2).lower()
    if unit.startswith("cm") or unit.startswith("centimet"):
        return round(value / 100, 2)
    return value


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
    latitude = _to_float(form_dict.get("Latitude"))
    longitude = _to_float(form_dict.get("Longitude"))

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
            "cars can't pass'.\nYou can attach a photo."
        )

    district, community = _extract_location(body)
    urgency = _extract_urgency(body)

    report_data = {
        "district": district or "Unclassified - needs triage",
        "community": community or "Unspecified",
        "report_type": _extract_report_type(body),
        "description": body,
        "flood_depth_m": _extract_depth_m(body),
        "photo_url": photo_url,
        "reporter_name": profile_name,
        "reporter_phone": from_number,
        "latitude": latitude,
        "longitude": longitude,
        "urgency": urgency,
    }

    try:
        result = community_memory.submit_report(report_data)
    except Exception:
        logger.exception("Failed to save WhatsApp community report")
        return _twiml("Sorry, we couldn't save your report right now. Please try again shortly.")

    log_level = logger.warning if urgency == "CRITICAL" else logger.info
    log_level(
        "WhatsApp report saved: id=%s district=%s community=%s urgency=%s gps=%s from=%s",
        result.get("report_id"), report_data["district"], report_data["community"],
        urgency, bool(latitude and longitude), from_number,
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
