# NFCC flood-prediction experiments: results

216 districts in 10 regions, 979 weeks (2000–2018). 203 flood onsets in 68 districts, out of 209,175 scored district-weeks (base rate 0.0010).

Onsets by region: Ashanti 3, Brong Ahafo 19, Central 2, Eastern 18, Greater Accra 18, Northern 71, Upper East 17, Upper West 1, Volta 51, Western 3

## E1 + E3. Model hierarchy, temporal forward-chaining (test 2008–2018)

| Model | ROC-AUC | PR-AUC (90% CI) | Brier | Precision | Recall | F1 | FAR | MER | SEDI (90% CI) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Climatology | 0.621 | 0.005 [0.000, 0.020] | 0.0009 | 0.001 | 0.094 | 0.001 | 0.999 | 0.906 | -0.091 [-0.706, 0.313] |
| Persistence | 0.511 | 0.001 [0.000, 0.002] | 0.0068 | 0.000 | 0.123 | 0.001 | 1.000 | 0.877 | -0.393 [-0.732, 0.131] |
| Rainfall threshold (live rule) | 0.765 | 0.003 [0.001, 0.007] | 0.1410 | 0.003 | 0.425 | 0.005 | 0.997 | 0.575 | 0.440 [-0.006, 0.921] |
| Logistic regression (rainfall) | 0.631 | 0.003 [0.000, 0.009] | 0.0009 | 0.001 | 0.085 | 0.002 | 0.999 | 0.915 | 0.018 [-0.681, 0.428] |
| Random forest (rainfall) | 0.613 | 0.002 [0.000, 0.005] | 0.0009 | 0.001 | 0.094 | 0.001 | 0.999 | 0.906 | -0.035 [-0.608, 0.338] |
| XGBoost (rainfall) | 0.631 | 0.002 [0.000, 0.006] | 0.0009 | 0.001 | 0.113 | 0.002 | 0.999 | 0.887 | 0.067 [-0.602, 0.452] |
| Temporal XGBoost (rain lags + soil state) | 0.675 | 0.003 [0.000, 0.013] | 0.0009 | 0.001 | 0.094 | 0.002 | 0.999 | 0.906 | -0.026 [-0.722, 0.447] |
| Multi-source XGBoost | 0.731 | 0.003 [0.001, 0.012] | 0.0009 | 0.002 | 0.094 | 0.004 | 0.998 | 0.906 | 0.158 [-0.578, 0.585] |

## E2. Source ablation (XGBoost, temporal)

| Configuration | ROC-AUC | PR-AUC (90% CI) | Brier | Precision | Recall | F1 | FAR | MER | SEDI (90% CI) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline (rainfall + season) | 0.630 | 0.003 [0.000, 0.017] | 0.0009 | 0.001 | 0.170 | 0.002 | 0.999 | 0.830 | 0.103 [-0.662, 0.445] |
| + Soil moisture | 0.675 | 0.003 [0.000, 0.013] | 0.0009 | 0.001 | 0.094 | 0.002 | 0.999 | 0.906 | -0.026 [-0.722, 0.447] |
| + River (runoff, discharge) | 0.620 | 0.003 [0.000, 0.014] | 0.0009 | 0.001 | 0.094 | 0.003 | 0.999 | 0.906 | 0.082 [-0.622, 0.495] |
| + Dam | not run: No historical dam release or reservoir record exists for Ghana (VRA data never obtained); DAHITI levels start after most labelled events. | | | | | | | | |
| + Geographic | 0.670 | 0.004 [0.001, 0.017] | 0.0009 | 0.001 | 0.094 | 0.003 | 0.999 | 0.906 | 0.084 [-0.665, 0.538] |
| + Exposure | 0.731 | 0.003 [0.001, 0.012] | 0.0009 | 0.002 | 0.094 | 0.004 | 0.998 | 0.906 | 0.158 [-0.578, 0.585] |

## E4. Spatial holdout (leave-one-region-out)

