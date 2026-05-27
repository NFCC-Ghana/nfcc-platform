"""Async tasks for Celery worker."""

import logging
from typing import Dict, Any

logger = logging.getLogger("nfcc.tasks")

# Try to import Celery, but don't fail if not installed
try:
    from src.celery_app import celery

    @celery.task(
        bind=True,
        autoretry_for=(Exception,),
        retry_backoff=True,
        retry_backoff_max=300,
        retry_jitter=True,
        retry_kwargs={"max_retries": 5},
        name="send_whatsapp_alert",
    )
    def send_whatsapp_alert(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send WhatsApp alert asynchronously."""
        from src.alerts.providers.whatsapp_provider import WhatsAppAlertProvider
        from src.alerts.models import AlertPayload

        logger.info(f"Processing async alert for {payload.get('location')}")

        provider = WhatsAppAlertProvider()
        alert = AlertPayload(**payload)
        result = provider.send(alert)

        if not result.get("success"):
            raise Exception(f"Failed to send: {result.get('message')}")

        return result

    CELERY_AVAILABLE = True
    print("✅ Celery tasks registered")

except ImportError:
    # Celery not installed - create no-op fallback
    CELERY_AVAILABLE = False

    def send_whatsapp_alert(payload):
        """Synchronous fallback when Celery not available."""
        from src.alerts.providers.whatsapp_provider import WhatsAppAlertProvider
        from src.alerts.models import AlertPayload

        logger.warning("Celery not available - sending synchronously")
        provider = WhatsAppAlertProvider()
        alert = AlertPayload(**payload)
        return provider.send(alert)

    print("⚠️  Celery not installed - using synchronous sends")
