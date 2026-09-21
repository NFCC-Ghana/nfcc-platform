"""Production settings with explicit environment loading."""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

# ============================================================
# EXPLICIT ENVIRONMENT SELECTION - NO AMBIGUITY
# ============================================================
# Priority:
#   1. NFCC_ENV environment variable (highest priority)
#   2. ENVIRONMENT variable from .env file
#   3. Default to "development"

# First, check if NFCC_ENV is set in OS environment
NFCC_ENV = os.getenv("NFCC_ENV", "")

if NFCC_ENV:
    # NFCC_ENV takes highest priority
    ENVIRONMENT = NFCC_ENV
    print(f"🔧 Using NFCC_ENV={NFCC_ENV} from environment")
else:
    # Fallback to ENVIRONMENT variable
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    print(f"🔧 Using ENVIRONMENT={ENVIRONMENT} from config")

# Select the correct env file based on explicit environment
env_file_map = {
    "production": ".env.production",
    "development": ".env.development",
    "testing": ".env.testing",
}

env_file_name = env_file_map.get(ENVIRONMENT, ".env.development")
env_file = Path(env_file_name)

if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded configuration from {env_file}")
else:
    print(f"⚠️ Environment file {env_file} not found")

# Now reload environment variables after loading env file
ENVIRONMENT = os.getenv("ENVIRONMENT", ENVIRONMENT)
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")

print(f"🌍 FINAL ENVIRONMENT: {ENVIRONMENT}")
print(f"📋 LOG LEVEL: {LOG_LEVEL}")


def get_env_int(key: str, default: int = None) -> Optional[int]:
    value = os.getenv(key)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def get_env_bool(key: str, default: bool = False) -> bool:
    value = os.getenv(key)
    if value is None or value == "":
        return default
    return value.lower() in ["true", "1", "yes", "on"]


def get_env_list(key: str, default: List[str] = None) -> List[str]:
    if default is None:
        default = []
    value = os.getenv(key)
    if not value or value == "":
        return default
    return [v.strip() for v in value.split(",") if v.strip()]


