"""Shared fluvial (river/dam) pathway construction - real river gauge
and dam/upstream-proxy readings mapped to comparable 0-100 risk bands
via src/hydrology/altimetry_thresholds.py's percentile classification.

Used by BOTH POST /decision/card (src/api/routes/decision_card.py,
reusing an already-fetched /situation dict so this doesn't double a
live DAHITI call) and GET /v1/districts/{district}/fluvial-risk
(src/api/v1/fluvial_risk.py, a standalone check with NO rainfall
dependency at all).

That second, independent path matters for a real reason, not a
hypothetical one: scripts/automated_risk_assessment.py (the actual
scheduled production alerting pipeline) previously only ever scored
rainfall/antecedent-rainfall - a pure dam-release flood with zero local
rain, like Ghana's own real 2023 Akosombo spillage or the 2021/2010
Bagre-driven Tamale floods already in this platform's
flood_polygons.py history, would never have crossed its review
threshold at all. Real flood science and real dam-release warning
practice both treat rainfall-driven (pluvial) and dam/river-driven
(fluvial) flooding as independent causal pathways (see
src/models/multi_source_confidence.py's module docstring for the full
citations) - the fluvial pathway needs to be checkable, and alertable,
entirely on its own.
"""

from typing import Dict, List

from src.models.multi_source_confidence import (
    DAM_DIRECT_WEIGHT,
    DAM_UPSTREAM_PROXY_WEIGHT,
    RIVER_GAUGE_WEIGHT,
    SourceReading,
)

# Real, data-derived percentile thresholds (src/hydrology/
# altimetry_thresholds.py) mapped to a comparable 0-100 risk band -
# shared by river gauges and dam/upstream-proxy levels, since both are
# now classified into the same NORMAL/WARNING/DANGER/FLOOD bands from
# each water body's own historical DAHITI series.
ALTIMETRY_STATUS_RISK = {
    "NORMAL": 15.0,
    "WARNING": 45.0,
    "DANGER": 75.0,
    "FLOOD": 95.0,
}


def build_fluvial_sources(
    river_gauge: Dict, dam_intelligence: List[Dict], river_applicable: bool
) -> List[SourceReading]:
    """Pure mapping - takes already-fetched real river/dam dicts (from
    river_level_intelligence.get_river_level_for_district and
    dam_intelligence.get_dam_intelligence_for_district) and returns the
    SourceReadings for the fluvial pathway. Does no I/O itself, so
    callers control whether that data comes from an already-fetched
    /situation response or a fresh standalone call."""
    river_risk = ALTIMETRY_STATUS_RISK.get(river_gauge.get("status"))
    sources: List[SourceReading] = [
        SourceReading(
            name="river_gauge",
            display_name="river levels",
            applicable=river_applicable,
            available=bool(river_gauge.get("available")) and river_risk is not None,
            risk_0_100=river_risk,
            weight=RIVER_GAUGE_WEIGHT,
            unavailable_reason=river_gauge.get("reason"),
        )
    ]

    for dam in dam_intelligence:
        dam_name = dam.get("dam", "unknown")
        dam_risk = ALTIMETRY_STATUS_RISK.get(dam.get("status"))
        dam_available = bool(dam.get("available")) and dam_risk is not None
        sources.append(
            SourceReading(
                name=f"dam_{dam_name.lower()}",
                display_name=f"{dam_name} Dam level",
                applicable=True,
                available=dam_available,
                risk_0_100=dam_risk if dam_available else None,
                weight=DAM_DIRECT_WEIGHT,
                unavailable_reason=dam.get("reason"),
            )
        )
        proxy = dam.get("upstream_proxy")
        if proxy:
            proxy_risk = ALTIMETRY_STATUS_RISK.get(proxy.get("status"))
            proxy_available = bool(proxy.get("available")) and proxy_risk is not None
            sources.append(
                SourceReading(
                    name=f"dam_{dam_name.lower()}_upstream_proxy",
                    display_name=f"{dam_name} upstream river proxy",
                    applicable=True,
                    available=proxy_available,
                    risk_0_100=proxy_risk if proxy_available else None,
                    weight=DAM_UPSTREAM_PROXY_WEIGHT,
                    unavailable_reason=proxy.get("reason"),
                )
            )

    return sources
