"""Injection attack testing utilities."""

from typing import Dict, Any, List


class InjectionTester:
    """Test injection vulnerabilities."""

    @staticmethod
    def sql_injection_payloads() -> List[Dict[str, Any]]:
        """Generate SQL injection payloads."""
        injections = [
            {"location": "' OR '1'='1"},
            {"location": "'; DROP TABLE users; --"},
            {"location": "1' UNION SELECT NULL--"},
            {"precipitation": "10; WAITFOR DELAY '00:00:05'"},
            {"precipitation": "10' OR '1'='1"},
            {"roll_3d": "1 AND 1=1"},
            {"roll_7d": "1 AND 1=2"},
        ]

        return [
            {
                "precipitation": 10,
                "roll_3d": 10,
                "roll_7d": 20,
                "roll_30d": 30,
                "cumulative": 100,
                "z_score": 1.5,
                **injection,
            }
            for injection in injections
        ]

    @staticmethod
    def nosql_injection_payloads() -> List[Dict[str, Any]]:
        """Generate NoSQL injection payloads."""
        injections = [
            {"location": {"$ne": None}},
            {"location": {"$gt": ""}},
            {"precipitation": {"$gt": 0}},
            {"precipitation": {"$regex": ".*"}},
            {"roll_3d": {"$in": [1, 2, 3]}},
            {"$where": "function() { return true; }"},
        ]

        return [
            {
                "precipitation": 10,
                "roll_3d": 10,
                "roll_7d": 20,
                "roll_30d": 30,
                "cumulative": 100,
                "z_score": 1.5,
                **injection,
            }
            for injection in injections
        ]

    @staticmethod
    def xss_injection_payloads() -> List[Dict[str, Any]]:
        """Generate XSS injection payloads."""
        injections = [
            {"location": "<script>alert('XSS')</script>"},
            {"location": "<img src=x onerror=alert(1)>"},
            {"location": "javascript:alert('XSS')"},
            {"location": "<svg onload=alert(1)>"},
            {"location": "';alert('XSS');//"},
        ]

        return [
            {
                "precipitation": 10,
                "roll_3d": 10,
                "roll_7d": 20,
                "roll_30d": 30,
                "cumulative": 100,
                "z_score": 1.5,
                **injection,
            }
            for injection in injections
        ]

    @staticmethod
    def path_traversal_payloads() -> List[Dict[str, Any]]:
        """Generate path traversal payloads."""
        injections = [
            {"location": "../../../etc/passwd"},
            {"location": "..\\..\\..\\windows\\win.ini"},
            {"location": "%2e%2e%2f%2e%2e%2f"},
            {"location": "....//....//....//etc/passwd"},
        ]

        return [
            {
                "precipitation": 10,
                "roll_3d": 10,
                "roll_7d": 20,
                "roll_30d": 30,
                "cumulative": 100,
                "z_score": 1.5,
                **injection,
            }
            for injection in injections
        ]

    @staticmethod
    def assert_no_injection_success(response):
        """Assert injection attempt didn't succeed."""
        # Should either reject or fail safely
        assert response.status_code in (
            200,
            400,
            422,
            403,
            401,
        ), f"Injection may have succeeded: {response.status_code}"
        return True
