"""Turns a caught request exception into a message safe to log or
return to a client - never the exception's raw str(), which for a
requests.exceptions.RequestException includes the full request URL. A
security audit found src/hydrology/dam_intelligence.py and
river_level_intelligence.py building DAHITI requests with the real
DAHITI_API_KEY directly in the URL's query string
(params={"api_key": ...}) and then, on any failure, logging - and,
worse, returning in the live /situation API response body's "reason"
field - f"...{e}" verbatim. requests.exceptions.HTTPError's message
includes the exact URL that was requested, so every DAHITI hiccup (a
bad key, downtime, a rate limit) would have written the real API key
in plaintext into Cloud Run logs and into any client's HTTP response.
"""

import requests


def safe_error_message(e: Exception, service_name: str) -> str:
    """A short, secret-free description of what went wrong - the
    exception's type and, for an HTTP error, its status code, but never
    anything derived from the request URL or its query parameters."""
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        return f"{service_name} returned HTTP {e.response.status_code}"
    if isinstance(e, requests.exceptions.Timeout):
        return f"{service_name} request timed out"
    if isinstance(e, requests.exceptions.ConnectionError):
        return f"{service_name} connection failed"
    return f"{service_name} request failed ({type(e).__name__})"
