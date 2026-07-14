"""Subscription management API endpoints for WhatsApp/SMS alerts."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.alerts.subscriptions import subscription_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


class SubscribeRequest(BaseModel):
    """Subscribe request model."""

    phone: str = Field(
        ..., description="Phone number with country code", example="+233244714242"
    )
    district: str = Field(
        ..., description="District to subscribe to", example="Accra Central"
    )
    channel: str = Field("whatsapp", description="Channel: whatsapp, sms, email")


class SubscribeResponse(BaseModel):
    """Subscribe response model."""

    status: str
    phone: str
    district: str
    channel: str
    message: str


class UnsubscribeRequest(BaseModel):
    """Unsubscribe request model."""

    phone: str = Field(..., description="Phone number to unsubscribe")


class UnsubscribeResponse(BaseModel):
    """Unsubscribe response model."""

    status: str
    phone: str
    message: str


@router.post("/subscribe", response_model=SubscribeResponse)
async def subscribe(request: SubscribeRequest):
    """Subscribe a phone number to flood alerts for a district."""
    try:
        result = subscription_manager.subscribe(
            phone=request.phone, district=request.district, channel=request.channel
        )
        return SubscribeResponse(
            status="success",
            phone=request.phone,
            district=request.district,
            channel=request.channel,
            message=f"✅ Subscribed to alerts for {request.district}",
        )
    except Exception as e:
        logger.error(f"Subscription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/unsubscribe", response_model=UnsubscribeResponse)
async def unsubscribe(request: UnsubscribeRequest):
    """Unsubscribe a phone number from all alerts."""
    try:
        result = subscription_manager.unsubscribe(phone=request.phone)
        return UnsubscribeResponse(
            status="success",
            phone=request.phone,
            message="✅ Unsubscribed from all alerts",
        )
    except Exception as e:
        logger.error(f"Unsubscription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscribers")
async def get_subscribers(
    district: str = Query(..., description="District to get subscribers for"),
    alert_level: Optional[str] = Query(None, description="Minimum alert level"),
):
    """Get all subscribers for a district."""
    try:
        subscribers = subscription_manager.get_subscribers(district, alert_level)
        return {
            "status": "success",
            "district": district,
            "count": len(subscribers),
            "subscribers": subscribers,
        }
    except Exception as e:
        logger.error(f"Failed to get subscribers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_subscription_stats():
    """Get subscription statistics."""
    try:
        stats = subscription_manager.get_stats()
        return {"status": "success", "stats": stats}
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check/{phone}")
async def check_subscription(phone: str):
    """Check if a phone number is subscribed."""
    try:
        # Get all subscribers and check if phone exists
        conn = subscription_manager._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM subscriptions WHERE phone_number = ? AND active = TRUE",
            (phone,),
        )
        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                "status": "success",
                "subscribed": True,
                "phone": phone,
                "district": result[4] if len(result) > 4 else "Unknown",
            }
        else:
            return {"status": "success", "subscribed": False, "phone": phone}
    except Exception as e:
        logger.error(f"Failed to check subscription: {e}")
        raise HTTPException(status_code=500, detail=str(e))
