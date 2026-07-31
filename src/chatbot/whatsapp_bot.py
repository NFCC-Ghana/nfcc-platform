"""CiviSenti WhatsApp chatbot logic for community flood reporting.

This module handles incoming WhatsApp-style webhook payloads and converts
them into structured community flood reports.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

FLOOD_KEYWORDS = {
    "flood",
    "flooding",
    "rain",
    "overflow",
    "water",
    "submerged",
    "blocked",
    "drain",
    "drainage",
}

SEVERITY_KEYWORDS = {
    "LOW": {"small", "minor", "low", "ankle"},
    "MODERATE": {"moderate", "medium", "knee", "blocked"},
    "HIGH": {"high", "waist", "danger", "severe", "road blocked"},
    "CRITICAL": {"critical", "trapped", "emergency", "rescue", "life"},
}


@dataclass
class MediaAttachment:
    """Metadata for an incoming WhatsApp media attachment."""

    url: str
    content_type: str
    stored_path: Optional[str] = None


@dataclass
class CommunityFloodReport:
    """Structured community flood report from WhatsApp."""

    report_id: str
    reporter_phone: str
    message: str
    location_text: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    severity: str
    media: List[MediaAttachment] = field(default_factory=list)
    status: str = "received"
    satellite_validation: str = "pending"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["media"] = [asdict(item) for item in self.media]
        return data


class CiviSentiWhatsAppBot:
    """Parse incoming WhatsApp reports and generate bot responses."""

    def parse_incoming_payload(self, payload: Dict[str, Any]) -> CommunityFloodReport:
        """Convert a Twilio-style WhatsApp webhook payload into a report."""

        body = str(payload.get("Body", "")).strip()
        reporter_phone = str(payload.get("From", "")).replace("whatsapp:", "")

        latitude = self._to_float(payload.get("Latitude"))
        longitude = self._to_float(payload.get("Longitude"))

        location_text = self._extract_location_text(body)
        severity = self._infer_severity(body)
        media = self._extract_media(payload)

        return CommunityFloodReport(
            report_id=f"civisenti-{uuid.uuid4().hex[:12]}",
            reporter_phone=reporter_phone,
            message=body,
            location_text=location_text,
            latitude=latitude,
            longitude=longitude,
            severity=severity,
            media=media,
        )

    def validate_report(self, report: CommunityFloodReport) -> Dict[str, Any]:
        """Validate whether the incoming report has enough information."""

        issues = []

        if not report.message and not report.media:
            issues.append("Report must include a message or photo.")

        if not self._mentions_flood(report.message):
            issues.append("Message does not clearly mention flooding.")

        if report.latitude is None or report.longitude is None:
            issues.append("GPS location is missing.")

        if report.media:
            report.status = "validated"
        elif not issues:
            report.status = "validated"
        else:
            report.status = "needs_more_info"

        return {
            "valid": len(issues) == 0,
            "status": report.status,
            "issues": issues,
        }

    def build_reply(
        self, report: CommunityFloodReport, validation: Dict[str, Any]
    ) -> str:
        """Build WhatsApp reply text for the reporter."""

        if validation["valid"]:
            return (
                "Thank you. Your flood report has been received by CiviSenti.\n\n"
                f"Report ID: {report.report_id}\n"
                f"Severity: {report.severity}\n"
                "NFCC will review this report with available satellite/rainfall data."
            )

        missing = "\n".join(f"- {issue}" for issue in validation["issues"])
        return (
            "Thank you for contacting CiviSenti. "
            "We need a little more information before submitting the report.\n\n"
            f"{missing}\n\n"
            "Please send your location and describe the flooding level."
        )

    def _mentions_flood(self, text: str) -> bool:
        lowered = text.lower()
        return any(keyword in lowered for keyword in FLOOD_KEYWORDS)

    def _infer_severity(self, text: str) -> str:
        lowered = text.lower()

        for severity, keywords in SEVERITY_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                return severity

        if self._mentions_flood(text):
            return "MODERATE"

        return "UNKNOWN"

    def _extract_location_text(self, text: str) -> Optional[str]:
        patterns = [
            r"(?:at|around|near|in)\s+([A-Za-z0-9\s\-_,]+)",
            r"location[:\-]\s*([A-Za-z0-9\s\-_,]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_media(self, payload: Dict[str, Any]) -> List[MediaAttachment]:
        media_items = []
        media_count = int(payload.get("NumMedia", 0) or 0)

        for index in range(media_count):
            media_url = payload.get(f"MediaUrl{index}")
            content_type = payload.get(f"MediaContentType{index}", "")

            if media_url:
                media_items.append(
                    MediaAttachment(url=media_url, content_type=content_type)
                )

        return media_items

    def _to_float(self, value: Any) -> Optional[float]:
        if value in (None, ""):
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None
