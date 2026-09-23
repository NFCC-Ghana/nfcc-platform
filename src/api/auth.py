"""API authentication and security."""

import hmac

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

from src.config.settings import settings

# Rate limiting - the limiter object itself was already created here, but
# a security audit found zero `@limiter.limit(...)` call sites anywhere
# in src/ - it was imported and instantiated but never actually applied,
# leaving every endpoint (including ones that call paid/quota-limited
# Earth Engine and Gemini APIs) with no inbound request throttling at
# all. Now actually wired onto the app in main.py and applied to the
# expensive endpoints - see src/api/routes/situation.py and
# src/api/v1/copilot.py.
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """Verify API key for protected endpoints."""
    if not settings.API_KEY:
        return "development"

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing {settings.API_KEY_HEADER} header",
        )

    # hmac.compare_digest, not `!=` - a plain string comparison short-
    # circuits on the first mismatched byte, so response time leaks how
    # many leading characters of a guess were correct. compare_digest
    # runs in constant time regardless of where the strings first differ.
    if not hmac.compare_digest(api_key, settings.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key"
        )

    return api_key
