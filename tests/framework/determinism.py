"""Determinism and replay testing for ML APIs."""

import hashlib
import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class ReplayResult:
    """Result of replay test."""

    original_response: Dict[str, Any]
    replay_responses: List[Dict[str, Any]]
    consistent: bool
    differences: List[Dict[str, Any]]


class DeterminismValidator:
    """Validate deterministic behavior."""

    @staticmethod
    def assert_idempotent(client, endpoint: str, payload: Dict[str, Any], n: int = 5):
        """Assert same input produces same output."""
        responses = []

        for i in range(n):
            response = client.post(endpoint, json=payload)
            assert (
                response.status_code == 200
            ), f"Request {i+1} failed: {response.status_code}"
            responses.append(response.json())

        # Remove timestamp fields for comparison
        def normalize(data):
            normalized = {
                k: v
                for k, v in data.items()
                if k not in ["timestamp", "time", "request_id"]
            }
            # Handle nested structures
            for k, v in normalized.items():
                if isinstance(v, dict):
                    normalized[k] = normalize(v)
            return normalized

        normalized_responses = [normalize(r) for r in responses]

        # Compare all responses
        for i in range(1, len(normalized_responses)):
            assert (
                normalized_responses[0] == normalized_responses[i]
            ), f"Non-deterministic: Response {i} differs from first"

        return responses[0]

    @staticmethod
    def replay_failure(
        client, failure_payload: Dict[str, Any], n: int = 3
    ) -> ReplayResult:
        """Replay a failure and verify consistent behavior."""
        responses = []

        for i in range(n):
            response = client.post("/score", json=failure_payload)
            responses.append(response.json())

        # Check consistency
        consistent = (
            all(
                responses[0].get("error_code") == r.get("error_code")
                for r in responses[1:]
            )
            if responses
            else False
        )

        differences = []
        for i in range(1, len(responses)):
            if responses[0] != responses[i]:
                differences.append(
                    {
                        "attempt": i,
                        "first": responses[0],
                        "current": responses[i],
                    }
                )

        return ReplayResult(
            original_response=responses[0] if responses else {},
            replay_responses=responses,
            consistent=consistent,
            differences=differences,
        )

    @staticmethod
    def hash_response(response: Dict[str, Any], exclude_keys: List[str] = None) -> str:
        """Create deterministic hash of response."""
        exclude_keys = exclude_keys or ["timestamp", "time", "request_id", "trace_id"]
        response_copy = {k: v for k, v in response.items() if k not in exclude_keys}

        # Sort keys for consistent hashing
        return hashlib.md5(
            json.dumps(response_copy, sort_keys=True, default=str).encode()
        ).hexdigest()

    @staticmethod
    def verify_failure_reproducible(client, failure_scenarios: List[Dict[str, Any]]):
        """Verify that failures are reproducible."""
        results = {}

        for i, scenario in enumerate(failure_scenarios):
            hash1 = DeterminismValidator.hash_response(
                client.post("/score", json=scenario).json()
            )

            # Small delay
            time.sleep(0.1)

            hash2 = DeterminismValidator.hash_response(
                client.post("/score", json=scenario).json()
            )

            results[f"scenario_{i}"] = {
                "reproducible": hash1 == hash2,
                "hash": hash1,
            }

        return results

    @staticmethod
    def golden_path_test(
        client, golden_payload: Dict[str, Any], expected_response: Dict[str, Any]
    ):
        """Test against golden response."""
        response = client.post("/score", json=golden_payload)
        assert response.status_code == 200

        actual = response.json()
        # Check key fields match
        for key in expected_response:
            if key in actual:
                if isinstance(expected_response[key], (int, float)):
                    assert (
                        abs(actual[key] - expected_response[key]) < 0.01
                    ), f"Field {key}: expected {expected_response[key]}, got {actual[key]}"
                else:
                    assert (
                        actual[key] == expected_response[key]
                    ), f"Field {key}: expected {expected_response[key]}, got {actual[key]}"

        return actual
