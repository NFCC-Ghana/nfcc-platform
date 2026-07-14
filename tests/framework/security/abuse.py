"""Abuse testing utilities."""

import random
import string
from typing import Any, Dict, List


class AbuseTester:
    """Test API abuse scenarios."""

    @staticmethod
    def header_injection_payloads() -> List[Dict[str, str]]:
        """Generate header injection payloads."""
        return [
            {"X-Forwarded-For": "127.0.0.1, 192.168.1.1"},
            {"X-Forwarded-For": "evil.com"},
            {"User-Agent": "'; DROP TABLE--"},
            {"Content-Type": "application/x-www-form-urlencoded"},
            {"Content-Length": "9999999999"},
            {"Host": "evil.com"},
            {"Origin": "https://evil.com"},
            {"Referer": "https://evil.com"},
        ]

    @staticmethod
    def encoding_attack_payloads() -> List[Dict[str, Any]]:
        """Generate encoding attack payloads."""
        return [
            {"location": "\x00null\x00"},
            {"location": "%00null%00"},
            {"precipitation": "NaN"},
            {"precipitation": "Infinity"},
            {"precipitation": "-Infinity"},
            {"z_score": "NaN"},
        ]

    @staticmethod
    def rate_limit_abuse(
        client, endpoint: str, payload: Dict[str, Any], n_requests: int = 1000
    ):
        """Test rate limiting under abuse."""
        results = []

        for i in range(n_requests):
            response = client.post(endpoint, json=payload)
            results.append(response.status_code)

            # Small delay to avoid overwhelming
            if i % 100 == 0:
                import time

                time.sleep(0.01)

        status_counts = {}
        for status in results:
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_requests": n_requests,
            "status_counts": status_counts,
            "rate_limited": status_counts.get(429, 0),
            "successful": status_counts.get(200, 0),
        }

    @staticmethod
    def concurrent_abuse(
        client,
        endpoint: str,
        payload: Dict[str, Any],
        n_threads: int = 10,
        n_per_thread: int = 100,
    ):
        """Test concurrent abuse."""
        import threading

        results = []
        lock = threading.Lock()

        def worker():
            local_results = []
            for _ in range(n_per_thread):
                response = client.post(endpoint, json=payload)
                local_results.append(response.status_code)
            with lock:
                results.extend(local_results)

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        status_counts = {}
        for status in results:
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_requests": n_threads * n_per_thread,
            "status_counts": status_counts,
            "successful": status_counts.get(200, 0),
        }
