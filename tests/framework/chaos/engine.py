"""Core chaos engineering engine."""

import json
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass
class ChaosResult:
    """Result of chaos operation."""

    mutated_payload: Dict[str, Any]
    strategy: str
    changes: List[Dict[str, Any]]
    severity: str  # low, medium, high, critical


class ChaosEngine:
    """Production chaos engineering engine."""

    STRATEGIES = {
        "corrupt_json": "low",
        "drop_required_field": "high",
        "inject_large_numbers": "medium",
        "inject_null_values": "medium",
        "swap_fields": "low",
        "duplicate_fields": "low",
        "infinite_recursion": "critical",
        "circular_reference": "critical",
        "type_mismatch": "high",
    }

    @classmethod
    def corrupt_json(cls, payload: Dict[str, Any]) -> ChaosResult:
        """Randomly corrupt JSON structure."""
        changes = []
        mutated = payload.copy()

        # Corrupt random field
        keys = list(mutated.keys())
        if keys:
            field = random.choice(keys)
            original = mutated[field]
            mutated[field] = None
            changes.append({"field": field, "from": original, "to": None})

        return ChaosResult(
            mutated_payload=mutated,
            strategy="corrupt_json",
            changes=changes,
            severity="low",
        )

    @classmethod
    def drop_required_field(cls, payload: Dict[str, Any]) -> ChaosResult:
        """Remove a required field."""
        changes = []
        mutated = payload.copy()

        required_fields = [
            "precipitation",
            "roll_3d",
            "roll_7d",
            "roll_30d",
            "cumulative",
            "z_score",
        ]
        available = [f for f in required_fields if f in mutated]

        if available:
            field = random.choice(available)
            original = mutated.pop(field)
            changes.append({"field": field, "removed": original})

        return ChaosResult(
            mutated_payload=mutated,
            strategy="drop_required_field",
            changes=changes,
            severity="high",
        )

    @classmethod
    def inject_large_numbers(cls, payload: Dict[str, Any]) -> ChaosResult:
        """Inject extremely large numbers."""
        changes = []
        mutated = payload.copy()

        for key, value in mutated.items():
            if isinstance(value, (int, float)):
                original = value
                mutated[key] = 1e308  # Python float max
                changes.append({"field": key, "from": original, "to": "1e308"})

        return ChaosResult(
            mutated_payload=mutated,
            strategy="inject_large_numbers",
            changes=changes,
            severity="medium",
        )

    @classmethod
    def inject_null_values(cls, payload: Dict[str, Any]) -> ChaosResult:
        """Inject null values."""
        changes = []
        mutated = payload.copy()

        keys = list(mutated.keys())
        if keys:
            field = random.choice(keys)
            original = mutated[field]
            mutated[field] = None
            changes.append({"field": field, "from": original, "to": None})

        return ChaosResult(
            mutated_payload=mutated,
            strategy="inject_null_values",
            changes=changes,
            severity="medium",
        )

    @classmethod
    def type_mismatch(cls, payload: Dict[str, Any]) -> ChaosResult:
        """Replace numeric fields with strings."""
        changes = []
        mutated = payload.copy()

        for key in [
            "precipitation",
            "roll_3d",
            "roll_7d",
            "roll_30d",
            "cumulative",
            "z_score",
        ]:
            if key in mutated:
                original = mutated[key]
                mutated[key] = "NOT_A_NUMBER"
                changes.append({"field": key, "from": original, "to": "NOT_A_NUMBER"})
                break

        return ChaosResult(
            mutated_payload=mutated,
            strategy="type_mismatch",
            changes=changes,
            severity="high",
        )

    @classmethod
    def random_mutation(cls, payload: Dict[str, Any]) -> ChaosResult:
        """Apply random mutation strategy."""
        strategies = [
            cls.corrupt_json,
            cls.drop_required_field,
            cls.inject_large_numbers,
            cls.inject_null_values,
            cls.type_mismatch,
        ]
        strategy = random.choice(strategies)
        return strategy(payload)

    @classmethod
    def apply_all_strategies(cls, payload: Dict[str, Any]) -> List[ChaosResult]:
        """Apply all chaos strategies and return results."""
        results = []
        for strategy_name in cls.STRATEGIES.keys():
            if hasattr(cls, strategy_name):
                try:
                    result = getattr(cls, strategy_name)(payload)
                    results.append(result)
                except Exception as e:
                    print(f"Strategy {strategy_name} failed: {e}")
        return results
