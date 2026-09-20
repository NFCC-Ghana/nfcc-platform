"""Channel-agnostic free-text parsing for citizen flood reports.

Shared by src/api/routes/whatsapp_webhook.py and
src/api/routes/telegram_webhook.py so the district/community matching,
report-type inference, depth extraction, and urgency detection stay in
one place - both channels feed the same community_memory.py store and
should classify identical message text identically.

Message format is deliberately forgiving, not a rigid schema: citizens
were never told an exact format, so free text is parsed best-effort for
a known district/community name, a report type, an optional depth
("Alajo - water rising on the main road, knee-deep, about 40cm"), and an
urgency level. Text with no recognizable place name is deliberately left
unclassified rather than fuzzy-matched to a nearby district - misfiling a
real report to the wrong district is worse than leaving it for a human
to fix (see build_report_data's "Unclassified - needs triage" district).
"""

import re
from typing import Optional, Tuple

from src.exposure.community_names import DISTRICT_COMMUNITIES

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

# Urgency keywords - folded in from an earlier, never-wired-live prototype
# (src/chatbot/whatsapp_bot.py, removed) whose one genuinely good idea was
# flagging "trapped"/"rescue" language as a distinct, more urgent signal
# than ordinary flooding language - worth a human reviewer seeing
# immediately.
_URGENCY_KEYWORDS = [
    (("trapped", "rescue", "emergency", "life", "dying", "help us"), "CRITICAL"),
    (("waist", "danger", "severe", "cannot leave", "stranded"), "HIGH"),
    (("ankle", "minor", "small", "low"), "LOW"),
]

_DEPTH_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(cm|centimet\w*|m\b|met(?:er|re)s?)", re.IGNORECASE)


def extract_location(text: str) -> Tuple[Optional[str], Optional[str]]:
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


def extract_report_type(text: str) -> str:
    lowered = text.lower()
    for keywords, label in _TYPE_KEYWORDS:
        if any(k in lowered for k in keywords):
            return label
    return "Active Flooding"


def extract_urgency(text: str) -> str:
    lowered = text.lower()
    for keywords, label in _URGENCY_KEYWORDS:
        if any(k in lowered for k in keywords):
            return label
    return "MODERATE"


def extract_depth_m(text: str) -> Optional[float]:
    match = _DEPTH_RE.search(text)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2).lower()
    if unit.startswith("cm") or unit.startswith("centimet"):
        return round(value / 100, 2)
    return value


def to_float(value) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_report_data(
    *,
    body: str,
    reporter_phone: Optional[str] = None,
    reporter_name: Optional[str] = None,
    photo_url: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> dict:
    """Parse one inbound message's text into the dict shape
    community_memory.submit_report() expects - the one piece of logic
    every intake channel (WhatsApp, Telegram, ...) shares after
    extracting its own channel-specific envelope fields."""
    district, community = extract_location(body)
    return {
        "district": district or "Unclassified - needs triage",
        "community": community or "Unspecified",
        "report_type": extract_report_type(body),
        "description": body,
        "flood_depth_m": extract_depth_m(body),
        "photo_url": photo_url,
        "reporter_name": reporter_name,
        "reporter_phone": reporter_phone,
        "latitude": latitude,
        "longitude": longitude,
        "urgency": extract_urgency(body),
    }
