# NFCC flood-prediction experiments: results (v1_gfd)

216 districts in 10 regions, 979 weeks (onsets 2003–2018). 203 flood onsets in 68 districts, out of 209,175 scored district-weeks (base rate 0.0010).

Onsets by region: Ashanti 3, Brong Ahafo 19, Central 2, Eastern 18, Greater Accra 18, Northern 71, Upper East 17, Upper West 1, Volta 51, Western 3

Onsets by year: 2003 29, 2004 2, 2006 8, 2007 58, 2009 14, 2010 51, 2011 10, 2015 1, 2018 30

## E1 + E3. Model hierarchy, temporal forward-chaining

POD/FAR ±1 wk count an alert one week early or late as a hit.

| Model | ROC-AUC | PR-AUC (90% CI) | Brier | Precision | Recall | F1 | FAR | MER | SEDI (90% CI) | POD ±1 wk | FAR ±1 wk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Climatology | 0.621 | 0.005 [0.000, 0.020] | 0.0009 | 0.001 | 0.217 | 0.003 | 0.999 | 0.783 | 0.142 [-0.196, 0.576] | 0.217 | 0.997 |
| Persistence | 0.511 | 0.001 [0.000, 0.002] | 0.0068 | 0.001 | 0.236 | 0.001 | 0.999 | 0.764 | -0.205 [-0.535, 0.781] | 0.236 | 0.999 |
| Rainfall threshold (live rule) | 0.765 | 0.003 [0.001, 0.007] | 0.1410 | 0.002 | 0.094 | 0.004 | 0.998 | 0.906 | 0.153 [-0.467, 0.567] | 0.104 | 0.996 |
| River percentile (GloFAS-style) | 0.804 | 0.004 [0.001, 0.016] | 0.4181 | 0.007 | 0.528 | 0.014 | 0.993 | 0.472 | 0.667 [0.319, 0.869] | 0.566 | 0.986 |
| Logistic regression (rainfall) | 0.631 | 0.003 [0.000, 0.009] | 0.0009 | 0.001 | 0.085 | 0.002 | 0.999 | 0.915 | 0.075 [-0.563, 0.471] | 0.104 | 0.997 |
| Random forest (rainfall) | 0.613 | 0.002 [0.000, 0.005] | 0.0009 | 0.001 | 0.094 | 0.002 | 0.999 | 0.906 | -0.016 [-0.540, 0.341] | 0.094 | 0.998 |
| XGBoost (rainfall) | 0.643 | 0.002 [0.000, 0.007] | 0.0009 | 0.002 | 0.189 | 0.003 | 0.998 | 0.811 | 0.162 [-0.631, 0.452] | 0.245 | 0.997 |
| Temporal XGBoost (rain lags + soil state) | 0.652 | 0.002 [0.000, 0.005] | 0.0009 | 0.001 | 0.104 | 0.002 | 0.999 | 0.896 | 0.007 [-0.644, 0.443] | 0.132 | 0.998 |
| Multi-source XGBoost | 0.780 | 0.004 [0.001, 0.015] | 0.0009 | 0.003 | 0.123 | 0.005 | 0.997 | 0.877 | 0.228 [-0.555, 0.614] | 0.302 | 0.991 |

## E3b. One week ahead (inputs known when the week starts)

| Model | ROC-AUC | PR-AUC (90% CI) | Brier | Precision | Recall | F1 | FAR | MER | SEDI (90% CI) | POD ±1 wk | FAR ±1 wk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Nowcast multi-source XGBoost | 0.780 | 0.004 [0.001, 0.015] | 0.0009 | 0.003 | 0.123 | 0.005 | 0.997 | 0.877 | 0.228 [-0.555, 0.614] | 0.302 | 0.991 |
| Forecast logistic regression | 0.611 | 0.004 [0.000, 0.012] | 0.0009 | 0.001 | 0.047 | 0.002 | 0.999 | 0.953 | -0.003 [-0.617, 0.275] | 0.047 | 0.999 |
| Forecast multi-source XGBoost | 0.788 | 0.003 [0.001, 0.007] | 0.0009 | 0.004 | 0.189 | 0.007 | 0.996 | 0.811 | 0.317 [-0.555, 0.511] | 0.453 | 0.989 |

## E3c. Real lead time: archived ECMWF forecasts (test 2024-2025)

