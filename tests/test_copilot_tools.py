"""Regression tests for the AI Copilot's evidence/retrieval layer
(src/copilot/tools.py) - each @beta_async_tool wraps one real platform
computation; these tests call the tool's underlying function directly
(`.func(...)`, the plain async function the decorator wraps - confirmed
via the installed anthropic SDK, not guessed) and assert it returns real
data, never a fabricated fallback, and honestly reports unknown
districts / missing history instead of guessing.
"""

import pytest

from src.copilot import tools
from src.database.risk_history_db import init_risk_history_table


@pytest.mark.asyncio
async def test_list_tracked_districts_returns_all_nine():
    result = await tools.list_tracked_districts.func()
    assert result["count"] == 9
    names = [d["name"] for d in result["districts"]]
    assert "Accra Central" in names
    assert "Tamale" in names
    # Real named communities, not a placeholder - see
    # src/exposure/community_names.py.
    accra = next(d for d in result["districts"] if d["name"] == "Accra Central")
    assert len(accra["communities"]) > 0


@pytest.mark.asyncio
async def test_get_district_decision_rejects_untracked_district():
    result = await tools.get_district_decision.func("Atlantis")
    assert "error" in result
    assert "Atlantis" in result["error"]


@pytest.mark.asyncio
async def test_get_district_decision_real_data_for_tracked_district():
    result = await tools.get_district_decision.func("Tamale", precipitation_mm=90)
    assert result["precipitation_source"] == "user-specified"
    assert result["risk_tier"] in ("VERY_LOW", "LOW", "MODERATE", "HIGH", "CRITICAL", "EXTREME")
    assert "evidence" in result
    assert "data_gaps" in result


@pytest.mark.asyncio
async def test_get_district_decision_auto_fetches_precipitation_when_omitted():
    result = await tools.get_district_decision.func("Tamale")
    assert result["precipitation_source"].startswith("auto:")
    assert isinstance(result["precipitation_mm_used"], float)


@pytest.mark.asyncio
async def test_get_current_risk_overview_covers_every_tracked_district():
    init_risk_history_table()  # same table conftest's api_client fixture
    # would create via the app's startup event - this test doesn't go
    # through the app, so it creates it directly, matching the pattern
    # tests/conftest.py already uses for the alerts DB.
    overview = await tools.get_current_risk_overview.func()
    districts = {d["district"] for d in overview["districts"]}
    assert districts == set(tools.TRACKED_DISTRICT_NAMES)
    # A district with no recorded snapshot must say so honestly, never
    # fabricate a score - this is the default state for a fresh DB.
    for entry in overview["districts"]:
        assert "status" in entry or "latest" in entry


@pytest.mark.asyncio
async def test_get_district_evidence_rejects_untracked_district():
    result = await tools.get_district_evidence.func("Neverland")
    assert "error" in result


@pytest.mark.asyncio
async def test_get_district_forecast_includes_six_hour_point():
    result = await tools.get_district_forecast.func("Kumasi", current_precipitation_mm=20)
    hours = [p["hour"] for p in result["risk_timeline"]]
    assert "6h" in hours
    assert "Now" in hours


@pytest.mark.asyncio
async def test_get_district_resources_excludes_fabricated_inventory():
    result = await tools.get_district_resources.func("Ho", precipitation_mm=10)
    # Deliberately no rescue_boats/ambulances/pumps keys - no real
    # inventory system exists for those (see resources.py's docstring).
    assert "rescue_boats" not in result
    assert "shelters" in result
    assert "dams" in result


@pytest.mark.asyncio
async def test_get_data_source_health_reports_real_statuses():
    result = await tools.get_data_source_health.func()
    assert result["overall_status"] in ("healthy", "degraded")
    names = [s["name"] for s in result["sources"]]
    assert any("Earth Engine" in n for n in names)


@pytest.mark.asyncio
async def test_get_data_quality_report_returns_system_status():
    result = await tools.get_data_quality_report.func()
    assert result["system_status"] in ("healthy", "partial", "degraded")
    assert "sources" in result
