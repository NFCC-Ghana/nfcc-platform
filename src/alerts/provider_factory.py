"""Singleton provider factory - prevents duplicate initialization."""

import logging
from functools import lru_cache
from typing import List

logger = logging.getLogger("nfcc.alert.factory")


class ProviderFactory:
    """Factory that creates providers once and caches them."""

    _providers = None

    @classmethod
    @lru_cache(maxsize=1)
    def get_providers(cls, provider_names: List[str] = None) -> List:
        """Get or create providers - cached across calls."""
        if cls._providers is not None:
            return cls._providers

        from src.alerts.providers import (
            SMSAlertProvider,
            WhatsAppAlertProvider,
            EmailAlertProvider,
            MockAlertProvider,
        )
        from src.config.settings import settings

        provider_map = {
            "sms": lambda: SMSAlertProvider(),
            "whatsapp": lambda: WhatsAppAlertProvider(),
            "email": lambda: EmailAlertProvider(),
            "mock": lambda: MockAlertProvider(),
        }

        if provider_names is None:
            status = settings.get_provider_status()
            if any(status.values()):
                provider_names = [name for name, enabled in status.items() if enabled]
            else:
                provider_names = ["mock"]

        providers = []
        for name in provider_names:
            if name in provider_map:
                try:
                    provider = provider_map[name]()
                    providers.append(provider)
                    logger.info(f"✅ Initialized {name} provider")
                except Exception as e:
                    logger.error(f"Failed to initialize {name} provider: {e}")

        if not providers:
            providers.append(MockAlertProvider())
            logger.warning("No providers configured, using mock")

        cls._providers = providers
        return providers