Not run: no archived forecasts.

## When vs where, and value to users

Within-district AUC ranks weeks inside each district (0.5 = no timing skill). Peak value: relative economic value at the best cost-loss ratio (Richardson 2000; 1 = perfect, 0 = no better than always/never acting).

| Model | Within-district AUC | Urban PR-AUC (base) | Rural PR-AUC (base) | Peak value | Useful for cost/loss |
| --- | --- | --- | --- | --- | --- |
| Climatology | 0.578 | 0.004 (0.0006) | 0.006 (0.0010) | 0.346 | 0.001–0.02 |
| Persistence | 0.499 | 0.005 (0.0006) | 0.001 (0.0010) | 0.021 | 0.001–0.00 |
| Rainfall threshold (live rule) | 0.781 | 0.005 (0.0006) | 0.003 (0.0010) | 0.375 | 0.001–0.01 |
| River percentile (GloFAS-style) | 0.821 | 0.001 (0.0006) | 0.005 (0.0010) | 0.413 | 0.001–0.01 |
| Logistic regression (rainfall) | 0.635 | 0.001 (0.0006) | 0.003 (0.0010) | 0.266 | 0.001–0.01 |
| Random forest (rainfall) | 0.611 | 0.001 (0.0006) | 0.002 (0.0010) | 0.198 | 0.001–0.00 |
| XGBoost (rainfall) | 0.636 | 0.001 (0.0006) | 0.002 (0.0010) | 0.193 | 0.001–0.00 |
| Temporal XGBoost (rain lags + soil state) | 0.644 | 0.001 (0.0006) | 0.002 (0.0010) | 0.151 | 0.001–0.00 |
| Multi-source XGBoost | 0.670 | 0.005 (0.0006) | 0.005 (0.0010) | 0.442 | 0.001–0.01 |

## E2. Source ablation (XGBoost, temporal)

| Configuration | ROC-AUC | PR-AUC (90% CI) | Brier | Precision | Recall | F1 | FAR | MER | SEDI (90% CI) | POD ±1 wk | FAR ±1 wk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline (rainfall + season) | 0.650 | 0.002 [0.000, 0.005] | 0.0009 | 0.001 | 0.113 | 0.002 | 0.999 | 0.887 | 0.034 [-0.624, 0.452] | 0.160 | 0.998 |
| + Soil moisture | 0.652 | 0.002 [0.000, 0.005] | 0.0009 | 0.001 | 0.104 | 0.002 | 0.999 | 0.896 | 0.007 [-0.644, 0.443] | 0.132 | 0.998 |
| + River (runoff, discharge) | 0.689 | 0.003 [0.000, 0.010] | 0.0009 | 0.003 | 0.321 | 0.005 | 0.997 | 0.679 | 0.347 [-0.644, 0.590] | 0.425 | 0.994 |
| + Dam | not run: No historical dam release or reservoir record exists for Ghana (VRA data never obtained); DAHITI levels start after most labelled events. | | | | | | | | | | |
| + Geographic | 0.772 | 0.004 [0.001, 0.013] | 0.0009 | 0.006 | 0.283 | 0.012 | 0.994 | 0.717 | 0.467 [-0.499, 0.667] | 0.500 | 0.983 |
| + Exposure | 0.780 | 0.004 [0.001, 0.015] | 0.0009 | 0.003 | 0.123 | 0.005 | 0.997 | 0.877 | 0.228 [-0.555, 0.614] | 0.302 | 0.991 |

## E4. Spatial holdout (leave-one-region-out)

| Model | ROC-AUC | PR-AUC (90% CI) | Brier | Precision | Recall | F1 | FAR | MER | SEDI (90% CI) | POD ±1 wk | FAR ±1 wk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Climatology | 0.640 | 0.002 [0.000, 0.006] | 0.0009 | 0.000 | 0.000 | 0.000 | – | 1.000 | -0.000 [-0.000, 0.000] | 0.000 | – |
| Rainfall threshold (live rule) | 0.765 | 0.003 [0.001, 0.007] | 0.1410 | 0.005 | 0.066 | 0.009 | 0.995 | 0.934 | 0.241 [-0.019, 0.505] | 0.094 | 0.993 |
| Logistic regression (rainfall) | 0.763 | 0.002 [0.001, 0.004] | 0.0009 | 0.002 | 0.085 | 0.003 | 0.998 | 0.915 | 0.127 [0.027, 0.276] | 0.094 | 0.998 |
| XGBoost (rainfall) | 0.668 | 0.001 [0.000, 0.002] | 0.0009 | 0.002 | 0.434 | 0.003 | 0.998 | 0.566 | 0.305 [0.053, 0.631] | 0.575 | 0.996 |
| Multi-source XGBoost | 0.708 | 0.002 [0.001, 0.004] | 0.0009 | 0.002 | 0.462 | 0.004 | 0.998 | 0.538 | 0.391 [0.137, 0.604] | 0.613 | 0.995 |

