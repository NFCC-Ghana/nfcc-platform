"""Regression test for src/copilot/engine.py's configuration-gap honesty
path: with no ANTHROPIC_API_KEY set, the Copilot must say so plainly
rather than silently answering from the model's general knowledge (which
would be impossible anyway with no API key, but the point is the
response must clearly name the real cause - "not configured" - not a
generic error)."""

import pytest

from src.copilot.engine import ask_copilot


@pytest.mark.asyncio
async def test_ask_copilot_reports_missing_api_key_honestly(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = await ask_copilot("Which districts are at highest risk?")
    assert "ANTHROPIC_API_KEY" in result.answer
    assert result.tool_calls == []
