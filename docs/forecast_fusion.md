# Forecast fusion

This document describes the **additive** multi-source forecast fusion layer. It does not replace or alter the existing `/score` rainfall endpoint or the alert engine.

## Data contract

Each upstream product (CHIRPS-derived, GloFAS-style, Google Flood Hub–style) must be mapped to a **normalized risk score between 0 and 100** before calling the fusion API:

| Field | Meaning |
|-------|--------|
| `chirps_risk` | Rainfall / hydrology signal mapped to 0–100 risk |
| `glofas_risk` | River / discharge exceedance signal mapped to 0–100 |
| `flood_hub_risk` | Public flood guidance / inundation likelihood mapped to 0–100 |

Omit a field or send JSON `null` when that source is unavailable for the location or time. The fusion reweights over **present** sources only.

## Fusion model

Default fusion is a **weighted mean**:

\[
\text{unified} = \frac{\sum_i w_i m_i x_i}{\sum_i w_i m_i}
\]

- \(x_i\): clipped source risk in \([0,100]\)
- \(m_i \in \{0,1\}\): presence mask
- \(w_i\): positive weights from environment (defaults 1,1,1):

- `FUSION_WEIGHT_CHIRPS`
- `FUSION_WEIGHT_GLOFAS`
- `FUSION_WEIGHT_FLOOD_HUB`

## Confidence (0–100)

Confidence blends:

1. **Coverage** — more sources present increases the score.
2. **Agreement** — lower spread among present `x_i` increases the score.

Optional tuning: `FUSION_CONFIDENCE_MAX_SPREAD` (default `50.0`) scales how fast disagreement reduces confidence.

## SHAP explanations

`/explain/forecast` uses SHAP `KernelExplainer` on the same fusion function, with a reference vector defaulting to 50 per source. Values attribute how each **active** source moves the fused risk away from the baseline expectation.

## Historical accuracy

Run:

```bash
python scripts/validate_forecast_accuracy.py path/to/labeled.csv --target realized_risk --out data/forecast_accuracy/metrics.json
```

Expected columns:

- `chirps_risk`, `glofas_risk`, `flood_hub_risk` (each optional / nullable)
- `realized_risk` (or pass `--target`) with observed outcome on 0–100

The script prints JSON with `mae`, `rmse`, and `bias`.

## Tests (forecast fusion and model intelligence only)

These files cover fusion math, confidence, SHAP explain helpers, and the `/forecast/confidence` and `/explain/forecast` routes. They do **not** include SMS/WhatsApp/email provider unit tests or other alert stack tests.

```bash
pytest tests/unit/test_forecast_fusion.py tests/integration/test_forecast_api.py -v
```

Use this when you want a green bar for the **Forecast Fusion & Model Intelligence** slice only. A full `pytest` run may still report failures in unrelated modules (for example provider mocks when Twilio is in MOCK MODE).
