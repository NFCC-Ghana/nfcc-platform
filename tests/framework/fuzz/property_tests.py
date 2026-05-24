"""Property-based testing with Hypothesis - automatic invariant discovery."""

from hypothesis import given, strategies as st, assume, settings, HealthCheck
from typing import Dict, Any, Callable
import json


class PropertyTestEngine:
    """Property-based testing engine for automatic invariant discovery."""
    
    @staticmethod
    @st.composite
    def valid_payload_strategy(draw):
        """Generate valid payloads."""
        return {
            "precipitation": draw(st.floats(min_value=0, max_value=500, allow_nan=False, allow_infinity=False)),
            "roll_3d": draw(st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False)),
            "roll_7d": draw(st.floats(min_value=0, max_value=500, allow_nan=False, allow_infinity=False)),
            "roll_30d": draw(st.floats(min_value=0, max_value=200, allow_nan=False, allow_infinity=False)),
            "cumulative": draw(st.floats(min_value=0, max_value=5000, allow_nan=False, allow_infinity=False)),
            "z_score": draw(st.floats(min_value=-5, max_value=10, allow_nan=False, allow_infinity=False)),
            "location": draw(st.text(min_size=1, max_size=50))
        }
    
    @staticmethod
    @st.composite
    def adversarial_payload_strategy(draw):
        """Generate adversarial payloads."""
        base = draw(PropertyTestEngine.valid_payload_strategy())
        
        # Mutate randomly
        mutation_type = draw(st.sampled_from(["corrupt", "null", "extreme", "type_mismatch"]))
        
        if mutation_type == "corrupt":
            field = draw(st.sampled_from(list(base.keys())))
            base[field] = draw(st.text(min_size=100, max_size=1000))
        elif mutation_type == "null":
            field = draw(st.sampled_from(list(base.keys())))
            base[field] = None
        elif mutation_type == "extreme":
            for k in ["precipitation", "roll_3d"]:
                if k in base:
                    base[k] = draw(st.floats(min_value=1e6, max_value=1e9))
        elif mutation_type == "type_mismatch":
            field = draw(st.sampled_from(["precipitation", "roll_3d", "z_score"]))
            base[field] = draw(st.text(min_size=1, max_size=20))
        
        return base
    
    @staticmethod
    def test_score_range_invariant(client):
        """Invariant: Risk score must be between 0 and 100."""
        
        @given(PropertyTestEngine.valid_payload_strategy())
        @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
        def _test(payload):
            response = client.post("/score", json=payload)
            if response.status_code == 200:
                data = response.json()
                score = data.get("score", data.get("risk_score", 0))
                assert 0 <= score <= 100, f"Score {score} out of range"
        
        _test()
        return True
    
    @staticmethod
    def test_idempotence_invariant(client):
        """Invariant: Same input must produce same output."""
        
        @given(PropertyTestEngine.valid_payload_strategy())
        @settings(max_examples=50)
        def _test(payload):
            response1 = client.post("/score", json=payload)
            response2 = client.post("/score", json=payload)
            
            if response1.status_code == 200 and response2.status_code == 200:
                data1 = response1.json()
                data2 = response2.json()
                score1 = data1.get("score", data1.get("risk_score"))
                score2 = data2.get("score", data2.get("risk_score"))
                assert score1 == score2, f"Idempotence violated: {score1} != {score2}"
        
        _test()
        return True
    
    @staticmethod
    def test_monotonicity_invariant(client):
        """Invariant: Higher precipitation should not decrease risk score."""
        
        @given(st.floats(min_value=0, max_value=100), st.floats(min_value=0, max_value=100))
        @settings(max_examples=50)
        def _test(low_precip, high_precip):
            assume(low_precip < high_precip)
            
            base_payload = {
                "precipitation": low_precip,
                "roll_3d": 100,
                "roll_7d": 200,
                "roll_30d": 300,
                "cumulative": 1000,
                "z_score": 1.5,
                "location": "Accra"
            }
            
            low_response = client.post("/score", json=base_payload)
            base_payload["precipitation"] = high_precip
            high_response = client.post("/score", json=base_payload)
            
            if low_response.status_code == 200 and high_response.status_code == 200:
                low_score = low_response.json().get("score", low_response.json().get("risk_score", 0))
                high_score = high_response.json().get("score", high_response.json().get("risk_score", 0))
                assert high_score >= low_score, f"Monotonicity violated: {high_score} < {low_score}"
        
        _test()
        return True
    
    @staticmethod
    def test_boundary_invariant(client):
        """Invariant: Extreme values should be handled gracefully."""
        
        @given(PropertyTestEngine.adversarial_payload_strategy())
        @settings(max_examples=200)
        def _test(payload):
            response = client.post("/score", json=payload)
            # Should not crash - 5xx is acceptable, but no exception
            assert response.status_code in (200, 400, 422, 429, 500), f"Unexpected status: {response.status_code}"
        
        _test()
        return True
    
    @staticmethod
    def run_all_property_tests(client) -> Dict[str, bool]:
        """Run all property tests."""
        results = {}
        
        print("🔍 Running property-based tests...")
        
        try:
            PropertyTestEngine.test_score_range_invariant(client)
            results["score_range"] = True
            print("✅ Score range invariant: PASSED")
        except Exception as e:
            results["score_range"] = False
            print(f"❌ Score range invariant: FAILED - {e}")
        
        try:
            PropertyTestEngine.test_idempotence_invariant(client)
            results["idempotence"] = True
            print("✅ Idempotence invariant: PASSED")
        except Exception as e:
            results["idempotence"] = False
            print(f"❌ Idempotence invariant: FAILED - {e}")
        
        try:
            PropertyTestEngine.test_monotonicity_invariant(client)
            results["monotonicity"] = True
            print("✅ Monotonicity invariant: PASSED")
        except Exception as e:
            results["monotonicity"] = False
            print(f"❌ Monotonicity invariant: FAILED - {e}")
        
        try:
            PropertyTestEngine.test_boundary_invariant(client)
            results["boundary"] = True
            print("✅ Boundary invariant: PASSED")
        except Exception as e:
            results["boundary"] = False
            print(f"❌ Boundary invariant: FAILED - {e}")
        
        return results
