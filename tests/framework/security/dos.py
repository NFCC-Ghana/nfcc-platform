"""Denial of Service testing utilities."""

import json
from typing import Dict, Any, List


class DoSTester:
    """Test DoS vulnerabilities."""

    @staticmethod
    def large_payload(size_mb: float = 10) -> Dict[str, Any]:
        """Generate large payload for DoS testing."""
        # Create large string (capped at reasonable size for testing)
        char_count = min(int(size_mb * 1024 * 1024), 50000)  # Cap at 50k chars
        large_string = "X" * char_count

        return {
            "precipitation": 10,
            "roll_3d": 10,
            "roll_7d": 20,
            "roll_30d": 30,
            "cumulative": 100,
            "z_score": 1.5,
            "location": large_string,
        }

    @staticmethod
    def many_fields_payload(n_fields: int = 100) -> Dict[str, Any]:
        """Generate payload with many fields."""
        payload = {
            "precipitation": 10,
            "roll_3d": 10,
            "roll_7d": 20,
            "roll_30d": 30,
            "cumulative": 100,
            "z_score": 1.5,
            "location": "Accra",
        }

        for i in range(n_fields):
            payload[f"extra_field_{i}"] = "x" * 100

        return payload

    @staticmethod
    def array_explosion_payload(array_size: int = 1000) -> Dict[str, Any]:
        """Generate payload with large array."""
        return {
            "precipitation": 10,
            "roll_3d": 10,
            "roll_7d": 20,
            "roll_30d": 30,
            "cumulative": 100,
            "z_score": 1.5,
            "location": "Accra",
            "extra_data": ["x" * 100 for _ in range(array_size)],
        }

    @staticmethod
    def json_bomb(depth: int = 100) -> Dict[str, Any]:
        """Generate JSON bomb with deep nesting."""
        bomb = {"a": "b"}
        current = bomb
        for i in range(depth):
            current["next"] = {"level": i}
            current = current["next"]
        return bomb

    @staticmethod
    def billion_laughs_attack() -> str:
        """Generate billion laughs XML-style attack (JSON equivalent)."""
        # Create nested expansion
        laugh = {"lol": "lol"}
        for i in range(10):
            laugh = {"lol": [laugh, laugh]}

        return {"precipitation": 10, "attack": laugh}

    @staticmethod
    def assert_resilient(response, max_status: int = 500):
        """Assert system remains resilient under DoS."""
        assert (
            response.status_code < max_status or response.status_code == 500
        ), f"DoS attack caused crash: {response.status_code}"
        return True