| Model | Held-out region | Onsets | PR-AUC | Base rate |
| --- | --- | --- | --- | --- |
| Climatology | Ashanti | 1 | 0.000 | 0.0001 |
| Climatology | Brong Ahafo | 13 | 0.003 | 0.0008 |
| Climatology | Central | 1 | 0.000 | 0.0001 |
| Climatology | Eastern | 12 | 0.001 | 0.0008 |
| Climatology | Greater Accra | 12 | 0.002 | 0.0013 |
| Climatology | Northern | 31 | 0.012 | 0.0021 |
| Climatology | Upper East | 5 | 0.008 | 0.0007 |
| Climatology | Volta | 28 | 0.004 | 0.0020 |
| Climatology | Western | 3 | 0.001 | 0.0002 |
| Rainfall threshold (live rule) | Ashanti | 1 | 0.000 | 0.0001 |
| Rainfall threshold (live rule) | Brong Ahafo | 13 | 0.001 | 0.0008 |
| Rainfall threshold (live rule) | Central | 1 | 0.005 | 0.0001 |
| Rainfall threshold (live rule) | Eastern | 12 | 0.001 | 0.0008 |
| Rainfall threshold (live rule) | Greater Accra | 12 | 0.015 | 0.0013 |
| Rainfall threshold (live rule) | Northern | 31 | 0.012 | 0.0021 |
| Rainfall threshold (live rule) | Upper East | 5 | 0.061 | 0.0007 |
| Rainfall threshold (live rule) | Volta | 28 | 0.004 | 0.0020 |
| Rainfall threshold (live rule) | Western | 3 | 0.005 | 0.0002 |
| Logistic regression (rainfall) | Ashanti | 1 | 0.000 | 0.0001 |
| Logistic regression (rainfall) | Brong Ahafo | 13 | 0.003 | 0.0008 |
| Logistic regression (rainfall) | Central | 1 | 0.000 | 0.0001 |
| Logistic regression (rainfall) | Eastern | 12 | 0.001 | 0.0008 |
| Logistic regression (rainfall) | Greater Accra | 12 | 0.006 | 0.0013 |
| Logistic regression (rainfall) | Northern | 31 | 0.010 | 0.0021 |
| Logistic regression (rainfall) | Upper East | 5 | 0.005 | 0.0007 |
| Logistic regression (rainfall) | Volta | 28 | 0.004 | 0.0020 |
| Logistic regression (rainfall) | Western | 3 | 0.001 | 0.0002 |
| XGBoost (rainfall) | Ashanti | 1 | 0.000 | 0.0001 |
| XGBoost (rainfall) | Brong Ahafo | 13 | 0.002 | 0.0008 |
| XGBoost (rainfall) | Central | 1 | 0.000 | 0.0001 |
| XGBoost (rainfall) | Eastern | 12 | 0.002 | 0.0008 |
| XGBoost (rainfall) | Greater Accra | 12 | 0.004 | 0.0013 |
| XGBoost (rainfall) | Northern | 31 | 0.002 | 0.0021 |
| XGBoost (rainfall) | Upper East | 5 | 0.003 | 0.0007 |
| XGBoost (rainfall) | Volta | 28 | 0.006 | 0.0020 |
| XGBoost (rainfall) | Western | 3 | 0.001 | 0.0002 |
| Multi-source XGBoost | Ashanti | 1 | 0.000 | 0.0001 |
| Multi-source XGBoost | Brong Ahafo | 13 | 0.005 | 0.0008 |
| Multi-source XGBoost | Central | 1 | 0.000 | 0.0001 |
| Multi-source XGBoost | Eastern | 12 | 0.002 | 0.0008 |
| Multi-source XGBoost | Greater Accra | 12 | 0.004 | 0.0013 |
| Multi-source XGBoost | Northern | 31 | 0.002 | 0.0021 |
| Multi-source XGBoost | Upper East | 5 | 0.004 | 0.0007 |
| Multi-source XGBoost | Volta | 28 | 0.005 | 0.0020 |
| Multi-source XGBoost | Western | 3 | 0.000 | 0.0002 |

