# NFCC flood-prediction experiments: results (v2)

216 districts in 10 regions, 573 weeks (onsets 2015–2025). 898 flood onsets in 167 districts, out of 121,755 scored district-weeks (base rate 0.0074).

Onsets by region: Ashanti 107, Brong Ahafo 22, Central 103, Eastern 67, Greater Accra 251, Northern 90, Upper East 63, Upper West 27, Volta 103, Western 65

Onsets by year: 2015 40, 2016 41, 2017 67, 2018 91, 2019 83, 2020 78, 2021 80, 2022 117, 2023 135, 2024 68, 2025 98

Groundsource events in Ghana: 2686; placed in a district: 2527; dropped as region- or country-level: 159. Flood weeks by label: news 1149. Sentinel-1 labels pending.

## E1 + E3. Model hierarchy, temporal forward-chaining

POD/FAR ±1 wk count an alert one week early or late as a hit.

| Model | ROC-AUC | PR-AUC (90% CI) | Brier | Precision | Recall | F1 | FAR | MER | SEDI (90% CI) | POD ±1 wk | FAR ±1 wk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Climatology | 0.764 | 0.048 [0.038, 0.059] | 0.0082 | 0.100 | 0.132 | 0.114 | 0.900 | 0.868 | 0.399 [0.364, 0.441] | 0.149 | 0.817 |
| Persistence | 0.609 | 0.018 [0.013, 0.024] | 0.0534 | 0.045 | 0.265 | 0.077 | 0.955 | 0.735 | 0.418 [0.337, 0.479] | 0.268 | 0.922 |
| Rainfall threshold (live rule) | 0.775 | 0.030 [0.022, 0.038] | 0.1487 | 0.041 | 0.113 | 0.060 | 0.959 | 0.887 | 0.280 [0.204, 0.334] | 0.149 | 0.938 |
| River percentile (GloFAS-style) | 0.740 | 0.025 [0.020, 0.031] | 0.3287 | 0.038 | 0.177 | 0.063 | 0.962 | 0.823 | 0.324 [0.224, 0.410] | 0.200 | 0.941 |
| Logistic regression (rainfall) | 0.765 | 0.043 [0.026, 0.061] | 0.0082 | 0.024 | 0.233 | 0.044 | 0.976 | 0.767 | 0.289 [0.211, 0.412] | 0.283 | 0.960 |
| Random forest (rainfall) | 0.747 | 0.028 [0.019, 0.039] | 0.0083 | 0.034 | 0.145 | 0.055 | 0.966 | 0.855 | 0.281 [0.153, 0.388] | 0.200 | 0.943 |
| XGBoost (rainfall) | 0.745 | 0.025 [0.019, 0.032] | 0.0083 | 0.036 | 0.208 | 0.061 | 0.964 | 0.792 | 0.338 [0.235, 0.433] | 0.283 | 0.942 |
| Temporal XGBoost (rain lags + soil state) | 0.724 | 0.022 [0.018, 0.028] | 0.0083 | 0.030 | 0.155 | 0.050 | 0.970 | 0.845 | 0.269 [0.174, 0.366] | 0.205 | 0.954 |
| Multi-source XGBoost | 0.834 | 0.072 [0.058, 0.091] | 0.0081 | 0.131 | 0.159 | 0.144 | 0.869 | 0.841 | 0.451 [0.405, 0.499] | 0.183 | 0.808 |

## E3b. One week ahead (inputs known when the week starts)

| Model | ROC-AUC | PR-AUC (90% CI) | Brier | Precision | Recall | F1 | FAR | MER | SEDI (90% CI) | POD ±1 wk | FAR ±1 wk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Nowcast multi-source XGBoost | 0.834 | 0.072 [0.058, 0.091] | 0.0081 | 0.131 | 0.159 | 0.144 | 0.869 | 0.841 | 0.451 [0.405, 0.499] | 0.183 | 0.808 |
| Forecast logistic regression | 0.811 | 0.044 [0.038, 0.053] | 0.0083 | 0.079 | 0.125 | 0.097 | 0.921 | 0.875 | 0.368 [0.312, 0.420] | 0.149 | 0.849 |
| Forecast multi-source XGBoost | 0.791 | 0.047 [0.035, 0.065] | 0.0082 | 0.074 | 0.172 | 0.103 | 0.926 | 0.828 | 0.404 [0.334, 0.467] | 0.212 | 0.854 |

