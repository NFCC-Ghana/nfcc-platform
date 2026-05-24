"""State corruption testing for shared state."""

import threading
import random
from typing import Any, Dict, List


class StateCorruptor:
    """Corrupt shared state during concurrent access."""

    @staticmethod
    def race_condition_test(
        func: callable, n_threads: int = 10, n_operations: int = 100
    ):
        """Test for race conditions by running concurrent operations."""
        results = []
        errors = []

        def worker():
            for _ in range(n_operations):
                try:
                    result = func()
                    results.append(result)
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        return {
            "total_operations": n_threads * n_operations,
            "successful": len(results),
            "errors": len(errors),
            "unique_results": len(set(results)) if results else 0,
        }

    @staticmethod
    def cache_poisoning(cache: Dict, key: str, corrupt_value: Any):
        """Attempt to corrupt cache."""
        original = cache.get(key)
        cache[key] = corrupt_value
        return {"key": key, "original": original, "corrupted": corrupt_value}

    @staticmethod
    def rate_limiter_drift_test(rate_limiter, location: str, n_requests: int = 100):
        """Test rate limiter state under concurrent access."""
        import time

        results = []
        errors = []

        def send_request():
            try:
                if rate_limiter.can_send(location):
                    rate_limiter.record_send(location)
                    results.append(True)
                else:
                    results.append(False)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=send_request) for _ in range(n_requests)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        total_success = sum(results)
        return {
            "total_requests": n_requests,
            "successful_sends": total_success,
            "errors": len(errors),
            "rate_limiter_state": len(rate_limiter.alerts.get(location, [])),
        }
