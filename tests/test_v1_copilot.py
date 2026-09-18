"""Regression tests for POST /v1/copilot/ask (src/api/v1/copilot.py).

The route itself is a thin pass-through to src/copilot/engine.py's
ask_copilot() - these tests mock that function so they run without a
real ANTHROPIC_API_KEY or network access, and only assert the route's
own contract (request/response shape). Grounding behavior itself is
exercised by tests/test_copilot_tools.py (the real tool functions) and
tests/test_copilot_engine.py (the no-API-key honesty path).
"""

from unittest.mock import AsyncMock, patch

from src.copilot.engine import CopilotAnswer


def test_copilot_ask_returns_answer_and_tool_calls(api_client):
    fake_answer = CopilotAnswer(
        answer="Tamale is at MODERATE risk per get_district_decision.",
        tool_calls=[{"tool": "get_district_decision", "input": {"district": "Tamale"}}],
        model="claude-opus-5",
    )
    with patch(
        "src.api.v1.copilot.ask_copilot", new=AsyncMock(return_value=fake_answer)
    ):
        resp = api_client.post(
            "/v1/copilot/ask",
            json={"question": "Why is Tamale at moderate risk?", "district": "Tamale"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == fake_answer.answer
    assert data["tool_calls"][0]["tool"] == "get_district_decision"
    assert data["model"] == "claude-opus-5"


def test_copilot_ask_requires_question_field(api_client):
    resp = api_client.post("/v1/copilot/ask", json={"district": "Tamale"})
    assert resp.status_code == 422