## E2. Source ablation (XGBoost, temporal)

| Configuration | ROC-AUC | PR-AUC (90% CI) | Brier | Precision | Recall | F1 | FAR | MER | SEDI (90% CI) | POD ±1 wk | FAR ±1 wk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline (rainfall + season) | 0.717 | 0.023 [0.017, 0.029] | 0.0083 | 0.029 | 0.144 | 0.048 | 0.971 | 0.856 | 0.258 [0.172, 0.359] | 0.196 | 0.955 |
| + Soil moisture | 0.724 | 0.022 [0.018, 0.028] | 0.0083 | 0.030 | 0.155 | 0.050 | 0.970 | 0.845 | 0.269 [0.174, 0.366] | 0.205 | 0.954 |
| + River (runoff, discharge) | 0.746 | 0.033 [0.020, 0.049] | 0.0083 | 0.039 | 0.229 | 0.066 | 0.961 | 0.771 | 0.368 [0.271, 0.461] | 0.295 | 0.941 |
| + Dam | not run: No historical dam release or reservoir record exists for Ghana (VRA data never obtained); DAHITI levels start after most labelled events. | | | | | | | | | | |
| + Geographic | 0.842 | 0.079 [0.063, 0.099] | 0.0081 | 0.135 | 0.172 | 0.151 | 0.865 | 0.828 | 0.466 [0.414, 0.511] | 0.199 | 0.807 |
| + Exposure | 0.834 | 0.072 [0.058, 0.091] | 0.0081 | 0.131 | 0.159 | 0.144 | 0.869 | 0.841 | 0.451 [0.405, 0.499] | 0.183 | 0.808 |

## E4. Spatial holdout (leave-one-region-out)

| Model | ROC-AUC | PR-AUC (90% CI) | Brier | Precision | Recall | F1 | FAR | MER | SEDI (90% CI) | POD ±1 wk | FAR ±1 wk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Climatology | 0.643 | 0.012 [0.010, 0.015] | 0.0084 | 0.000 | 0.000 | 0.000 | – | 1.000 | -0.000 [-0.000, 0.000] | 0.000 | – |
| Rainfall threshold (live rule) | 0.775 | 0.030 [0.022, 0.038] | 0.1487 | 0.029 | 0.111 | 0.045 | 0.971 | 0.889 | 0.229 [0.162, 0.281] | 0.132 | 0.957 |
| Logistic regression (rainfall) | 0.711 | 0.038 [0.021, 0.055] | 0.0083 | 0.025 | 0.225 | 0.045 | 0.975 | 0.775 | 0.290 [0.208, 0.361] | 0.313 | 0.959 |
| XGBoost (rainfall) | 0.695 | 0.021 [0.016, 0.030] | 0.0083 | 0.029 | 0.181 | 0.051 | 0.971 | 0.819 | 0.288 [0.198, 0.351] | 0.225 | 0.956 |
| Multi-source XGBoost | 0.786 | 0.053 [0.043, 0.064] | 0.0083 | 0.075 | 0.089 | 0.081 | 0.925 | 0.911 | 0.325 [0.286, 0.368] | 0.104 | 0.894 |

