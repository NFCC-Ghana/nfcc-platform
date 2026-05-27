"""Singleton provider factory - prevents duplicate initialization."""

import logging
from typing import List, Optional

logger = logging.getLogger("nfcc.alert.factory")


class ProviderFactory:
    """Factory that creates providers once and caches them."""
    
    _providers = None
    
    @classmethod
    def get_providers(cls, provider_names: Optional[List[str]] = None) -> List:
        """Get or create providers."""
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
            provider_names = [name for name, enabled in status.items() if enabled] if any(status.values()) else ["mock"]
        
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
        
        cls._providers = providers
        return providers

    @classmethod
    def reset(cls):
        """Reset the factory cache (useful for testing)."""
        cls._providers = None
        logger.info("Provider factory reset")
