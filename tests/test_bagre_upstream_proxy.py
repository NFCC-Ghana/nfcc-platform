"""Regression tests for dam_intelligence.py's Bagre Dam upstream proxy -
real river level from DAHITI's Nakembé station (~22.4km from the dam,
same Nakambé/White Volta watershed), added as supplementary evidence
without changing Bagre's own `available` status (no official dam
operator data exists, and this proxy doesn't change that fact)."""

from src.hydrology.dam_intelligence import get_bagre_status, get_kompienga_status


def test_bagre_still_reports_unavailable_at_top_level():
    """The dam's own official status must still honestly report
    unavailable - the upstream proxy is real, but it is not official
    Bagre operator telemetry, and must never be conflated with it."""
    result = get_bagre_status()
    assert result["available"] is False
    assert "upstream_proxy" in result


def test_bagre_upstream_proxy_is_structurally_distinct():
    """The proxy must carry its own available flag, separate from the
    dam's top-level available=False, so a consumer can tell "the dam
    itself has no data" apart from "but here's a real nearby reading"."""
    result = get_bagre_status()
    proxy = result["upstream_proxy"]
    assert "available" in proxy
    assert "official" not in proxy.get("note", "").lower() or "not official" in proxy.get(
        "note", ""
    ).lower()


def test_kompienga_has_no_upstream_proxy():
    """Kompienga Dam sits on the Ouale/Pendjari-Oti watershed, a
    completely different river system from Nakembé/White Volta -
    despite being geographically close to the same DAHITI station,
    using it as a Kompienga proxy would be hydrologically wrong. Must
    never be added here."""
    result = get_kompienga_status()
    assert "upstream_proxy" not in result