| Model | Held-out region | Onsets | PR-AUC | Base rate |
| --- | --- | --- | --- | --- |
| Climatology | Ashanti | 76 | 0.015 | 0.0061 |
| Climatology | Brong Ahafo | 20 | 0.003 | 0.0018 |
| Climatology | Central | 86 | 0.029 | 0.0104 |
| Climatology | Eastern | 56 | 0.008 | 0.0052 |
| Climatology | Greater Accra | 206 | 0.051 | 0.0322 |
| Climatology | Northern | 77 | 0.012 | 0.0072 |
| Climatology | Upper East | 54 | 0.016 | 0.0101 |
| Climatology | Upper West | 27 | 0.009 | 0.0059 |
| Climatology | Volta | 94 | 0.015 | 0.0091 |
| Climatology | Western | 54 | 0.019 | 0.0059 |
| Rainfall threshold (live rule) | Ashanti | 76 | 0.024 | 0.0061 |
| Rainfall threshold (live rule) | Brong Ahafo | 20 | 0.003 | 0.0018 |
| Rainfall threshold (live rule) | Central | 86 | 0.033 | 0.0104 |
| Rainfall threshold (live rule) | Eastern | 56 | 0.011 | 0.0052 |
| Rainfall threshold (live rule) | Greater Accra | 206 | 0.107 | 0.0322 |
| Rainfall threshold (live rule) | Northern | 77 | 0.032 | 0.0072 |
| Rainfall threshold (live rule) | Upper East | 54 | 0.075 | 0.0101 |
| Rainfall threshold (live rule) | Upper West | 27 | 0.039 | 0.0059 |
| Rainfall threshold (live rule) | Volta | 94 | 0.021 | 0.0091 |
| Rainfall threshold (live rule) | Western | 54 | 0.070 | 0.0059 |
| Logistic regression (rainfall) | Ashanti | 76 | 0.106 | 0.0061 |
| Logistic regression (rainfall) | Brong Ahafo | 20 | 0.004 | 0.0018 |
| Logistic regression (rainfall) | Central | 86 | 0.030 | 0.0104 |
| Logistic regression (rainfall) | Eastern | 56 | 0.029 | 0.0052 |
| Logistic regression (rainfall) | Greater Accra | 206 | 0.097 | 0.0322 |
| Logistic regression (rainfall) | Northern | 77 | 0.031 | 0.0072 |
| Logistic regression (rainfall) | Upper East | 54 | 0.081 | 0.0101 |
| Logistic regression (rainfall) | Upper West | 27 | 0.032 | 0.0059 |
| Logistic regression (rainfall) | Volta | 94 | 0.015 | 0.0091 |
| Logistic regression (rainfall) | Western | 54 | 0.146 | 0.0059 |
| XGBoost (rainfall) | Ashanti | 76 | 0.023 | 0.0061 |
| XGBoost (rainfall) | Brong Ahafo | 20 | 0.004 | 0.0018 |
| XGBoost (rainfall) | Central | 86 | 0.030 | 0.0104 |
| XGBoost (rainfall) | Eastern | 56 | 0.010 | 0.0052 |
| XGBoost (rainfall) | Greater Accra | 206 | 0.105 | 0.0322 |
| XGBoost (rainfall) | Northern | 77 | 0.028 | 0.0072 |
| XGBoost (rainfall) | Upper East | 54 | 0.077 | 0.0101 |
| XGBoost (rainfall) | Upper West | 27 | 0.033 | 0.0059 |
| XGBoost (rainfall) | Volta | 94 | 0.022 | 0.0091 |
| XGBoost (rainfall) | Western | 54 | 0.048 | 0.0059 |
| Multi-source XGBoost | Ashanti | 76 | 0.115 | 0.0061 |
| Multi-source XGBoost | Brong Ahafo | 20 | 0.004 | 0.0018 |
| Multi-source XGBoost | Central | 86 | 0.050 | 0.0104 |
| Multi-source XGBoost | Eastern | 56 | 0.020 | 0.0052 |
| Multi-source XGBoost | Greater Accra | 206 | 0.116 | 0.0322 |
| Multi-source XGBoost | Northern | 77 | 0.037 | 0.0072 |
| Multi-source XGBoost | Upper East | 54 | 0.061 | 0.0101 |
| Multi-source XGBoost | Upper West | 27 | 0.031 | 0.0059 |
| Multi-source XGBoost | Volta | 94 | 0.036 | 0.0091 |
| Multi-source XGBoost | Western | 54 | 0.081 | 0.0059 |

