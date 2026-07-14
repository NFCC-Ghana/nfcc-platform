"""Shared payload fixtures for testing."""

from typing import Any, Dict, List


class PayloadFixtures:
    """Reusable payload fixtures for API testing."""

    @staticmethod
    def valid_payload(location: str = "Accra") -> Dict[str, Any]:
        """Valid scoring payload."""
        return {
            "precipitation": 10.5,
            "roll_3d": 25.0,
            "roll_7d": 30.0,
            "roll_30d": 40.0,
            "cumulative": 150.0,
            "z_score": 1.2,
            "location": location,
        }

    @staticmethod
    def high_risk_payload(location: str = "Accra") -> Dict[str, Any]:
        """High risk scoring payload."""
        return {
            "precipitation": 75.0,
            "roll_3d": 150.0,
            "roll_7d": 180.0,
            "roll_30d": 200.0,
            "cumulative": 800.0,
            "z_score": 3.5,
            "location": location,
        }

    @staticmethod
    def critical_risk_payload(location: str = "Accra") -> Dict[str, Any]:
        """Critical risk scoring payload."""
        return {
            "precipitation": 120.0,
            "roll_3d": 250.0,
            "roll_7d": 300.0,
            "roll_30d": 350.0,
            "cumulative": 1500.0,
            "z_score": 5.0,
            "location": location,
        }

    @staticmethod
    def zero_payload(location: str = "Accra") -> Dict[str, Any]:
        """Zero values payload."""
        return {
            "precipitation": 0.0,
            "roll_3d": 0.0,
            "roll_7d": 0.0,
            "roll_30d": 0.0,
            "cumulative": 0.0,
            "z_score": 0.0,
            "location": location,
        }

    @staticmethod
    def invalid_payload_variants() -> List[Dict[str, Any]]:
        """List of invalid payload variants."""
        return [
            {},  # Empty
            {"precipitation": 10},  # Missing fields
            {"precipitation": "invalid", "roll_3d": 10},  # Wrong type
            {"precipitation": -10},  # Negative
            {"precipitation": 600},  # Exceeds max
            {"roll_3d": 5, "precipitation": 10},  # roll_3d < precipitation
            {"precipitation": 10, "location": ""},  # Empty location
            {"precipitation": 10, "z_score": 100},  # Extreme z_score
        ]

    @staticmethod
    def batch_payload(records: list) -> Dict[str, Any]:
        """Batch scoring payload."""
        return {"records": records}

    @staticmethod
    def batch_valid_payload(count: int = 10) -> Dict[str, Any]:
        """Batch payload with valid records."""
        records = [PayloadFixtures.valid_payload() for _ in range(count)]
        return {"records": records}
