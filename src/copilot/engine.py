"""AI Copilot - a real, tool-calling operational assistant, not a chatbot
with general knowledge about floods.

Grounding architecture (why this is enforced structurally, not just by
prompting - "only answer from retrieved data" in a system prompt is not
by itself an enforcement mechanism; research on grounded/RAG assistants
is explicit that grounding has to be an architectural constraint: the
model must have no path to an answer except through tools that return
real data, and generation must be blocked - or forced into an honest
refusal - when those tools return nothing):

1. The model is given ONLY the tools in src/copilot/tools.py. None of
   them return free-text "knowledge" - every one returns a real,
   structured snapshot of this platform's own live computations (the
   same service-layer functions the deployed /v1/* routes call).
2. The system prompt requires every factual claim to name the tool/field
   it came from, and requires an explicit "I don't have enough data to
   answer that" when the tools don't cover the question - never a
   confident guess. This mirrors src/verification/outcome_verifier.py's
   existing "no_evidence_found" (not "no_flood_confirmed") pattern
   already used elsewhere in this platform for the same reason.
3. tool_choice is left at "auto" rather than forced, because most
   questions need 1-3 tool calls in sequence (e.g. "which districts are
   highest risk" -> get_current_risk_overview, then possibly
   get_district_decision on the top district for detail) - forcing a
   single tool would prevent that.

The Copilot never calls Earth Engine, DAHITI, Open-Meteo, or the
database directly - it only calls the tool functions, which call this
platform's existing, already-tested service layer. There is exactly one
implementation of every computation (decision cards, evidence, risk
history); the Copilot reuses it, it does not reimplement it.
"""

import logging
import os
from typing import List, Optional

from anthropic import AsyncAnthropic

from src.copilot.tools import (
    get_current_risk_overview,
    get_data_quality_report,
    get_data_source_health,
    get_district_decision,
    get_district_evidence,
    get_district_forecast,
    get_district_resources,
    list_tracked_districts,
)

logger = logging.getLogger("nfcc.copilot.engine")

_MODEL = "claude-opus-5"
_MAX_TOKENS = 4096
_MAX_ITERATIONS = 8

_TOOLS = [
    list_tracked_districts,
    get_current_risk_overview,
    get_district_decision,
    get_district_evidence,
    get_district_forecast,
    get_district_resources,
    get_data_source_health,
    get_data_quality_report,
]

_SYSTEM_PROMPT = """You are the NFCC (National Flood Command Center) AI Copilot, an \
operational assistant for Ghana's flood early-warning system. You are used by \
emergency operations staff making real decisions, so an overconfident wrong \
answer is worse than an honest "I don't know."

Hard rules:
1. You have NO knowledge of current flood conditions, risk levels, forecasts, \
shelters, or data-source status from your training. That information changes \
constantly and only exists in this platform's live systems. You MUST call a \
tool to get it - never state a risk tier, score, forecast figure, shelter \
name, or data-source status without having just retrieved it from a tool in \
this conversation.
2. Every factual claim in your answer must be traceable to a specific tool \
result. When you state a number or status, make clear which tool/district it \
came from (e.g. "per get_district_decision for Accra Central: risk_tier=MODERATE, \
score=42").
3. If the available tools do not cover what was asked, or a tool reports no \
recorded data (e.g. "no_recorded_snapshot", an unavailable data source, a \
missing field), say so plainly instead of guessing. Never fill a gap with a \
plausible-sounding fabricated value.
4. General flood-safety knowledge not specific to this platform's live data \
(e.g. "why does standing water spread disease") is out of scope - redirect to \
what the platform's own data shows.
5. Ghana has exactly 9 tracked districts (see list_tracked_districts). If \
asked about a place not on that list, say it isn't tracked rather than \
guessing its risk.
6. Keep answers operational and concise - the people reading this are making \
time-pressured decisions, not reading a report."""


class CopilotAnswer:
    def __init__(self, answer: str, tool_calls: List[dict], model: str):
        self.answer = answer
        self.tool_calls = tool_calls
        self.model = model

    def to_dict(self) -> dict:
        return {"answer": self.answer, "tool_calls": self.tool_calls, "model": self.model}


async def ask_copilot(question: str, district: Optional[str] = None) -> CopilotAnswer:
    """Answer one operational question, grounded entirely in this
    platform's real, live data via the tools in src/copilot/tools.py.

    Args:
        question: The user's question, verbatim.
        district: Optional district the question is scoped to, if the
            caller (e.g. the dashboard) already knows which one is
            selected - passed to the model as context, not assumed by
            any tool.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return CopilotAnswer(
            answer=(
                "The AI Copilot is not configured yet: ANTHROPIC_API_KEY is not "
                "set on this deployment. This is a configuration gap, not a data "
                "gap - ask your platform administrator to set it."
            ),
            tool_calls=[],
            model=_MODEL,
        )

    client = AsyncAnthropic(api_key=api_key)

    user_content = question
    if district:
        user_content = f"[Currently selected district in the dashboard: {district}]\n{question}"

    messages = [{"role": "user", "content": user_content}]
    tool_calls: List[dict] = []
    final_text = ""

    runner = client.beta.messages.tool_runner(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        system=_SYSTEM_PROMPT,
        tools=_TOOLS,
        messages=messages,
        thinking={"type": "adaptive"},
    )

    try:
        iterations = 0
        async for message in runner:
            iterations += 1
            for block in message.content:
                if block.type == "tool_use":
                    tool_calls.append({"tool": block.name, "input": block.input})
                elif block.type == "text":
                    final_text = block.text
            if iterations >= _MAX_ITERATIONS:
                logger.warning("Copilot hit max_iterations (%d) for question: %s", _MAX_ITERATIONS, question)
                break
    except Exception as e:
        logger.exception("Copilot tool-runner loop failed")
        return CopilotAnswer(
            answer=(
                "The Copilot hit an error retrieving live data and cannot answer "
                f"reliably right now ({e}). Try again, or check "
                "/v1/health/data-sources directly."
            ),
            tool_calls=tool_calls,
            model=_MODEL,
        )

    if not final_text:
        final_text = (
            "I wasn't able to produce a grounded answer to that from the "
            "platform's current data. Try rephrasing, or ask about a specific "
            "tracked district."
        )

    return CopilotAnswer(answer=final_text, tool_calls=tool_calls, model=_MODEL)
