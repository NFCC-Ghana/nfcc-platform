"""GET /v1/alert-subscriptions - read access to real WhatsApp/Telegram
alert opt-ins (src/database/channel_subscriptions_db.py).

A citizen subscribes with "ALERTS ON <district>" in the same chat they
report floods from (src/community/alert_subscription_commands.py) -
this is the operator-facing view of who that has actually reached,
mirroring src/api/v1/community_reports.py's role for inbound reports.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.auth import verify_api_key
from src.database.channel_subscriptions_db import get_all_channel_subscriptions

router = APIRouter(prefix="/alert-subscriptions", tags=["v1"])


class ChannelSubscription(BaseModel):
    id: int
    channel: str
    identifier: str
    district: Optional[str] = None
    min_risk_tier: str
    active: bool
    subscribed_at: str
    updated_at: str


class ChannelSubscriptionListResponse(BaseModel):
    count: int
    subscriptions: List[ChannelSubscription]


@router.get(
    "",
    response_model=ChannelSubscriptionListResponse,
    dependencies=[Depends(verify_api_key)],
)
async def list_alert_subscriptions(
    active_only: bool = True,
) -> ChannelSubscriptionListResponse:
    """Protected like /subscriptions/'s GET (src/api/routes/
    subscriptions.py) - a real WhatsApp phone number or Telegram
    chat_id is PII, not just risk-assessment output."""
    rows = get_all_channel_subscriptions(active_only=active_only)
    return ChannelSubscriptionListResponse(count=len(rows), subscriptions=rows)
