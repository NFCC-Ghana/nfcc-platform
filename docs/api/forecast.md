# Forecast fusion API

New endpoints are mounted alongside the existing API. They **do not** change `/score` or `/score/batch`.

## POST `/forecast/confidence`

Fuse normalized multi-source risks and return a **unified risk** (0–100) plus **confidence** (0–100).

### Request body (JSON)

| Field | Type | Description |
|-------|------|---------------|
| `location` | string | Label (e.g. district name) |
| `chirps_risk` | number or null | 0–100 normalized CHIRPS-side risk |
| `glofas_risk` | number or null | 0–100 GloFAS-style risk |
| `flood_hub_risk` | number or null | 0–100 Flood Hub–style risk |

### Example

```json
{
  "location": "Accra Central",
  "chirps_risk": 40,
  "glofas_risk": 60,
  "flood_hub_risk": 50
}
```

### Response (success)

- `unified_risk` — fused 0–100 risk  
- `confidence` — 0–100 confidence  
- `confidence_breakdown` — `coverage_factor`, `agreement_factor`, `num_sources`  
- `sources` — echoes inputs plus `present` / `missing` source keys  
- `fusion_weights` — weights used for each source  

## POST `/explain/forecast`

SHAP attribution for the same fusion inputs.

### Request body (JSON)

Same three risk fields as above, plus:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `nsamples` | int | 64 | KernelExplainer sample count (8–400) |

### Response (success)

- `unified_risk` — fused risk  
- `expected_value` — baseline expectation from the explainer  
- `shap_values` — per-source SHAP contributions (`chirps`, `glofas`, `flood_hub`)  
- `baseline` — reference values used for each source (default 50)  
- `summary` — short text ranking contributions  

## Validation errors

Sending a risk outside `[0, 100]` returns **422** with FastAPI validation detail.

For full platform behavior, see [forecast_fusion.md](../forecast_fusion.md).
