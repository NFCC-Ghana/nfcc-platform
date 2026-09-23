"""POST /v1/copilot/ask - the AI Copilot's single entry point. Thin
wrapper: all grounding logic lives in src/copilot/engine.py and
src/copilot/tools.py; this route only validates the request and returns
the answer plus the tool calls that produced it, so a caller (the
dashboard, or a curious operator) can see exactly what real data backed
the answer - never a black-box response.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from src.api.auth import limiter, verify_api_key
from src.copilot.engine import ask_copilot

router = APIRouter(prefix="/copilot", tags=["v1"])


class CopilotAskRequest(BaseModel):
    question: str
    district: Optional[str] = None


class CopilotToolCall(BaseModel):
    tool: str
    input: dict


class CopilotAskResponse(BaseModel):
    answer: str
    tool_calls: List[CopilotToolCall]
    model: str


@router.post(
    "/ask", response_model=CopilotAskResponse, dependencies=[Depends(verify_api_key)]
)
# 10/minute per IP - this calls the real Gemini API (src/copilot/engine.py),
# a paid/quota-limited external service, on every request. A security
# audit found no rate limiting anywhere on this endpoint - anyone holding
# the shared API key could script unlimited calls, directly driving up
# Gemini usage/cost with no cap. 10/minute is generous for a human asking
# questions through the dashboard's chat UI, the only real caller today.
@limiter.limit("10/minute")
async def copilot_ask(request: Request, body: CopilotAskRequest) -> CopilotAskResponse:
    result = await ask_copilot(body.question, district=body.district)
    return CopilotAskResponse(**result.to_dict())
