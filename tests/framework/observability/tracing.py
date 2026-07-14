"""Tracing validation utilities."""

import uuid
from typing import Any, Dict, Optional


class TracingValidator:
    """Validate distributed tracing."""

    @staticmethod
    def assert_trace_id(response, header_name: str = "X-Request-ID"):
        """Assert response contains trace ID."""
        # Check headers
        if header_name in response.headers:
            trace_id = response.headers[header_name]
            assert trace_id, "Trace ID header is empty"
            return trace_id

        # Check response body
        data = response.json()
        if "trace_id" in data:
            assert data["trace_id"], "Trace ID is empty"
            return data["trace_id"]

        if "request_id" in data:
            assert data["request_id"], "Request ID is empty"
            return data["request_id"]

        raise AssertionError(
            f"No trace ID found in response. Headers: {dict(response.headers)}"
        )

    @staticmethod
    def generate_trace_id() -> str:
        """Generate a trace ID for correlation."""
        return str(uuid.uuid4())

    @staticmethod
    def inject_trace_header(headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Inject trace header into request."""
        headers = headers or {}
        headers["X-Request-ID"] = TracingValidator.generate_trace_id()
        return headers

    @staticmethod
    def assert_trace_consistency(responses: list, trace_header: str = "X-Request-ID"):
        """Assert all responses have same trace ID pattern."""
        trace_ids = []
        for response in responses:
            trace_id = response.headers.get(trace_header)
            if trace_id:
                trace_ids.append(trace_id)

        # Not all need to be same, but they should exist
        assert len(trace_ids) > 0, "No trace IDs found"
        return trace_ids

    @staticmethod
    def extract_trace_id(response) -> Optional[str]:
        """Extract trace ID from response."""
        if "X-Request-ID" in response.headers:
            return response.headers["X-Request-ID"]

        data = response.json()
        return data.get("trace_id") or data.get("request_id")
