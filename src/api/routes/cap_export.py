"""Real OASIS Common Alerting Protocol (CAP) v1.2 XML export for the Alert
Review Queue.

Every field this app already computes for a reviewer (severity/urgency/
certainty in src/api/routes/alert_review.py, real affected_communities from
src/exposure/community_names.py, JMA-style response_guidance) maps directly
onto CAP's own schema - this endpoint doesn't invent new data, it just
serializes what pending_alerts already stores into the exact XML schema
FEMA IPAWS, the EU, Japan, and Canada's NAAD all consume. That means an
alert from this system could be handed to any real CAP-compliant
distributor without a bespoke integration.

Uses cap-tools (typed dataclass bindings for the CAP 1.2 schema, built on
xsdata for serialization) rather than hand-built XML strings/f-strings,
which would be easy to get subtly wrong (attribute vs. element, namespace,
enumerated value spelling) in a format other systems parse strictly.

Exporting has no side effects - it never calls AlertEngine and doesn't
change a pending_alerts row's status. It reflects whatever status the row
already has: a plain assessment or an approved send exports as CAP
msgType=Alert; a retraction (src/api/routes/alert_review.py's /cancel,
itself CAP msgType=Cancel) exports as msgType=Cancel with a `references`
field pointing back at the original alert's identifier, per CAP's own
retraction model.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import cap_tools as cap
from fastapi import APIRouter, HTTPException, Response
from xsdata.formats.dataclass.serializers import XmlSerializer
from xsdata.formats.dataclass.serializers.config import SerializerConfig
from xsdata.models.datatype import XmlDateTime

from src.config.settings import settings
from src.database.alert_db import get_pending_alert

logger = logging.getLogger("nfcc-api.cap-export")

router = APIRouter(prefix="/alerts", tags=["alert-review"])

_CAP_NAMESPACE = "urn:oasis:names:tc:emergency:cap:1.2"

# Matches src/alerts/providers/email_provider.py's own existing default
# identity ("alerts@nfcc.com" / "NFCC Flood Alert System") - reusing it here
# rather than inventing a second identity, and deliberately NOT a real
# ghana.gov.gh address: this is a hackathon prototype (Ghana AI Innovation
# Challenge 2026), not an authorized government alerting system, and a CAP
# `sender` claiming otherwise would misrepresent that.
_CAP_SENDER = "alerts@nfcc.com"

# Our severity/urgency/certainty strings (src/api/routes/alert_review.py)
# were deliberately chosen to already be exact CAP vocabulary, so these are
# straight lookups, not a translation layer - "Unknown" is CAP's own
# defined fallback for a value this row never computed (e.g. rows saved
# before severity/urgency/certainty existed).
_SEVERITY_MAP = {s.value: s for s in cap.Severity}
_URGENCY_MAP = {u.value: u for u in cap.Urgency}
_CERTAINTY_MAP = {c.value: c for c in cap.Certainty}

# JMA-style response_guidance (src/api/routes/alert_review.py) already says
# WHO should act in prose; CAP's own responseType enum is the closest
# structured equivalent a CAP-consuming system can act on programmatically.
_RESPONSE_TYPE_BY_TIER = {
    "EXTREME": cap.ResponseType.EVACUATE,
    "CRITICAL": cap.ResponseType.EVACUATE,
    "HIGH": cap.ResponseType.PREPARE,
    "MODERATE": cap.ResponseType.MONITOR,
}


def _parse_timestamp(value: str) -> XmlDateTime:
    """pending_alerts stores created_at/reviewed_at via
    datetime.now().isoformat() - naive, no UTC offset. CAP requires an
    explicit offset; Cloud Run's runtime clock is UTC, so naive timestamps
    are treated as UTC rather than silently guessing a local offset."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return XmlDateTime.from_datetime(dt)


def _build_cap_alert(pending: dict) -> cap.Alert:
    alert_id = pending["id"]
    is_cancel = pending["status"] == "cancelled"
    is_exercise = pending.get("cap_status") == "Exercise"

    communities = pending.get("affected_communities") or []
    area_desc = ", ".join(communities) if communities else pending["location"]

    severity = pending.get("severity")
    identifier = f"NFCC-{alert_id}-{'CANCEL' if is_cancel else 'ALERT'}"
    sent_source = pending.get("reviewed_at") or pending["created_at"]

    info = cap.Info(
        categories=[cap.Category.MET],
        event="Flood Warning",
        response_types=[
            _RESPONSE_TYPE_BY_TIER.get(pending["risk_tier"], cap.ResponseType.MONITOR)
        ],
        urgency=_URGENCY_MAP.get(pending.get("urgency"), cap.Urgency.UNKNOWN),
        severity=_SEVERITY_MAP.get(severity, cap.Severity.UNKNOWN),
        certainty=_CERTAINTY_MAP.get(pending.get("certainty"), cap.Certainty.UNKNOWN),
        sender_name=settings.APP_NAME,
        headline=f"{severity or pending['risk_tier']} flood risk - {pending['location']}",
        description=pending["message"],
        instruction=pending.get("response_guidance"),
        effective=_parse_timestamp(pending["created_at"]),
        areas=[cap.Area(area_desc=area_desc)],
    )

    references: Optional[str] = None
    if is_cancel:
        # CAP's own format for referencing the message being cancelled:
        # "sender,identifier,sent" of the ORIGINAL alert.
        original_sent = _parse_timestamp(pending["created_at"])
        references = f"{_CAP_SENDER},NFCC-{alert_id}-ALERT,{original_sent}"

    return cap.Alert(
        identifier=identifier,
        sender=_CAP_SENDER,
        sent=_parse_timestamp(sent_source),
        status=cap.Status.EXERCISE if is_exercise else cap.Status.ACTUAL,
        msg_type=cap.MsgType.CANCEL if is_cancel else cap.MsgType.ALERT,
        scope=cap.Scope.PUBLIC,
        references=references,
        infos=[info],
    )


@router.get("/pending/{alert_id}/cap.xml")
async def export_cap_xml(alert_id: int):
    """Real OASIS CAP v1.2 XML for one review-queue alert - read-only, no
    side effects, safe to call regardless of the alert's status."""
    pending = get_pending_alert(alert_id)
    if pending is None:
        raise HTTPException(status_code=404, detail=f"No pending alert #{alert_id}")

    alert = _build_cap_alert(pending)
    config = SerializerConfig(pretty_print=True)
    xml = XmlSerializer(config=config).render(alert, ns_map={None: _CAP_NAMESPACE})

    return Response(content=xml, media_type="application/cap+xml")
