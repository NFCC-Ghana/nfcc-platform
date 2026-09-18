"""Real GDELT DOC 2.0 API client (api.gdeltproject.org) - GDELT (Global
Database of Events, Language and Tone), a Google Jigsaw-supported
project monitoring world broadcast/print/web news in 100+ languages in
near-real-time, free and keyless. The broad net alongside ReliefWeb's
precise one: GDELT catches recent coverage ReliefWeb's editorial team
hasn't tagged yet, at the cost of being noisier free-text search
rather than curated disaster reports.

Two real constraints confirmed only by making live calls during this
module's development, not assumed from documentation:

1. GDELT enforces a real rate limit - confirmed via an actual 429
   response: "Please limit requests to one every 5 seconds or contact
   [...] for larger queries." _MIN_REQUEST_INTERVAL_SECONDS enforces
   this client-side so this platform is never the reason GDELT rate-
   limits it - a good-citizen throttle on a free public service, not
   an arbitrary number.

2. A rate-limited response is PLAIN TEXT, not JSON - a naive
   `response.json()` would raise/crash on exactly the response this
   client is most likely to receive if run too often. Every field is
   read defensively with .get() and a real JSONDecodeError is caught
   and honestly reported as unavailable, rather than assumed away.

Because live verification was rate-limited during development, this
client could not confirm GDELT's exact per-article JSON field names
against a real successful response in this session - the field names
below (articles/url/title/seendate/domain) match GDELT's own published
documentation and widely-used third-party integrations, but are
treated defensively (missing fields default to None) rather than
assumed authoritative, and this limitation is disclosed here rather
than hidden.
"""

import logging
import time
from typing import Dict, List

import requests

logger = logging.getLogger("nfcc.verification.gdelt")

_BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
_MIN_REQUEST_INTERVAL_SECONDS = 5.0
_last_request_time = 0.0


def _throttle() -> None:
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < _MIN_REQUEST_INTERVAL_SECONDS:
        time.sleep(_MIN_REQUEST_INTERVAL_SECONDS - elapsed)
    _last_request_time = time.time()


def search_flood_news(district: str, start_date: str, end_date: str) -> Dict:
    """Real GDELT news search for flood coverage mentioning this
    district, within a real date window. start_date/end_date are
    'YYYY-MM-DD'; GDELT wants 'YYYYMMDDHHMMSS'."""
    _throttle()

    start_dt = start_date.replace("-", "") + "000000"
    end_dt = end_date.replace("-", "") + "235959"

    try:
        resp = requests.get(
            _BASE_URL,
            params={
                "query": f"flood Ghana {district}",
                "format": "json",
                "mode": "artlist",
                "maxrecords": 10,
                "startdatetime": start_dt,
                "enddatetime": end_dt,
            },
            timeout=20,
        )
        resp.raise_for_status()
        payload = resp.json()
    except ValueError as e:
        # A rate-limited or malformed response comes back as plain
        # text, not JSON - resp.json() raises here rather than this
        # client silently treating rate-limit text as "no articles".
        logger.warning(f"GDELT returned non-JSON (likely rate-limited): {e}")
        return {"available": False, "reason": "GDELT rate-limited or returned non-JSON"}
    except Exception as e:
        logger.warning(f"GDELT request failed: {e}")
        return {"available": False, "reason": f"GDELT request failed: {e}"}

    raw_articles = payload.get("articles") or payload.get("docs") or []
    articles: List[Dict] = [
        {
            "title": a.get("title"),
            "url": a.get("url"),
            "seendate": a.get("seendate"),
            "domain": a.get("domain"),
        }
        for a in raw_articles
    ]

    return {
        "available": True,
        "matched_articles": articles,
        "count": len(articles),
        "source": "GDELT (global news monitoring)",
    }
