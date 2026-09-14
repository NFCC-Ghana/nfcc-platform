"""FastAPI router for alert subscriptions management."""

import logging
import sqlite3
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, validator

from src.database.alert_db import (
    subscribe,
    unsubscribe,
    get_subscription,
    get_all_subscriptions,
)

logger = logging.getLogger("nfcc-api.subscriptions")

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])

ALLOWED_PROVIDERS = {"email", "sms", "whatsapp"}
ALLOWED_RISK_TIERS = {"LOW", "MODERATE", "HIGH", "CRITICAL", "EXTREME"}


class SubscriptionRequest(BaseModel):
    """Request body to create a new subscription."""

    email: EmailStr = Field(..., description="Subscriber email address")
    phone: Optional[str] = Field(
        None,
        description="Optional phone number for SMS/WhatsApp delivery",
    )
    preferred_provider: str = Field(
        "email",
        description="Preferred delivery provider",
    )
    location_filter: Optional[str] = Field(
        None,
        description="Optional district or location filter for alerts",
    )
    min_risk_tier: str = Field(
        "MODERATE",
        description="Minimum risk tier required to receive alerts",
    )
    unsubscribe_token: Optional[str] = Field(
        None,
        description="Optional unsubscribe token for self-service URLs",
    )

    @validator("preferred_provider")
    def validate_provider(cls, value: str) -> str:
        if value not in ALLOWED_PROVIDERS:
            raise ValueError(
                f"preferred_provider must be one of {sorted(ALLOWED_PROVIDERS)}"
            )
        return value

    @validator("min_risk_tier")
    def validate_risk_tier(cls, value: str) -> str:
        tier = value.upper()
        if tier not in ALLOWED_RISK_TIERS:
            raise ValueError(f"min_risk_tier must be one of {sorted(ALLOWED_RISK_TIERS)}")
        return tier


class SubscriptionResponse(BaseModel):
    """Response model for created or retrieved subscriptions."""

    id: int
    email: EmailStr
    phone: Optional[str]
    preferred_provider: str
    location_filter: Optional[str]
    min_risk_tier: str
    active: bool
    created_at: str
    updated_at: str
    unsubscribe_token: Optional[str]


class UnsubscribeResponse(BaseModel):
    """Response model for unsubscribe actions."""

    status: str
    email: EmailStr
    unsubscribed: bool


@router.post("/", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(payload: SubscriptionRequest) -> SubscriptionResponse:
    """Create a new alert subscription."""
    try:
        subscription_id = subscribe(payload.dict())
        subscription = get_subscription(payload.email)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve newly created subscription",
            )
        return SubscriptionResponse(**subscription)
    except sqlite3.IntegrityError as exc:
        logger.error(f"Subscription creation failed for {payload.email}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A subscription already exists for this email",
        )
    except ValueError as exc:
        logger.error(f"Invalid subscription payload: {exc}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error(f"Unexpected subscription creation error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create subscription",
        )


@router.delete("/{email}", response_model=UnsubscribeResponse)
async def unsubscribe_endpoint(email: EmailStr) -> UnsubscribeResponse:
    """Unsubscribe the target email address."""
    try:
        success = unsubscribe(email)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found",
            )
        return UnsubscribeResponse(status="success", email=email, unsubscribed=True)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Unexpected unsubscribe error for {email}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to unsubscribe",
        )


@router.get("/", response_model=List[SubscriptionResponse])
async def list_subscriptions(active_only: bool = True) -> List[SubscriptionResponse]:
    """List current subscriptions."""
    subscriptions = get_all_subscriptions(active_only=active_only)
    return [SubscriptionResponse(**sub) for sub in subscriptions]
