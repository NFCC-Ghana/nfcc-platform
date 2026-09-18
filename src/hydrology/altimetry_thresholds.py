"""Real, data-derived reference levels and status classification shared
by every real DAHITI satellite altimetry consumer (river gauges, dam
water levels) - extracted from river_level_intelligence.py so
dam_intelligence.py can apply the exact same real methodology to real
dam/upstream-proxy historical series instead of leaving them
unclassified (see multi_source_confidence.py's causal-independence
redesign: a dam pathway needs a real risk band the same way the river
pathway already has one, or dam-driven flooding stays invisible to any
system that fuses evidence into a risk number)."""

from typing import Dict, List, Optional


def compute_relative_thresholds(readings: List[dict]) -> Optional[Dict[str, float]]:
    """Real, data-derived reference levels from this water body's own
    full historical DAHITI series - not arbitrary constants. baseline =
    5th percentile (typical dry-season/low-pool low); warning/danger/
    flood_stage = 75th/90th/95th percentiles of the same real
    distribution, expressed relative to baseline. Needs at least 20
    real readings to be statistically meaningful; returns None
    otherwise rather than guessing from too little data."""
    elevations = sorted(r["wse"] for r in readings if r.get("wse") is not None)
    n = len(elevations)
    if n < 20:
        return None

    def pct(p: float) -> float:
        return elevations[min(int(n * p), n - 1)]

    baseline = pct(0.05)
    return {
        "baseline_m": round(baseline, 3),
        "warning_level_m": round(pct(0.75) - baseline, 3),
        "danger_level_m": round(pct(0.90) - baseline, 3),
        "flood_stage_m": round(pct(0.95) - baseline, 3),
    }


def classify_level(elevation: float, thresholds: Dict[str, float]) -> Dict:
    """Real elevation -> (level_above_baseline_m, status) using the
    thresholds above. status is one of NORMAL/WARNING/DANGER/FLOOD -
    the same 0-100 risk band decision_card.py's _RIVER_STATUS_RISK
    (and, now, its dam equivalent) map onto a comparable risk score."""
    level_above_baseline = round(elevation - thresholds["baseline_m"], 3)
    if level_above_baseline >= thresholds["flood_stage_m"]:
        status = "FLOOD"
    elif level_above_baseline >= thresholds["danger_level_m"]:
        status = "DANGER"
    elif level_above_baseline >= thresholds["warning_level_m"]:
        status = "WARNING"
    else:
        status = "NORMAL"
    return {"level_above_baseline_m": level_above_baseline, "status": status}