class Settings:
    """Production settings with validation."""

    # Environment
    ENVIRONMENT: str = ENVIRONMENT
    LOG_LEVEL: str = LOG_LEVEL
    DEBUG: bool = ENVIRONMENT == "development"

    # API Configuration
    API_VERSION: str = "2.0.0"
    APP_NAME: str = "NFCC Flood Alert Platform"
    APP_DESCRIPTION: str = "Enterprise flood risk alert system"

    API_KEY: Optional[str] = os.getenv("API_KEY")
    if not API_KEY and ENVIRONMENT == "development":
        API_KEY = "dev-key-for-testing-only"

    API_KEY_HEADER: str = "X-API-Key"
    JWT_SECRET_KEY: Optional[str] = os.getenv("JWT_SECRET_KEY")
    # src/alerts/cooldown.py reads REDIS_URL directly via os.getenv (its
    # own lazy-connect logic needs the raw value, not this attribute) -
    # this copy exists only so GET /health's "configured" field can
    # report real presence instead of always False via
    # getattr(settings, "REDIS_URL", None), found during a codebase audit
    # to have never actually been a Settings attribute.
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = get_env_bool("RATE_LIMIT_ENABLED", False)
    RATE_LIMIT_REQUESTS: int = get_env_int("RATE_LIMIT_REQUESTS", 100) or 100
    RATE_LIMIT_PERIOD: int = get_env_int("RATE_LIMIT_PERIOD", 60) or 60

    # CORS
    ALLOWED_ORIGINS: List[str] = get_env_list(
        "ALLOWED_ORIGINS", ["http://localhost:3000", "http://localhost:8000"]
    )

    # Twilio WhatsApp
    TWILIO_ACCOUNT_SID: Optional[str] = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN: Optional[str] = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_WHATSAPP_FROM: str = os.getenv(
        "TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886"
    )

    WHATSAPP_RECIPIENTS: List[str] = get_env_list("ALERT_WHATSAPP_RECIPIENTS", [])

    if TWILIO_WHATSAPP_FROM and not TWILIO_WHATSAPP_FROM.startswith("whatsapp:"):
        TWILIO_WHATSAPP_FROM = f"whatsapp:{TWILIO_WHATSAPP_FROM}"

    WHATSAPP_MAX_RETRIES: int = get_env_int("WHATSAPP_MAX_RETRIES", 3) or 3
    WHATSAPP_RETRY_DELAY: float = float(
        os.getenv("WHATSAPP_RETRY_DELAY", "2.0") or "2.0"
    )

    # Twilio SMS (Disabled for trial)
    TWILIO_SMS_FROM: Optional[str] = os.getenv("TWILIO_SMS_FROM")
    SMS_RECIPIENTS: List[str] = get_env_list("ALERT_SMS_RECIPIENTS", [])
    SMS_MAX_RETRIES: int = get_env_int("SMS_MAX_RETRIES", 3) or 3
    SMS_RETRY_DELAY: float = float(os.getenv("SMS_RETRY_DELAY", "2.0") or "2.0")

    # Telegram citizen reporting (src/api/routes/telegram_webhook.py) - a
    # second, always-free intake channel alongside WhatsApp, added because
    # Telegram's Bot API has no trial/billing restriction anywhere,
    # unlike Twilio (see whatsapp_webhook.py's module docstring). Token
    # comes from @BotFather; webhook secret is an arbitrary string you
    # choose and pass to Telegram's setWebhook call, then Telegram echoes
    # it back on every request via X-Telegram-Bot-Api-Secret-Token so this
    # app can verify a request actually came from Telegram.
    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_WEBHOOK_SECRET: Optional[str] = os.getenv("TELEGRAM_WEBHOOK_SECRET")

    # SMTP Email (Optional)
    SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST")
    SMTP_PORT: Optional[int] = get_env_int("SMTP_PORT")
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER")
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")
    SMTP_FROM: Optional[str] = os.getenv("SMTP_FROM")
    SMTP_USE_TLS: bool = get_env_bool("SMTP_USE_TLS", True)
    EMAIL_RECIPIENTS: List[str] = get_env_list("ALERT_EMAIL_RECIPIENTS", [])
    EMAIL_MAX_RETRIES: int = get_env_int("EMAIL_MAX_RETRIES", 3) or 3
    EMAIL_RETRY_DELAY: float = float(os.getenv("EMAIL_RETRY_DELAY", "2.0") or "2.0")
    EMAIL_ENABLED: bool = bool(SMTP_USER and SMTP_PASSWORD and EMAIL_RECIPIENTS)

    # Alert Engine
    ALERTS_PER_HOUR: int = get_env_int("ALERTS_PER_HOUR", 3) or 3
    # Found during a codebase-wide audit: .env.example has documented
    # these five as real, deployer-configurable since this file's
    # earliest version, but nothing ever actually read them -
    # src/alerts/engine.py's THRESHOLDS dict and cooldown_minutes used
    # hardcoded literals that happened to match .env.example's numbers,
    # so the disconnect was invisible unless someone actually tried
    # changing one. Same bug class as ALERT_DRY_RUN above.
    ALERT_COOLDOWN_MINUTES: int = get_env_int("ALERT_COOLDOWN_MINUTES", 30) or 30
    ALERT_THRESHOLD_MODERATE: int = get_env_int("ALERT_THRESHOLD_MODERATE", 30) or 30
    ALERT_THRESHOLD_HIGH: int = get_env_int("ALERT_THRESHOLD_HIGH", 50) or 50
    ALERT_THRESHOLD_CRITICAL: int = get_env_int("ALERT_THRESHOLD_CRITICAL", 70) or 70
    ALERT_THRESHOLD_EXTREME: int = get_env_int("ALERT_THRESHOLD_EXTREME", 85) or 85

    # Observability
    ENABLE_METRICS: bool = get_env_bool("ENABLE_METRICS", False)
    ENABLE_TRACING: bool = get_env_bool("ENABLE_TRACING", False)

    # Resilience
    CIRCUIT_BREAKER_ENABLED: bool = get_env_bool("CIRCUIT_BREAKER_ENABLED", True)
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = (
        get_env_int("CIRCUIT_BREAKER_FAILURE_THRESHOLD", 5) or 5
    )
    CIRCUIT_BREAKER_TIMEOUT_SECONDS: int = (
        get_env_int("CIRCUIT_BREAKER_TIMEOUT_SECONDS", 60) or 60
    )

    # Timeouts
    API_TIMEOUT_SECONDS: int = get_env_int("API_TIMEOUT_SECONDS", 30) or 30

    @classmethod
    def get_provider_status(cls) -> Dict[str, bool]:
        return {
            # WHATSAPP_RECIPIENTS is no longer required for this provider
            # to be usable - src/database/channel_subscriptions_db.py now
            # supplies real, dynamic per-district recipients (a citizen
            # replying "ALERTS ON <district>"), so credentials alone are
            # enough to make sending worthwhile.
            "whatsapp": bool(cls.TWILIO_ACCOUNT_SID and cls.TWILIO_AUTH_TOKEN),
            "telegram": bool(cls.TELEGRAM_BOT_TOKEN),
            "sms": bool(
                cls.TWILIO_ACCOUNT_SID and cls.SMS_RECIPIENTS and cls.TWILIO_SMS_FROM
            ),
            "email": cls.EMAIL_ENABLED,
        }

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    def dict(self) -> Dict[str, Any]:
        return {
            "environment": self.ENVIRONMENT,
            "log_level": self.LOG_LEVEL,
            "api_version": self.API_VERSION,
            "providers": self.get_provider_status(),
            "alerts_per_hour": self.ALERTS_PER_HOUR,
        }


# Create singleton instance
settings = Settings()

# Production validation
if settings.is_production:
    errors = []
    if not settings.TWILIO_ACCOUNT_SID:
        errors.append("TWILIO_ACCOUNT_SID is required")
    if not settings.WHATSAPP_RECIPIENTS:
        errors.append("At least one WhatsApp recipient required")
    if not settings.API_KEY:
        errors.append("API_KEY is required")

    if errors:
        print("❌ Production configuration errors:")
        for error in errors:
            print(f"   - {error}")
    else:
        print("✅ Production configuration validated")

print(f"✅ Settings loaded for environment: {settings.ENVIRONMENT}")
print(f"   Providers: {settings.get_provider_status()}")

# ============================================================
# DRY RUN MODE - Prevent accidental alerts during testing
# ============================================================
# Real bug found while adding TelegramAlertProvider: this was a bare
# module-level variable, never attached to the `settings` object. Every
# real consumer (whatsapp_provider.py, telegram_provider.py, health.py)
# reads it via getattr(settings, "ALERT_DRY_RUN", False) - since the
# instance never actually had this attribute, that getattr silently
# fell back to False every time, regardless of the real env var. Setting
# ALERT_DRY_RUN=true to safely test never actually prevented a real
# WhatsApp send. The explicit assignment onto `settings` below is what
# makes every existing getattr(settings, "ALERT_DRY_RUN", ...) call
# actually work.
ALERT_DRY_RUN: bool = get_env_bool("ALERT_DRY_RUN", False)
settings.ALERT_DRY_RUN = ALERT_DRY_RUN

if ALERT_DRY_RUN:
    print("⚠️  ALERT_DRY_RUN is ENABLED - No real alerts will be sent")
