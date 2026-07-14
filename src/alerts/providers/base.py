"""Base alert provider interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict

from src.alerts.models import AlertPayload


class BaseAlertProvider(ABC):
    """Abstract base class for all alert providers."""

    name: str = "base"

    @abstractmethod
    def send(self, alert: AlertPayload) -> Dict[str, Any]:
        """Send an alert using this provider.

        Args:
            alert: The alert payload to send

        Returns:
            Dict with at minimum:
                - success: bool
                - message: str
                - provider: str
        """
        pass

    @abstractmethod
    def _format_message(self, alert: AlertPayload) -> str:
        """Format alert message for this provider."""
        pass
