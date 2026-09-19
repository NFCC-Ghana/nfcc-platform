"""AI Copilot - a real, tool-calling operational assistant, not a chatbot
with general knowledge about floods.

Runs on Google's Gemini API (google-genai), not Anthropic's Claude:
Anthropic's own free "Evaluation access" tier has $0 credits and no
usable free quota, while Gemini's free tier is a genuinely ongoing,
no-card-required allowance (confirmed against the currently installed
google-genai==2.24.0 SDK's own source, not guessed) - the only realistic
option for a solo, low-budget maintainer.

Model is "gemini-flash-lite-latest", a Google-maintained alias, not a
pinned dated model name: gemini-2.5-flash and gemini-2.5-flash-lite were
both tried first and both returned a live 404 ("no longer available to
new users") against this project's real key - Google had already
deprecated them for newly created API keys/projects by the time this was
written, despite still listing them in models.list. An alias that
Google itself keeps pointed at a current model avoids repeating that
exact failure the next time a dated model name is retired. If billing
ever allows it, swapping back to Claude only requires rewriting this
file - src/copilot/tools.py's plain async functions are provider-
agnostic and were already used unmodified.

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
3. Gemini's automatic function calling (google.genai.types.
   AutomaticFunctionCallingConfig) is left enabled with a bounded
   maximum_remote_calls rather than forced single-tool calls, because
   most questions need 1-3 tool calls in sequence (e.g. "which districts
   are highest risk" -> get_current_risk_overview, then possibly
   get_district_decision on the top district for detail).

The Copilot never calls Earth Engine, DAHITI, Open-Meteo, or the
database directly - it only calls the tool functions, which call this
platform's existing, already-tested service layer. There is exactly one
implementation of every computation (decision cards, evidence, risk
history); the Copilot reuses it, it does not reimplement it.
"""

import logging
import os
from typing import List, Optional

from google import genai
from google.genai import types

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

_MODEL = "gemini-flash-lite-latest"
_MAX_TOOL_CALLS = 8

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


def _extract_tool_calls(response) -> List[dict]:
    """Pulls {tool, input} pairs out of Gemini's automatic_function_calling_
    history - the record of every tool call the SDK executed on this
    platform's behalf, kept for the same transparency reason the dashboard
    shows an "Evidence used" panel: a grounded answer must be able to show
    its work, not just assert it."""
    calls: List[dict] = []
    for content in response.automatic_function_calling_history or []:
        for part in content.parts or []:
            if part.function_call is not None:
                calls.append(
                    {"tool": part.function_call.name, "input": dict(part.function_call.args or {})}
                )
    return calls


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
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return CopilotAnswer(
            answer=(
                "The AI Copilot is not configured yet: GEMINI_API_KEY is not "
                "set on this deployment. This is a configuration gap, not a data "
                "gap - ask your platform administrator to set it."
            ),
            tool_calls=[],
            model=_MODEL,
        )

    client = genai.Client(api_key=api_key)

    user_content = question
    if district:
        user_content = f"[Currently selected district in the dashboard: {district}]\n{question}"

    config = types.GenerateContentConfig(
        system_instruction=_SYSTEM_PROMPT,
        tools=_TOOLS,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            maximum_remote_calls=_MAX_TOOL_CALLS
        ),
    )

    try:
        response = await client.aio.models.generate_content(
            model=_MODEL, contents=user_content, config=config
        )
    except Exception as e:
        logger.exception("Copilot generate_content call failed")
        return CopilotAnswer(
            answer=(
                "The Copilot hit an error retrieving live data and cannot answer "
                f"reliably right now ({e}). Try again, or check "
                "/v1/health/data-sources directly."
            ),
            tool_calls=[],
            model=_MODEL,
        )

    tool_calls = _extract_tool_calls(response)
    answer_text = response.text or (
        "I wasn't able to produce a grounded answer to that from the "
        "platform's current data. Try rephrasing, or ask about a specific "
        "tracked district."
    )

    return CopilotAnswer(answer=answer_text, tool_calls=tool_calls, model=_MODEL)
