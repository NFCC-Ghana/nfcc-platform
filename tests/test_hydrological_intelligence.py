"""Comprehensive tests for hydrological intelligence."""

import pytest
from src.hydrology.unified_intelligence import unified_intelligence
from src.hydrology.rainfall_history import rainfall_history
from src.hydrology.river_intelligence import river_intelligence
from src.hydrology.reservoir_intelligence import reservoir_intelligence
from src.hydrology.soil_moisture import soil_moisture
from src.hydrology.flood_polygons import flood_polygons


def test_rainfall_history():
    """Test rainfall history engine."""
    features = rainfall_history.get_district_rainfall_features("Accra Central")
    assert features is not None
    assert "rain_3d" in features
    assert "rain_7d" in features
    assert "rain_30d" in features
    print("✅ Rainfall history test passed")


def test_river_intelligence():
    """Test river intelligence engine."""
    status = river_intelligence.get_river_status("Accra Central")
    assert status is not None
    assert "river" in status
    assert "status" in status
    print("✅ River intelligence test passed")


def test_reservoir_intelligence():
    """Test reservoir intelligence engine."""
    status = reservoir_intelligence.get_dam_status("akosombo")
    assert status is not None
    assert "dam_name" in status
    assert "spillage_risk" in status
    print("✅ Reservoir intelligence test passed")


def test_soil_moisture():
    """Test soil moisture engine."""
    status = soil_moisture.get_soil_moisture("Accra Central")
    assert status is not None
    assert "saturation_index" in status
    assert "runoff_potential" in status
    print("✅ Soil moisture test passed")


def test_flood_polygons():
    """Test flood polygon engine."""
    events = flood_polygons.get_flood_events("Accra Central")
    assert events is not None
    print("✅ Flood polygon test passed")


def test_unified_intelligence():
    """Test unified intelligence engine."""
    assessment = unified_intelligence.get_complete_risk_assessment(
        "Accra Central", 75.0
    )
    assert assessment is not None
    assert "composite_risk" in assessment
    assert "recommendations" in assessment
    assert "rainfall" in assessment
    assert "river" in assessment
    assert "dam_risk" in assessment
    assert "soil" in assessment
    print("✅ Unified intelligence test passed")

    # Print summary
    print(f"\n📊 Assessment Summary:")
    print(f"   District: {assessment['district']}")
    print(f"   Risk Score: {assessment['composite_risk']['score']}")
    print(f"   Risk Category: {assessment['composite_risk']['category']}")
    print(f"   Total Recommendations: {len(assessment['recommendations'])}")


def test_civicflood_integration():
    """Test CivicFlood AI integration."""
    from hackathon.ai.hydrological_intelligence import civicflood_hydrological

    data = civicflood_hydrological.get_complete_dashboard_data("Accra Central", 75.0)
    assert data is not None
    assert "risk" in data
    assert "river" in data
    assert "dam" in data
    assert "soil" in data
    assert "history" in data
    assert "recommendations" in data
    print("✅ CivicFlood integration test passed")


if __name__ == "__main__":
    print("🚀 Running Hydrological Intelligence Tests...\n")

    test_rainfall_history()
    test_river_intelligence()
    test_reservoir_intelligence()
    test_soil_moisture()
    test_flood_polygons()
    test_unified_intelligence()
    test_civicflood_integration()

    print("\n✅ All tests passed! Hydrological intelligence is ready.")
