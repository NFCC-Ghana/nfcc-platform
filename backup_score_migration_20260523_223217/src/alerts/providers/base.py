from abc import ABC, abstractmethod
from typing import Dict, Any
from src.alerts.models import AlertPayload


class BaseAlertProvider(ABC):
    name: str = "base"

    @abstractmethod
    def send(self, payload: AlertPayload) -> Dict[str, Any]:
        pass
