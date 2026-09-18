"""POST /v1/copilot/ask - the AI Copilot's single entry point. Thin
wrapper: all grounding logic lives in src/copilot/engine.py and
src/copilot/tools.py; this route only validates the request and returns
the answer plus the tool calls that produced it, so a caller (the
dashboard, or a curious operator) can see exactly what real data backed
the answer - never a black-box response.
"""

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

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


@router.post("/ask", response_model=CopilotAskResponse)
async def copilot_ask(request: CopilotAskRequest) -> CopilotAskResponse:
    result = await ask_copilot(request.question, district=request.district)
    return CopilotAskResponse(**result.to_dict())
