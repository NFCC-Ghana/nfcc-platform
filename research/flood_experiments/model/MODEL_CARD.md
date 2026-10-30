# Model card: NFCC weekly flood-onset model

## What it predicts

The probability that a flood *starts* in a Ghanaian district (GAUL 2015,
216 districts) in the coming Monday-to-Sunday week.

## Intended use

- Decision support for district disaster officers (NADMO) and the NFCC
  platform.
- Shadow mode first: compare its probabilities with what happens before
  anyone acts on them.
- Not for automatic public alerts. Not for sub-daily flash-flood timing.
- Lead time: one week (issued before the week starts).

## Inputs

Only inputs known when the week starts:

- **Rain:** past four weeks (IMERG live, CHIRPS in training), and the
  4-week total as a percentile of the district's own 2000-2014 climate.
- **Soil and runoff:** ERA5-Land soil moisture and runoff.
- **River:** GloFAS discharge at the district's main river (last week).
- **Place:** terrain, permanent water, built-up share, population
  density.

Features: woy_sin, woy_cos, rain_lag1, rain_lag2, rain_lag3, rain_lag4, rain_prev4w_sum, sm_start, runoff_prev4w_sum, rain_prev4w_pct, q_ratio_lag1, q_week_max_log_lag1, elev_mean, slope_mean, perm_water_frac, built_frac, log_pop_density.

The week's ECMWF rain forecast is *not* an input. In the real-forecast
test (E3c, 2024-2025), adding it lowered skill: PR-AUC 0.050 when fed
directly, 0.075 as a cross-fitted MOS blend, against 0.089 without it.
The shadow run reports the ensemble alongside the probability as context
for the forecaster.

## Training

- **Labels:** Groundsource news-reported floods plus documented events.
- **Data:** 2015-2024, with 2025
  held out for early stopping.
- **Model:** XGBoost, monotone in every rain, soil and river input; best
  iteration 259.
- **Calibration:** Platt scaling fitted on out-of-fold forecasts for
  2018-2025.

## Performance (out of fold, 2018-2025)

750 onsets, base rate 0.0084. ROC-AUC 0.810,
PR-AUC 0.051, Brier 0.00817, ECE 0.00097.
Within-district AUC (timing skill only) 0.726.

| Level | Rule | Alerts / year | POD | FAR | POD ±1 wk | FAR ±1 wk |
| --- | --- | --- | --- | --- | --- | --- |
| WATCH | P >= 5% | 217 | 0.19 | 0.92 | 0.21 | 0.84 |
| WARNING | P >= 20% | 9 | 0.02 | 0.84 | 0.02 | 0.68 |

Reliability (calibrated, equal-count bins):

| Mean predicted | Observed rate | Weeks |
| --- | --- | --- |
| 0.0003 | 0.0003 | 8912 |
| 0.0010 | 0.0007 | 8912 |
| 0.0020 | 0.0019 | 8911 |
| 0.0036 | 0.0037 | 8911 |
| 0.0045 | 0.0026 | 8911 |
| 0.0054 | 0.0049 | 8911 |
| 0.0071 | 0.0049 | 8911 |
| 0.0089 | 0.0097 | 8911 |
| 0.0131 | 0.0162 | 8911 |
| 0.0385 | 0.0393 | 8911 |

## Limitations: do not trust it here

- **Urban flood labels are unverified.** Radar cannot see them, so the
  model's urban skill partly reflects where news reports floods
  (results/v2: label audit). NADMO records are needed to verify it.
- **Weekly resolution.** It cannot time a flash flood within the week.
- **Dam releases are not inputs.** This covers Akosombo, Kpong and
  Bagre in Burkina Faso, so dam-driven floods on the Volta are under-
  predicted.
- **Boundaries.** GAUL 2015 districts; 261 districts exist since 2018.
- **Coverage is uneven.** Districts with little news coverage have few
  training events.
