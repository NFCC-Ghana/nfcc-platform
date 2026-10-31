"""Dashboard state built from a /situation response (hackathon/app/modules/v4/state.py)."""

from hackathon.app.modules.v4.state import create_state_from_api


def test_real_zero_exposure_is_not_treated_as_unavailable():
    """A dry day scores 0, so the real estimate is 0 exposed. The impact
    panel must show that 0, not switch to its illustrative generator."""
    state = create_state_from_api({"score": 0.0, "risk_tier": "LOW", "population_exposed": 0})
    assert state.impact_available is True
    assert state.population_exposed == 0


def test_missing_impact_block_is_unavailable():
    state = create_state_from_api({"score": 12.0, "risk_tier": "LOW"})
    assert state.impact_available is False
