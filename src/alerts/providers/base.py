"""Base alert provider interface - imports AlertPayload from models."""

from abc import ABC, abstractmethod
from typing import Dict, Any

# Import from models - SINGLE SOURCE OF TRUTH
from src.alerts.models import AlertPayload


class BaseAlertProvider(ABC):
    """Abstract base class for all alert providers."""

    name: str = "base"

    @abstractmethod
    def send(self, payload: AlertPayload) -> Dict[str, Any]:
        """Send an alert payload.

        Args:
            payload: AlertPayload object (from models.py)

        Returns:
            Dict with at minimum: {"success": bool, "provider": str}
        """
        pass

    def validate_payload(self, payload: AlertPayload) -> bool:
        """Validate payload before sending."""
        if not isinstance(payload, AlertPayload):
            raise TypeError(f"Expected AlertPayload, got {type(payload)}")
        return True