## E5. Fusion strategy (temporal)

| Strategy | ROC-AUC | PR-AUC (90% CI) | Brier | Precision | Recall | F1 | FAR | MER | SEDI (90% CI) | POD ±1 wk | FAR ±1 wk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Early fusion (multi-source XGBoost) | 0.780 | 0.004 [0.001, 0.015] | 0.0009 | 0.003 | 0.123 | 0.005 | 0.997 | 0.877 | 0.228 [-0.555, 0.614] | 0.302 | 0.991 |
| Late fusion (mean) | 0.688 | 0.004 [0.000, 0.018] | 0.0009 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | -0.670 [-0.742, -0.445] | 0.019 | 1.000 |
| Stacking (logistic meta-model) | 0.544 | 0.001 [0.000, 0.002] | 0.0009 | 0.000 | 0.057 | 0.001 | 1.000 | 0.943 | -0.205 [-0.813, 0.137] | 0.113 | 0.999 |
| Platform hand-set weights | 0.831 | 0.004 [0.001, 0.010] | 0.2080 | 0.003 | 0.085 | 0.006 | 0.997 | 0.915 | 0.223 [-0.443, 0.589] | 0.094 | 0.994 |

## E6. Source degradation (multi-source XGBoost, temporal)

| Condition | PR-AUC | Δ PR-AUC |
| --- | --- | --- |
| All sources | 0.004 | 0.000 |
| Rainfall missing | 0.001 | -0.003 |
| Rainfall one week stale | 0.004 | -0.000 |
| Soil moisture missing | 0.004 | -0.000 |
| Soil moisture one week stale | 0.004 | 0.000 |
| River (runoff, discharge) missing | 0.003 | -0.002 |
| River (runoff, discharge) one week stale | 0.005 | 0.000 |
| Geographic + exposure missing | 0.001 | -0.003 |

## E7. Calibration (multi-source XGBoost, temporal)

| Method | Brier | ECE | PR-AUC |
| --- | --- | --- | --- |
| Raw | 0.00091 | 0.00073 | 0.004 |
| Platt scaling | 0.00091 | 0.00115 | 0.003 |
| Isotonic | 0.00091 | 0.00128 | 0.003 |

## E9. SHAP fidelity and stability (train ≤ 2012, test 2014-2018)

| Feature | Mean abs SHAP |
| --- | --- |
| perm_water_frac | 1.0909 |
| woy_sin | 0.7821 |
| slope_mean | 0.5936 |
| woy_cos | 0.5839 |
| rain_lag1 | 0.5128 |
| runoff_week_sum | 0.4785 |
| q_ratio | 0.4569 |
| rain_week_max | 0.4250 |
| rain_lag2 | 0.3013 |
| built_frac | 0.2628 |
| rain_lag4 | 0.1995 |
| rain_prev4w_sum | 0.1524 |
| log_pop_density | 0.1305 |
| rain_lag3 | 0.0939 |
| rain_week_sum | 0.0879 |
| sm_week_mean | 0.0847 |
| elev_mean | 0.0770 |
| runoff_prev4w_sum | 0.0622 |
| q_week_max_log | 0.0167 |
| sm_start | 0.0108 |

| Features removed (k) | Mean abs change, top-SHAP | Mean abs change, random |
| --- | --- | --- |
| 1 | 0.0078 | 0.0031 |
| 3 | 0.0096 | 0.0069 |
| 5 | 0.0097 | 0.0082 |

Global-importance rank stability across bootstrap retrainings: mean Spearman ρ 0.885 (min 0.782, 10 pairs).

## Not runnable

- E8 impact layers: Needs people-affected counts per district per event; open sources (DFO, EM-DAT, ReliefWeb) report them per event or per country only.
- + Dam ablation step: no historical dam or reservoir record for Ghana.
- Human decision, warning-policy and incorrect-AI studies: need recruited participants and ethics approval.