## E5. Fusion strategy (temporal)

| Strategy | ROC-AUC | PR-AUC (90% CI) | Brier | Precision | Recall | F1 | FAR | MER | SEDI (90% CI) | POD ±1 wk | FAR ±1 wk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Early fusion (multi-source XGBoost) | 0.834 | 0.072 [0.058, 0.091] | 0.0081 | 0.131 | 0.159 | 0.144 | 0.869 | 0.841 | 0.451 [0.405, 0.499] | 0.183 | 0.808 |
| Late fusion (mean) | 0.792 | 0.051 [0.037, 0.065] | 0.0082 | 0.067 | 0.192 | 0.099 | 0.933 | 0.808 | 0.410 [0.350, 0.468] | 0.243 | 0.891 |
| Stacking (logistic meta-model) | 0.542 | 0.019 [0.010, 0.035] | 0.0083 | 0.066 | 0.108 | 0.082 | 0.934 | 0.892 | 0.331 [0.293, 0.359] | 0.127 | 0.895 |
| Platform hand-set weights | 0.776 | 0.032 [0.025, 0.040] | 0.1877 | 0.037 | 0.177 | 0.061 | 0.963 | 0.823 | 0.320 [0.271, 0.374] | 0.228 | 0.942 |

## E6. Source degradation (multi-source XGBoost, temporal)

| Condition | PR-AUC | Δ PR-AUC |
| --- | --- | --- |
| All sources | 0.072 | 0.000 |
| Rainfall missing | 0.048 | -0.024 |
| Rainfall one week stale | 0.038 | -0.034 |
| Soil moisture missing | 0.073 | 0.001 |
| Soil moisture one week stale | 0.072 | 0.000 |
| River (runoff, discharge) missing | 0.074 | 0.002 |
| River (runoff, discharge) one week stale | 0.067 | -0.006 |
| Geographic + exposure missing | 0.022 | -0.050 |

## E7. Calibration (multi-source XGBoost, temporal)

| Method | Brier | ECE | PR-AUC |
| --- | --- | --- | --- |
| Raw | 0.00809 | 0.00298 | 0.072 |
| Platt scaling | 0.00806 | 0.00063 | 0.076 |
| Isotonic | 0.00813 | 0.00115 | 0.069 |

## E9. SHAP fidelity and stability (train ≤ 2021, test 2023-2025)

| Feature | Mean abs SHAP |
| --- | --- |
| built_frac | 0.4134 |
| rain_week_sum | 0.2836 |
| slope_mean | 0.2296 |
| runoff_week_sum | 0.2063 |
| rain_week_sum_p95 | 0.2036 |
| log_pop_density | 0.1764 |
| q_ratio | 0.1691 |
| rain_week_max | 0.1372 |
| rain_prev4w_sum | 0.1359 |
| woy_cos | 0.1108 |
| rain_lag1 | 0.0812 |
| rain_lag4 | 0.0761 |
| rain_lag2 | 0.0623 |
| rain_week_max_p95 | 0.0261 |
| q_week_max_log | 0.0228 |
| elev_mean | 0.0204 |
| perm_water_frac | 0.0182 |
| woy_sin | 0.0121 |
| sm_week_mean | 0.0088 |
| rain_lag3 | 0.0078 |
| sm_start | 0.0035 |
| runoff_prev4w_sum | 0.0025 |

| Features removed (k) | Mean abs change, top-SHAP | Mean abs change, random |
| --- | --- | --- |
| 1 | 0.0504 | 0.0085 |
| 3 | 0.0604 | 0.0289 |
| 5 | 0.0622 | 0.0384 |

Global-importance rank stability across bootstrap retrainings: mean Spearman ρ 0.814 (min 0.688, 10 pairs).

## Not runnable

- E8 impact layers: Needs NADMO incident records with people affected per district (requested; see nadmo_data_request.md). 0 usable records found.
- + Dam ablation step: no historical dam or reservoir record for Ghana.
- Human decision, warning-policy and incorrect-AI studies: need recruited participants and ethics approval.