| Model | ROC-AUC | PR-AUC (90% CI) | Brier | Precision | Recall | F1 | FAR | MER | SEDI (90% CI) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Climatology | 0.640 | 0.002 [0.000, 0.006] | 0.0009 | 0.000 | 0.000 | 0.000 | – | 1.000 | -0.000 [-0.000, 0.000] |
| Rainfall threshold (live rule) | 0.765 | 0.003 [0.001, 0.007] | 0.1410 | 0.005 | 0.066 | 0.009 | 0.995 | 0.934 | 0.241 [-0.019, 0.505] |
| Logistic regression (rainfall) | 0.763 | 0.002 [0.001, 0.004] | 0.0009 | 0.002 | 0.085 | 0.003 | 0.998 | 0.915 | 0.127 [0.027, 0.276] |
| XGBoost (rainfall) | 0.613 | 0.001 [0.000, 0.002] | 0.0009 | 0.001 | 0.123 | 0.003 | 0.999 | 0.877 | 0.094 [-0.690, 0.365] |
| Multi-source XGBoost | 0.594 | 0.001 [0.001, 0.003] | 0.0009 | 0.001 | 0.132 | 0.002 | 0.999 | 0.868 | 0.019 [-0.738, 0.167] |

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
| XGBoost (rainfall) | Brong Ahafo | 13 | 0.001 | 0.0008 |
| XGBoost (rainfall) | Central | 1 | 0.000 | 0.0001 |
| XGBoost (rainfall) | Eastern | 12 | 0.002 | 0.0008 |
| XGBoost (rainfall) | Greater Accra | 12 | 0.003 | 0.0013 |
| XGBoost (rainfall) | Northern | 31 | 0.006 | 0.0021 |
| XGBoost (rainfall) | Upper East | 5 | 0.002 | 0.0007 |
| XGBoost (rainfall) | Volta | 28 | 0.004 | 0.0020 |
| XGBoost (rainfall) | Western | 3 | 0.001 | 0.0002 |
| Multi-source XGBoost | Ashanti | 1 | 0.000 | 0.0001 |
| Multi-source XGBoost | Brong Ahafo | 13 | 0.002 | 0.0008 |
| Multi-source XGBoost | Central | 1 | 0.001 | 0.0001 |
| Multi-source XGBoost | Eastern | 12 | 0.001 | 0.0008 |
| Multi-source XGBoost | Greater Accra | 12 | 0.005 | 0.0013 |
| Multi-source XGBoost | Northern | 31 | 0.007 | 0.0021 |
| Multi-source XGBoost | Upper East | 5 | 0.004 | 0.0007 |
| Multi-source XGBoost | Volta | 28 | 0.002 | 0.0020 |
| Multi-source XGBoost | Western | 3 | 0.001 | 0.0002 |

## E5. Fusion strategy (temporal)

| Strategy | ROC-AUC | PR-AUC (90% CI) | Brier | Precision | Recall | F1 | FAR | MER | SEDI (90% CI) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Early fusion (multi-source XGBoost) | 0.731 | 0.003 [0.001, 0.012] | 0.0009 | 0.002 | 0.094 | 0.004 | 0.998 | 0.906 | 0.158 [-0.578, 0.585] |
| Late fusion (mean) | 0.688 | 0.004 [0.000, 0.018] | 0.0009 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | -0.712 [-0.777, -0.595] |
| Stacking (logistic meta-model) | 0.544 | 0.001 [0.000, 0.002] | 0.0009 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | -0.754 [-0.816, -0.640] |
| Platform hand-set weights | 0.831 | 0.004 [0.001, 0.010] | 0.2080 | 0.002 | 0.443 | 0.004 | 0.998 | 0.557 | 0.379 [-0.058, 0.849] |

## E6. Source degradation (multi-source XGBoost, temporal)

| Condition | PR-AUC | Δ PR-AUC |
| --- | --- | --- |
| All sources | 0.003 | 0.000 |
| Rainfall missing | 0.001 | -0.002 |
| Rainfall one week stale | 0.002 | -0.001 |
| Soil moisture missing | 0.003 | -0.000 |
| Soil moisture one week stale | 0.003 | 0.000 |
| River (runoff, discharge) missing | 0.002 | -0.001 |
| River (runoff, discharge) one week stale | 0.004 | 0.001 |
| Geographic + exposure missing | 0.002 | -0.002 |

## E7. Calibration (multi-source XGBoost, temporal)

| Method | Brier | ECE | PR-AUC |
| --- | --- | --- | --- |
| Raw | 0.00093 | 0.00075 | 0.003 |
| Platt scaling | 0.00098 | 0.00134 | 0.002 |
| Isotonic | 0.00093 | 0.00154 | 0.002 |

## E9. SHAP fidelity and stability (train ≤ 2012, test 2014-2018)

| Feature | Mean abs SHAP |
| --- | --- |
| woy_sin | 1.0603 |
| perm_water_frac | 0.8863 |
| runoff_week_sum | 0.7126 |
| rain_lag1 | 0.6303 |
| q_ratio | 0.6106 |
| sm_start | 0.5639 |
| woy_cos | 0.5212 |
| rain_week_max | 0.4900 |
| slope_mean | 0.4812 |
| rain_prev4w_sum | 0.4335 |
| q_week_max_log | 0.2982 |
| rain_lag4 | 0.2966 |
| runoff_prev4w_sum | 0.2686 |
| rain_week_sum | 0.2416 |
| rain_lag3 | 0.2396 |
| built_frac | 0.2258 |
| sm_week_mean | 0.2258 |
| rain_lag2 | 0.2012 |
| log_pop_density | 0.1308 |
| elev_mean | 0.1264 |

| Features removed (k) | Mean abs change, top-SHAP | Mean abs change, random |
| --- | --- | --- |
| 1 | 0.0062 | 0.0036 |
| 3 | 0.0062 | 0.0058 |
| 5 | 0.0063 | 0.0057 |

Global-importance rank stability across bootstrap retrainings: mean Spearman ρ 0.835 (min 0.693, 10 pairs).

## Not runnable

- E8 impact layers: Needs people-affected counts per district per event; open sources (DFO, EM-DAT, ReliefWeb) report them per event or per country only.
- + Dam ablation step: no historical dam or reservoir record for Ghana.
- Human decision, warning-policy and incorrect-AI studies: need recruited participants and ethics approval.
