"""Production settings with explicit environment loading."""

import os
import pickle
import joblib
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

    # Model Configuration.
    #
    # models/xgboost_flood_risk.pkl (282KB, a real trained XGBRegressor -
    # see src/models/train_model.py) is the only model file that has ever
    # actually been trained and committed. models/xgboost_flood_risk.joblib
    # is NOT a converted copy of it - it's a 53-byte placeholder
    # (`{"model": "xgboost_flood_risk", "version": "1.0.0"}`) committed by
    # "fix: Force add dummy model file for CI tests", just JSON text, not
    # a real serialized model at all.
    #
    # This default used to point at that placeholder, and the "if the
    # configured path is .pkl, prefer a same-named .joblib sibling if one
    # exists" logic below actively redirected any explicit .pkl override
    # back onto it too - so unless MODEL_PATH was set to exactly
    # "models/xgboost_flood_risk.pkl" AND that redirect logic was somehow
    # bypassed, joblib.load() received JSON bytes instead of a pickle
    # stream and failed with a confusing KeyError deep inside pickle's
    # opcode dispatch, logged as "Failed to load model" with no further
    # detail. Nothing in Dockerfile.prod, railway.json, or
    # .env.example overrides this default away from the broken path
    # (.env.example itself has the same wrong path) - only
    # elite-resilience.yml happens to set MODEL_PATH explicitly, which is
    # why that one workflow's tests didn't hit this.
    MODEL_PATH: str = os.getenv("MODEL_PATH", "models/xgboost_flood_risk.pkl")
    _model_cache = None

    def _load_model(self):
        """Load the trained flood-risk model.

        joblib.load() transparently reads both real joblib-format files
        and plain pickle files (which is what MODEL_PATH actually points
        at) - so this does not need separate pickle.load()/joblib.load()
        code paths for the two extensions.
        """
        model_path = Path(self.MODEL_PATH)

        if not model_path.exists():
            raise FileNotFoundError(f"Model not found at {model_path}")

        try:
            model = joblib.load(model_path)
            print(f"✅ Model loaded from: {model_path}")
            return model
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            raise

    @property
    def model(self):
        """Lazy load model - caches after first load."""
        if self._model_cache is None:
            self._model_cache = self._load_model()
        return self._model_cache

    # Alert Engine
    ALERTS_PER_HOUR: int = get_env_int("ALERTS_PER_HOUR", 3) or 3

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
            "whatsapp": bool(cls.TWILIO_ACCOUNT_SID and cls.WHATSAPP_RECIPIENTS),
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
            "model_path": self.MODEL_PATH,
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
ALERT_DRY_RUN: bool = get_env_bool("ALERT_DRY_RUN", False)

if ALERT_DRY_RUN:
    print("⚠️  ALERT_DRY_RUN is ENABLED - No real alerts will be sent")
