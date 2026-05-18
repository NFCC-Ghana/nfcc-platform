"""Base alert provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AlertPayload:
    """Alert payload containing all necessary information."""

    location: str
    risk_score: float
    risk_tier: str
    precipitation: float
    roll_3d: float
    z_score: float
    timestamp: str = ""
    message: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
        if not self.message:
            self.message = self._default_message()

    def _default_message(self) -> str:
        tier_emoji = {
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MODERATE": "🟡",
            "LOW": "🟢",
        }.get(self.risk_tier, "⚪")

        return (
            f"{tier_emoji} NFCC FLOOD ALERT\n"
            f"Location  : {self.location}\n"
            f"Risk Score: {self.risk_score:.1f} / 100\n"
            f"Risk Tier : {self.risk_tier}\n"
            f"Rainfall  : {self.precipitation:.1f} mm today\n"
            f"3-Day Tot : {self.roll_3d:.1f} mm\n"
            f"Z-Score   : {self.z_score:.2f}\n"
            f"Time      : {self.timestamp[:19].replace('T', ' ')} UTC\n"
            f"National Flood Control Centre, Accra, Ghana"
        )


class BaseAlertProvider(ABC):
    """Abstract base class for alert providers."""

    name: str = "base"

    @abstractmethod
    def send(self, payload: AlertPayload) -> dict:
        """Send alert. Returns dict with success status and provider info."""
        pass
