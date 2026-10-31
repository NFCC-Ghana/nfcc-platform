# NFCC flood early-warning system: technical reference for the manuscript

*State of the system on 31 October 2026. Prepared for the NFCC manuscript team. Every number in the results sections is generated directly from the project's result files (`research/flood_experiments/results/`), not transcribed.*

## How to read this document

NFCC has two parts, and the manuscript should keep them distinct:

1. **The operational platform:** the live, rule-based flood-risk and alerting system. It runs on Google Cloud Run for 9 tracked districts and is used through a Streamlit dashboard. It is described in section 2.
2. **The research and forecasting framework:** a reproducible machine-learning study on all 216 districts of Ghana (FAO GAUL 2015 boundaries), with an operational model that runs weekly in *shadow mode* (scored and logged, never used for alerts). It is described in sections 3–5.

**Terms used throughout:**

- **District-week:** one district in one Monday-to-Sunday week, the unit of analysis.
- **Flood onset:** a district-week that is flooded when the previous week was not; the prediction target.
- **Base rate:** the share of district-weeks that are onsets.
- **PR-AUC:** area under the precision-recall curve (average precision). A model with no skill scores the base rate, so "PR-AUC ÷ base rate" reads as "times better than chance".
- **POD / FAR:** probability of detection / false-alarm ratio.
- **SEDI:** Symmetric Extremal Dependence Index (Ferro & Stephenson 2011): 0 is no skill, 1 is perfect, and it stays meaningful for rare events.
- **Within-district AUC:** ROC-AUC computed inside each district, then averaged; it measures *when* a district floods, not *which* districts flood.

## Summary: the team's five questions

| # | Question | Answer |
| --- | --- | --- |
| 1 | Did we use only XGBoost, or other models? | **No.** The study compares 11 models: two baselines (climatology, persistence), the NFCC rainfall rule, a river-discharge benchmark, logistic regression, random forest and five XGBoost variants. It also compares 4 ways of fusing data sources. The best is M11 (XGBoost on multi-source data plus local-climate rainfall features). The model deployed in shadow mode is a calibrated XGBoost using only inputs known when the week starts. The live alert system is rule-based. Full catalogue: section 4.1. |
| 2 | Is the dashboard connected to all data sources? | **Partly.** It is connected to 10 real sources: GPM IMERG V07, CHIRPS v2.0, Open-Meteo forecast, GloFAS v4, NASA SMAP L4, Sentinel-1 GRD, DAHITI altimetry, ReliefWeb, GDELT and citizen reports. It is **not** connected to river gauges (HSD), VRA dam telemetry, Google Flood Hub, TAHMO or GMet. "Phase 2" items in the project plan (nowcasting, inundation model, insurance trigger API, SMS at scale) are not built. Section 2.2. |
| 3 | Do the experiments cover Accra alone or many districts? | **All 216 districts in all 10 (2015) regions**, for 2015–2025 (main study) and 2000–2018 (sensitivity study). The live platform tracks 9 districts. Sections 3.1 and 5.1. |
| 4 | Were TAHMO, GMet and river-gauge data available? | **No.** None was obtained. Open satellite and reanalysis products were used instead (CHIRPS, IMERG, ERA5-Land, GloFAS). Section 6. |
| 5 | What models, datasets and results are accessible? | Everything in this document is in the public repository **NFCC-Ghana/nfcc-platform** and can be regenerated from open data. Section 7 lists each item and where it is. |

## 2. The operational platform

### 2.1 Coverage: tracked districts

| District | Region | Centroid (lat, lon) | Population | Area (km²) |
| --- | --- | --- | --- | --- |
| Accra Central | Greater Accra | 5.560, −0.210 | 187,928 | 45.5 |
| Accra West | Greater Accra | 5.550, −0.230 | 203,461 | 52.3 |
| Accra East | Greater Accra | 5.565, −0.190 | 142,587 | 38.2 |
| Tema | Greater Accra | 5.650, −0.020 | 177,924 | 565 |
| Kumasi | Ashanti | 6.670, −1.620 | 443,981 | 299 |
| Tamale | Northern | 9.400, −0.840 | 374,744 | 731 |
| Cape Coast | Central | 5.100, −1.250 | 189,925 | 122 |
| Ho | Volta | 6.601, 0.471 | 180,420 | 573.2 |
| Sunyani | Bono | 7.333, −2.333 | 193,595 | 1,289 |

Source: `src/exposure/districts.py`. The three Accra districts are adjacent: their centroids lie within 4 km of each other.

### 2.2 Data sources connected to the platform

The dashboard reads all data through the platform API; a source counts as connected only if the API uses it.

| # | Source (exact product) | Provider / access | Resolution and latency | Used for | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | GPM IMERG V07 half-hourly precipitation (`NASA/GPM_L3/IMERG_V07`) | NASA, via Google Earth Engine | 0.1°; about 2–4 days behind real time | Rain in the last 3 days (antecedent rainfall), rescaled to CHIRPS per location with the CHIRPS/IMERG ratio of a past year | Connected |
| 2 | CHIRPS v2.0 daily (`UCSB-CHG/CHIRPS/DAILY`) | Climate Hazards Center, via Earth Engine | 0.05°; final product lags by weeks | Historical backtest and rare-event verification (1981–present); CHIRPS v3 near-real-time as fallback for source 1 | Connected |
| 3 | Open-Meteo Forecast API (`api.open-meteo.com/v1/forecast`, default "best match" model selection) | Open-Meteo | Hourly; 3-day horizon | 24/48/72-hour rainfall forecast, rain probability, current weather | Connected. Reports "unavailable" with no values when unreachable |
| 4 | GloFAS v4 river discharge (`flood-api.open-meteo.com/v1/flood`) | Copernicus Emergency Management Service, via Open-Meteo | 0.05°; daily | River pathway: discharge relative to the day's long-term mean (≥1.5× = elevated; illustrative, not a calibrated flood stage) | Connected |
| 5 | NASA SMAP L4 surface and root-zone soil moisture (`NASA/SMAP/SPL4SMGP/008`) | NASA, via Earth Engine | 9 km, 3-hourly; 2–3 days latency | Soil saturation | Connected |
| 6 | Sentinel-1 GRD C-band SAR (`COPERNICUS/S1_GRD`), IW mode, VV and VH | ESA Copernicus, via Earth Engine | 10 m; revisit 6–12 days over Ghana | Flood detection by change detection (section 2.4) | Connected. Reports "unavailable" (no detection, no area) when Earth Engine is unreachable or there is no image in the last 12 days |
| 7 | DAHITI satellite altimetry (`dahiti.dgfi.tum.de`, API v2) | DGFI-TUM | Water-level time series per target | Lake Volta level, Akosombo (target 97); White Volta river level for Tamale only (target 9087, about 45.5 km away) | Connected (two targets only) |
| 8 | ReliefWeb API v2 (`api.reliefweb.int/v2/reports`) | UN OCHA | Reports, country-tagged | Post-event outcome evidence | Connected (country-level only) |
| 9 | GDELT DOC 2.0 API (`api.gdeltproject.org/api/v2/doc/doc`) | GDELT Project | News articles | Post-event outcome evidence | Connected (country-level only) |
| 10 | Citizen flood reports | NFCC community reporting (database `community_reports`) | Event-level | Direct-observation pathway, after verification | Connected |
| – | Urban drainage table | NFCC (static) | Accra Central, West and East only | Risk multiplier (section 2.3) | Static values with no cited source |
| – | Google Flood Hub (Flood Forecasting API) | Google | – | River forecasts | Client implemented; no API access (pilot waitlist) |
| – | Ghana Hydrological Authority (HSD) river gauges | – | – | River levels | Not connected |
| – | VRA dam telemetry (Akosombo, Kpong) | – | – | Dam releases | Not connected |
| – | TAHMO stations; Ghana Meteorological Agency (GMet) | – | – | Station rainfall | Not connected |

**Planned but not built ("Phase 2" in the project plan):**

- rainfall nowcasting (0–6 h);
- an urban inundation surrogate model;
- hydrological routing (HBV/GR4J + LSTM);
- an insurance (parametric) trigger API;
- dashboard v2 (nowcasting layer, 3D terrain, mobile);
- SMS/voice alerts at scale through Africa's Talking.

### 2.3 Risk scoring (rule-based)

The live risk score `S` (0–100) is a piecewise-linear function of rainfall `P` in mm (`calculate_score`, `src/alerts/formatter.py`):

| Rainfall P (mm) | Score S |
| --- | --- |
| P ≤ 0 | 0 |
| 0 < P < 10 | 3P |
| 10 ≤ P < 30 | 30 + 2(P − 10) |
| 30 ≤ P < 50 | 70 + 1.5(P − 30) |
| P ≥ 50 | min(100, 95 + 0.2(P − 50)) |

**Urban drainage multiplier** (Accra Central, West and East only). The score is multiplied by a drainage factor:

- **Base factor by drainage condition:** CRITICAL 1.5, POOR 1.2, FAIR 1.0, GOOD 0.8.
- **Rainfall factor:** 1.3 for P > 80 mm, 1.1 for P > 50 mm, otherwise 1.0.
- **Other districts:** 1.0 (no data).

**Risk tiers:**

| Tier | Score range |
| --- | --- |
| LOW | S < 30 |
| MODERATE | 30 ≤ S < 50 |
| HIGH | 50 ≤ S < 70 |
| CRITICAL | 70 ≤ S < 85 |
| EXTREME | S ≥ 85 |

(`src/config/settings.py`)

### 2.4 Multi-source evidence fusion

The decision card fuses evidence in two stages (`src/models/multi_source_confidence.py`):

1. **Within a causal pathway:** a weighted mean of the readings, with a confidence derived from coverage (the share of expected sources present) and agreement (spread capped at 45 points). Coverage below 60% marks the result "degraded".
2. **Across pathways:** a noisy-OR gate (Pearl 1988), P(flood) = 1 − Π(1 − pᵢ), so one active pathway is not averaged down by another that is inactive.

**Pathways and source weights:**

| Pathway | Source | Weight |
| --- | --- | --- |
| Pluvial | Rainfall (Open-Meteo forecast / observed) | 1.0 |
| Fluvial | River gauge level | 2.0 |
| Fluvial | Dam level, direct | 2.0 |
| Fluvial | Dam level, upstream proxy (e.g. Bagre for the north) | 1.2 |
| Direct observation | Sentinel-1 SAR, water detected | 2.2 |
| Direct observation | Sentinel-1 SAR, no water detected | 0.3 |
| Direct observation | Verified citizen reports (≥3) | 1.8 |
| Direct observation | Verified citizen reports (1–2) | 0.9 |

These weights are expert-set priors, not learned or skill-weighted. Only a real Sentinel-1 detection (source "Sentinel-1 SAR") counts as satellite evidence.

**Sentinel-1 flood detection.** Change detection is applied over a 0.05° box around the district centroid:

- **Before image:** the median of images taken 60 to 30 days before the date.
- **After image:** the median of images in the last 12 days.
- **Water:** a pixel is water where the drop in backscatter (before minus after) exceeds 3.0 dB in VH and 1.5 dB in VV.
- **Area:** summed at 10 m resolution; "water detected" means more than 0.1 km².
- **Confidence:** 0.55–0.90, increasing with the distance of the mean backscatter change from the thresholds.

**Dam spillage index** (`src/models/dam_spillage.py`): a fixed weighted formula,

> index = 0.5 × rainfall score + 0.3 × reservoir score + 0.2 × inflow score

where rainfall is normalised over 0–200 mm, reservoir level over 0–100% and inflow over 0–500 m³/s. It is a formula, not a fitted model.

### 2.5 Alerting, explanation and infrastructure

- **Human-in-the-loop alerting:** risk assessments create *pending* alerts, which an operator approves, dismisses or retracts on the dashboard.
- **Alert channels:** WhatsApp and SMS (Twilio), Telegram (Bot API) and email (SMTP).
- **Alert format:** each alert is also served as an OASIS Common Alerting Protocol (CAP 1.2) document.
- **Exercise mode:** produces practice alerts that are never sent.
- **AI copilot:** answers questions about districts by calling the platform's own tools. Model: Google Gemini (`gemini-flash-lite-latest`).
- **Hosting:** FastAPI service on Google Cloud Run (europe-west1, one instance), with SQLite databases continuously replicated to Google Cloud Storage by Litestream. API rate limits are shared through Upstash Redis.
- **Dashboard:** Streamlit, on Streamlit Community Cloud.

**Scheduled jobs (GitHub Actions):**

| Job | Schedule |
| --- | --- |
| Risk assessment for all tracked districts | Every 3 hours |
| Prediction outcome verification | Daily, 06:00 UTC |
| CHIRPS ingestion | Daily, 08:00 UTC |
| Weekly shadow flood forecast (section 5.10) | Mondays, 05:17 UTC |

## 3. Research framework: study design and data

### 3.1 Study design

| Item | Main study (v2) | Sensitivity study (v1) |
| --- | --- | --- |
| Spatial unit | 216 districts, FAO GAUL 2015 level 2, all 10 regions | 216 districts, same boundaries |
| Time unit | Monday–Sunday week | same |
| Period | 5 Jan 2015 – 28 Dec 2025 (573 weeks; 123,768 district-weeks) | 6 Mar 2000 – 9 Dec 2018 (979 weeks; 211,464 district-weeks) |
| Flood labels | Groundsource news-derived flood events, plus 8 documented events | Global Flood Database (MODIS), plus 8 documented events |
| Target | Flood onset (flooded this week, not flooded last week) | same |
| Scored district-weeks | 121,755 | 209,175 |
| Onsets | 898 in 167 districts (base rate 0.0074) | 203 in 68 districts (base rate 0.0010) |
| Test years | 2018–2025 | 2008–2018 |

Weeks that follow a flooded week (flood continuing or receding) are excluded from training and scoring, so every model is judged on predicting a **new** flood. The first four weeks of each district are excluded because their rainfall lags are incomplete.

### 3.2 Flood labels

- **Groundsource** (main study; Mayo et al. 2026; Earth Engine `projects/sat-io/open-datasets/groundsource_2026`): flood events extracted from news articles by a language model, each with a location polygon and start and end dates.
  - Ghana has 2,686 events.
  - Events with an area of 1,000 km² or less are assigned to the district containing their centroid (2,527 events).
  - 159 region- or country-level events are excluded.
  - A district-week is flooded if a placed event's dates overlap it.
- **Global Flood Database v1** (sensitivity study; Tellman et al. 2021; `GLOBAL_FLOOD_DB/MODIS_EVENTS/V1`): MODIS-mapped flood extents. A district-week is flooded if an event overlapping that week mapped at least 1 km² of water in the district, excluding permanent water.
- **Documented events:** 8 Ghana floods (2007–2023) in `src/hydrology/flood_polygons.py`, added to both label sets.
- **Sentinel-1 label audit** (section 5.8): an independent satellite check of the news labels. It is not used as a label.

### 3.3 Predictor data

| Group | Product | Earth Engine asset / endpoint | Resolution | Aggregation to district-week | Reference |
| --- | --- | --- | --- | --- | --- |
| Rainfall | CHIRPS v2.0 daily | `UCSB-CHG/CHIRPS/DAILY` | 0.05° | Weekly total and wettest day: district mean and 95th-percentile pixel (2 km grid) | Funk et al. 2015 |
| Soil moisture, runoff | ERA5-Land daily aggregates | `ECMWF/ERA5_LAND/DAILY_AGGR` | 0.1° | Mean top-layer volumetric soil water; weekly surface-runoff total (mm) | Muñoz-Sabater et al. 2021 |
| River discharge | GloFAS v4 reanalysis | Open-Meteo Flood API | 0.05° | Weekly maximum at each district's main river (the MERIT Hydro cell with the largest upstream area) | Harrigan et al. 2020; Alfieri et al. 2013 |
| River network | MERIT Hydro v1.0.1 | `MERIT/Hydro/v1_0_1` (upstream area `upa`) | 90 m | Locates each district's main river | Yamazaki et al. 2019 |
| Elevation, slope | SRTM 30 m | `USGS/SRTMGL1_003` | 30 m | District mean | Farr et al. 2007 |
| Permanent water | JRC Global Surface Water v1.4 | `JRC/GSW1_4/GlobalSurfaceWater` | 30 m | Share of district with water occurrence ≥ 75% | Pekel et al. 2016 |
| Built-up | GHSL GHS-BUILT-S R2023A, epoch 2010 | `JRC/GHSL/P2023A/GHS_BUILT_S` | 100 m | Built-up share of district | Pesaresi & Politis 2023 |
| Population | WorldPop 100 m, 2010 | `WorldPop/GP/100m/pop` | 100 m | Total, as log population density | Tatem 2017 |
| Boundaries | FAO GAUL 2015 level 2 | `FAO/GAUL/2015/level2` | – | 216 districts, 10 regions | FAO 2015 |
| Rain forecast (test E3c only) | ECMWF IFS 0.25° | Open-Meteo Previous Runs API | 0.25° | Forecast issued before each week, 2024–2025 | Zippenfenig 2023 |
| Live inputs (shadow run) | GPM IMERG V07; ECMWF IFS ensemble (51 members) | `NASA/GPM_L3/IMERG_V07`; Open-Meteo Ensemble API | 0.1°; 0.25° | Past 4 weeks of rain; next week's rain (context only) | Huffman et al. 2023 |

### 3.4 Model input features

| Feature | Definition |
| --- | --- |
| `woy_sin`, `woy_cos` | Week of year, sine and cosine (seasonality) |
| `rain_week_sum` | District-mean rainfall total for the week (mm) |
| `rain_week_max` | District-mean rainfall on the wettest day of the week (mm) |
| `rain_week_sum_p95`, `rain_week_max_p95` | Same, at the district's 95th-percentile pixel (the wettest area) |
| `rain_prev4w_sum` | Rainfall total of the previous 4 weeks |
| `rain_lag1` … `rain_lag4` | Weekly rainfall 1–4 weeks earlier |
| `rain_week_sum_pct`, `rain_week_max_pct`, `rain_prev4w_pct` | Percentile of the above within the district's own 2000–2014 CHIRPS record (local climate) |
| `sm_week_mean`, `sm_start` | Soil moisture this week and the previous week |
| `runoff_week_sum`, `runoff_prev4w_sum` | Surface runoff this week and over the previous 4 weeks |
| `q_week_max_log` | log(1 + weekly maximum discharge) |
| `q_ratio` | Weekly maximum discharge ÷ the district's 2015–2016 median (2000–2007 in v1) |
| `q_ratio_lag1`, `q_week_max_log_lag1` | Same, for the previous week |
| `elev_mean`, `slope_mean`, `perm_water_frac`, `built_frac` | Mean elevation, mean slope, permanent-water share, built-up share |
| `log_pop_density` | log(1 + population per km²) |
| `flood_recent8` | 1 if the district was flooded in any of weeks t−8 to t−2 (used only by M2) |

**Feature groups:**

| Group | Features |
| --- | --- |
| SEASON | `woy_sin`, `woy_cos` |
| RAIN | `rain_week_sum`, `rain_week_max`, `rain_prev4w_sum`, `rain_week_max_p95`, `rain_week_sum_p95` (v1 has no p95 features) |
| RAIN_LAGS | `rain_lag1`–`rain_lag4` |
| SOIL | `sm_start`, `sm_week_mean` |
| RIVER | `runoff_week_sum`, `runoff_prev4w_sum`, `q_week_max_log`, `q_ratio` |
| GEOGRAPHIC | `elev_mean`, `slope_mean`, `perm_water_frac`, `built_frac` |
| EXPOSURE | `log_pop_density` |
| LOCAL CLIMATE (v2) | `rain_week_sum_pct`, `rain_week_max_pct`, `rain_prev4w_pct` |

Except in the forecast-mode models (M12, and the E3b and E3c tests), inputs include the target week's observed rainfall. That is a *perfect-forecast hindcast*, an upper bound on forecast skill.

## 4. Models and evaluation

### 4.1 Model catalogue

All models output P(flood onset) for a district-week. They are implemented in `research/flood_experiments/models.py` (scikit-learn 1.x, XGBoost 2.x).

| ID | Name | Algorithm | Inputs | Settings |
| --- | --- | --- | --- | --- |
| M1 | Climatology | Empirical onset rate by district and calendar month, shrunk toward the national monthly rate | District, month | Beta prior, strength 50 weeks |
| M2 | Persistence | 1 if the district flooded in weeks t−8 to t−2, else 0 | `flood_recent8` | – |
| M3 | NFCC rainfall rule | The live platform's score S (section 2.3) on the week's wettest day, ÷ 100 | `rain_week_max` | Not fitted |
| M4 | River-discharge percentile (GloFAS-style benchmark) | Percentile of the week's maximum discharge within the district's training weeks | `q_week_max` | Not fitted |
| M5 | Logistic regression, rainfall | L2-regularised logistic regression (Cox 1958) | SEASON + RAIN | C = 1.0; standardised inputs; missing values imputed with the training median |
| M6 | Random forest, rainfall | Random forest classifier (Breiman 2001) | SEASON + RAIN | 300 trees, min_samples_leaf = 30, max_features = √p |
| M7 | XGBoost, rainfall | Gradient-boosted trees (Chen & Guestrin 2016) | SEASON + RAIN | XGBoost settings below |
| M8 | XGBoost, rainfall history + soil | as M7 | SEASON + RAIN + RAIN_LAGS + SOIL | XGBoost settings below |
| M9 | XGBoost, multi-source | as M7 | SEASON + RAIN + RAIN_LAGS + SOIL + RIVER + GEOGRAPHIC + EXPOSURE | XGBoost settings below |
| M10 | XGBoost, timing-only | as M7 | SEASON + RAIN + RAIN_LAGS + SOIL + RIVER + LOCAL CLIMATE (no place features) | XGBoost settings below |
| M11 | XGBoost, multi-source + local climate | as M7 | M9 inputs + LOCAL CLIMATE | XGBoost settings below |
| M12 | Operational model: XGBoost, forecast mode (deployed in shadow) | as M7, Platt-calibrated | Inputs known when the week starts: SEASON, RAIN_LAGS, `rain_prev4w_sum`, `rain_prev4w_pct`, `sm_start`, `runoff_prev4w_sum`, `q_ratio_lag1`, `q_week_max_log_lag1`, GEOGRAPHIC, EXPOSURE (17 inputs) | XGBoost settings below; section 5.10 |

**XGBoost settings (M7–M12):**

- **Trees:** up to 600, learning rate 0.03, maximum depth 3.
- **Regularisation:** min_child_weight 10, L2 penalty λ = 5.
- **Sampling:** row and column subsampling 0.8 each.
- **Early stopping:** after 50 rounds without improvement in validation PR-AUC.
- **Monotone constraints:** risk may only increase with every rainfall, soil-moisture, runoff and discharge input.

**Data-fusion strategies (experiment E5):**

| ID | Strategy | Description |
| --- | --- | --- |
| F1 | Early fusion | One model on all inputs (= M9) |
| F2 | Late fusion (mean) | One logistic regression per source group, probabilities averaged. Groups: rainfall (SEASON + RAIN + RAIN_LAGS), soil (SEASON + SOIL), river (SEASON + RIVER), static (GEOGRAPHIC + EXPOSURE) |
| F3 | Stacking | The F2 members combined by a logistic-regression meta-model fitted on the validation year |
| F4 | NFCC expert weights | The platform's hand-set fusion: (1.0 × rainfall score + 2.0 × river score) ÷ 3.0. The river score is (q_ratio − 1) ÷ 2, limited to 0–1 |

**Calibration methods (E7):** Platt scaling (Platt 1999) and isotonic regression (Zadrozny & Elkan 2002), fitted on the validation year.

**Explanation method (E9):** SHAP TreeExplainer (Lundberg & Lee 2017; Lundberg et al. 2020).

### 4.2 Validation design

- **Temporal forward-chaining (E1, E2, E3, E5–E7):** for each test year y, train on all years ≤ y−2, validate on y−1, test on y. Predictions are pooled over the test years.
- **Spatial hold-out (E4):** leave one region out, *and* separate it in time. Train on the other regions up to two years before the first test year, validate on them the following year, then test the held-out region over the test years. A purely spatial split would leak, because one flood event covers several regions in the same weeks.
- **Decision thresholds:** chosen to maximise F1 on the validation year, then applied unchanged to the test year. When the validation year has fewer than 5 onsets, the training years are used instead.
- **Uncertainty:** 90% intervals from a block bootstrap that resamples whole years (300 resamples), because weekly flood series are correlated within a season.

### 4.3 Evaluation metrics

| Metric | Definition | Reference |
| --- | --- | --- |
| ROC-AUC | Area under the receiver operating characteristic curve | Hanley & McNeil 1982 |
| PR-AUC | Average precision; equals the base rate for a no-skill model | Saito & Rehmsmeier 2015 |
| Brier score | Mean squared error of the probabilities | Brier 1950 |
| ECE | Expected calibration error, 10 equal-count bins | Naeini et al. 2015 |
| POD, FAR, MER, POFD | Hit rate; false-alarm ratio; missed-event rate (1 − POD); probability of false detection | Wilks 2011 |
| SEDI | Symmetric Extremal Dependence Index | Ferro & Stephenson 2011 |
| POD / FAR ±1 week | Event-based: an onset counts as detected if the district had an alert in weeks t−1 to t+1; an alert is false only if there was no onset within ±1 week | – |
| Within-district AUC | ROC-AUC within each district, averaged with weights by the district's onsets | – |
| Relative economic value | Value V(α) for a user with cost-loss ratio α, at the best threshold; 1 = perfect, 0 = no better than always or never acting | Richardson 2000; Murphy 1977 |

### 4.4 Experiments

| ID | Experiment | Design |
| --- | --- | --- |
| E1 | Model hierarchy | M1–M11, temporal forward-chaining |
| E2 | Source ablation | XGBoost with sources added cumulatively: rainfall + season → + soil → + river → + dam → + geography → + exposure |
| E3 | Temporal hold-out | The forward-chaining design itself; reported with E1 |
| E3b | One week ahead | Forecast-mode models (inputs known when the week starts) vs the perfect-forecast model |
| E3c | Real lead time | 2024–2025, using the ECMWF forecast issued before each week instead of observed rain |
| E4 | Spatial transfer | Leave one region out, separated in time |
| E5 | Data fusion | F1–F4 |
| E6 | Source degradation | At prediction time, one source group is missing (training median) or one week stale |
| E7 | Calibration | Raw vs Platt vs isotonic |
| E8 | Impact layer | Requires NADMO people-affected records. **Not run:** data not available |
| E9 | Explanation quality | SHAP fidelity (deleting the top-k SHAP features vs k random features) and stability (Spearman ρ across 5 bootstrap retrainings) |
| LA | Label audit | Sentinel-1 radar checked at every news-reported onset and at matched no-flood weeks |

## 5. Results

### 5.1 Datasets

**Main study (2015–2025):** 898 onsets in 167 of 216 districts.

| Year | Onsets |
| --- | --- |
| 2015 | 40 |
| 2016 | 41 |
| 2017 | 67 |
| 2018 | 91 |
| 2019 | 83 |
| 2020 | 78 |
| 2021 | 80 |
| 2022 | 117 |
| 2023 | 135 |
| 2024 | 68 |
| 2025 | 98 |


| Region | Onsets |
| --- | --- |
| Greater Accra | 251 |
| Ashanti | 107 |
| Central | 103 |
| Volta | 103 |
| Northern | 90 |
| Eastern | 67 |
| Western | 65 |
| Upper East | 63 |
| Upper West | 27 |
| Brong Ahafo | 22 |

**Sensitivity study (2000–2018):** 203 onsets in 68 districts.

| Year | Onsets |
| --- | --- |
| 2003 | 29 |
| 2004 | 2 |
| 2006 | 8 |
| 2007 | 58 |
| 2009 | 14 |
| 2010 | 51 |
| 2011 | 10 |
| 2015 | 1 |
| 2018 | 30 |

The Global Flood Database has no Ghana events in 2012–2014 or 2016–2017.

### 5.2 Model hierarchy (E1, E3): main study, test years 2018–2025

Base rate 0.0084; 750 test onsets.

| Model | ROC-AUC | PR-AUC [90% CI] | PR-AUC ÷ base rate | Brier | POD | FAR | SEDI [90% CI] | POD / FAR ±1 week |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M1 Climatology | 0.764 | 0.048 [0.038, 0.059] | 5.6× | 0.0082 | 0.13 | 0.90 | 0.40 [0.36, 0.44] | 0.15 / 0.82 |
| M2 Persistence | 0.609 | 0.018 [0.013, 0.024] | 2.2× | 0.0534 | 0.27 | 0.95 | 0.42 [0.34, 0.48] | 0.27 / 0.92 |
| M3 NFCC rainfall rule | 0.775 | 0.030 [0.022, 0.038] | 3.6× | 0.1487 | 0.11 | 0.96 | 0.28 [0.20, 0.33] | 0.15 / 0.94 |
| M4 River-discharge percentile | 0.740 | 0.025 [0.020, 0.031] | 2.9× | 0.3287 | 0.18 | 0.96 | 0.32 [0.22, 0.41] | 0.20 / 0.94 |
| M5 Logistic regression, rainfall | 0.765 | 0.043 [0.026, 0.061] | 5.1× | 0.0082 | 0.23 | 0.98 | 0.29 [0.21, 0.41] | 0.28 / 0.96 |
| M6 Random forest, rainfall | 0.747 | 0.028 [0.019, 0.039] | 3.4× | 0.0083 | 0.15 | 0.97 | 0.28 [0.15, 0.39] | 0.20 / 0.94 |
| M7 XGBoost, rainfall | 0.745 | 0.025 [0.019, 0.032] | 3.0× | 0.0083 | 0.21 | 0.96 | 0.34 [0.24, 0.43] | 0.28 / 0.94 |
| M8 XGBoost, rainfall history + soil | 0.724 | 0.022 [0.018, 0.028] | 2.6× | 0.0083 | 0.15 | 0.97 | 0.27 [0.17, 0.37] | 0.21 / 0.95 |
| M9 XGBoost, multi-source | 0.834 | 0.072 [0.058, 0.091] | 8.6× | 0.0081 | 0.16 | 0.87 | 0.45 [0.41, 0.50] | 0.18 / 0.81 |
| M10 XGBoost, timing-only | 0.758 | 0.034 [0.025, 0.045] | 4.0× | 0.0083 | 0.21 | 0.95 | 0.40 [0.28, 0.51] | 0.27 / 0.92 |
| M11 XGBoost, multi-source + local climate | 0.840 | 0.081 [0.063, 0.099] | 9.6× | 0.0081 | 0.20 | 0.87 | 0.49 [0.44, 0.53] | 0.23 / 0.81 |

### 5.3 When versus where, and value to users

Base rates in the test years: urban districts (top quarter by built-up share) 0.0206; rural districts 0.0045.

| Model | Within-district AUC | Urban PR-AUC | Rural PR-AUC | Peak economic value | Useful for cost-loss ratios |
| --- | --- | --- | --- | --- | --- |
| M1 Climatology | 0.715 | 0.079 | 0.011 | 0.36 | 0.003–0.14 |
| M2 Persistence | 0.554 | 0.032 | 0.009 | 0.22 | 0.001–0.04 |
| M3 NFCC rainfall rule | 0.798 | 0.066 | 0.019 | 0.41 | 0.002–0.11 |
| M4 River-discharge percentile | 0.765 | 0.049 | 0.019 | 0.39 | 0.003–0.03 |
| M5 Logistic regression, rainfall | 0.797 | 0.075 | 0.039 | 0.39 | 0.003–0.40 |
| M6 Random forest, rainfall | 0.768 | 0.063 | 0.019 | 0.36 | 0.003–0.11 |
| M7 XGBoost, rainfall | 0.774 | 0.059 | 0.017 | 0.37 | 0.004–0.07 |
| M8 XGBoost, rainfall history + soil | 0.755 | 0.054 | 0.015 | 0.36 | 0.004–0.06 |
| M9 XGBoost, multi-source | 0.779 | 0.106 | 0.019 | 0.55 | 0.002–0.40 |
| M10 XGBoost, timing-only | 0.764 | 0.068 | 0.025 | 0.44 | 0.004–0.09 |
| M11 XGBoost, multi-source + local climate | 0.782 | 0.116 | 0.027 | 0.56 | 0.002–0.50 |

### 5.4 Lead time (E3b, E3c)

**E3b, one week ahead (test years 2018–2025).** These models use only inputs known when the week starts; the first row is the perfect-forecast model for comparison.

| Model | ROC-AUC | PR-AUC [90% CI] | PR-AUC ÷ base rate | Brier | POD | FAR | SEDI [90% CI] | POD / FAR ±1 week |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M9 (perfect forecast: observed rain of the target week) | 0.834 | 0.072 [0.058, 0.091] | 8.6× | 0.0081 | 0.16 | 0.87 | 0.45 [0.41, 0.50] | 0.18 / 0.81 |
| Logistic regression, M12 inputs (forecast mode) | 0.817 | 0.046 [0.038, 0.057] | 5.4× | 0.0082 | 0.16 | 0.93 | 0.38 [0.33, 0.43] | 0.18 / 0.87 |
| XGBoost, M12 inputs (forecast mode; M12 before calibration) | 0.810 | 0.051 [0.040, 0.068] | 6.1× | 0.0082 | 0.17 | 0.93 | 0.40 [0.31, 0.48] | 0.21 / 0.86 |

**E3c, real archived forecasts (test years 2024, 2025).** The rows compare different rain inputs:

- **Perfect forecast:** the observed rain of the target week.
- **ECMWF forecast:** the ECMWF IFS forecast issued before each week (Open-Meteo Previous Runs), given to a model trained on observed rain.
- **MOS blend:** the antecedent-only model's probability, combined with the forecast's local-climate percentiles by a logistic regression fitted on the other forecast year.
- **No rain forecast:** antecedent inputs only.
- **NFCC rule on the forecast:** M3 applied to the forecast.

"Forecast-ready XGBoost" is M11 without the target week's soil-moisture, runoff and discharge inputs (which a forecaster does not have): its target-week rainfall inputs are fed either observed rain or the ECMWF forecast.

With two test years, the intervals are indicative.

| Model | ROC-AUC | PR-AUC [90% CI] | PR-AUC ÷ base rate | Brier | POD | FAR | SEDI [90% CI] | POD / FAR ±1 week |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Forecast-ready XGBoost, observed rain (upper bound) | 0.849 | 0.084 [0.072, 0.125] | 10.9× | 0.0074 | 0.19 | 0.87 | 0.48 [0.41, 0.58] | 0.23 / 0.81 |
| Forecast-ready XGBoost, ECMWF forecast | 0.837 | 0.050 [0.050, 0.072] | 6.4× | 0.0076 | 0.12 | 0.89 | 0.41 [0.40, 0.46] | 0.14 / 0.83 |
| XGBoost, M12 inputs (no rain forecast) | 0.870 | 0.089 [0.089, 0.101] | 11.4× | 0.0074 | 0.30 | 0.93 | 0.51 [0.47, 0.63] | 0.33 / 0.86 |
| M3 NFCC rainfall rule, ECMWF forecast | 0.693 | 0.013 [0.010, 0.020] | 1.7× | 0.1499 | 0.02 | 0.99 | 0.07 [-0.00, 0.12] | 0.02 / 0.99 |
| M1 Climatology | 0.803 | 0.060 [0.045, 0.075] | 7.7× | 0.0075 | 0.16 | 0.87 | 0.46 [0.44, 0.47] | 0.18 / 0.76 |
| MOS blend: M12-input XGBoost + ECMWF forecast | 0.864 | 0.075 [0.075, 0.105] | 9.7× | 0.0076 | 0.19 | 0.91 | 0.45 [0.40, 0.60] | 0.21 / 0.83 |

### 5.5 Source ablation (E2)

XGBoost, temporal forward-chaining, sources added cumulatively.

| Model | ROC-AUC | PR-AUC [90% CI] | PR-AUC ÷ base rate | Brier | POD | FAR | SEDI [90% CI] | POD / FAR ±1 week |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline (rainfall + season) | 0.717 | 0.023 [0.017, 0.029] | 2.8× | 0.0083 | 0.14 | 0.97 | 0.26 [0.17, 0.36] | 0.20 / 0.96 |
| + Soil moisture | 0.724 | 0.022 [0.018, 0.028] | 2.6× | 0.0083 | 0.15 | 0.97 | 0.27 [0.17, 0.37] | 0.21 / 0.95 |
| + River (runoff, discharge) | 0.746 | 0.033 [0.020, 0.049] | 4.0× | 0.0083 | 0.23 | 0.96 | 0.37 [0.27, 0.46] | 0.29 / 0.94 |
| + Dam | not run |  |  |  |  |  |  |  |
| + Geographic | 0.842 | 0.079 [0.063, 0.099] | 9.4× | 0.0081 | 0.17 | 0.87 | 0.47 [0.41, 0.51] | 0.20 / 0.81 |
| + Exposure | 0.834 | 0.072 [0.058, 0.091] | 8.6× | 0.0081 | 0.16 | 0.87 | 0.45 [0.41, 0.50] | 0.18 / 0.81 |

"+ Dam" was not run: no historical dam release or reservoir record exists for Ghana.

### 5.6 Spatial transfer (E4), data fusion (E5), degradation (E6)

**E4, held-out region** (pooled over the 10 held-out regions):

| Model | ROC-AUC | PR-AUC [90% CI] | PR-AUC ÷ base rate | Brier | POD | FAR | SEDI [90% CI] | POD / FAR ±1 week |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M1 Climatology | 0.643 | 0.012 [0.010, 0.015] | 1.5× | 0.0084 | 0.00 | – | -0.00 [-0.00, 0.00] | 0.00 / – |
| M3 NFCC rainfall rule | 0.775 | 0.030 [0.022, 0.038] | 3.6× | 0.1487 | 0.11 | 0.97 | 0.23 [0.16, 0.28] | 0.13 / 0.96 |
| M5 Logistic regression, rainfall | 0.711 | 0.038 [0.021, 0.055] | 4.5× | 0.0083 | 0.23 | 0.98 | 0.29 [0.21, 0.36] | 0.31 / 0.96 |
| M7 XGBoost, rainfall | 0.695 | 0.021 [0.016, 0.030] | 2.5× | 0.0083 | 0.18 | 0.97 | 0.29 [0.20, 0.35] | 0.23 / 0.96 |
| M9 XGBoost, multi-source | 0.786 | 0.053 [0.043, 0.064] | 6.3× | 0.0083 | 0.09 | 0.93 | 0.33 [0.29, 0.37] | 0.10 / 0.89 |

**E4, M9 by held-out region:**

| Held-out region | Test onsets | PR-AUC | Base rate |
| --- | --- | --- | --- |
| Ashanti | 76 | 0.115 | 0.0061 |
| Brong Ahafo | 20 | 0.004 | 0.0018 |
| Central | 86 | 0.050 | 0.0104 |
| Eastern | 56 | 0.020 | 0.0052 |
| Greater Accra | 206 | 0.116 | 0.0322 |
| Northern | 77 | 0.037 | 0.0072 |
| Upper East | 54 | 0.061 | 0.0101 |
| Upper West | 27 | 0.031 | 0.0059 |
| Volta | 94 | 0.036 | 0.0091 |
| Western | 54 | 0.081 | 0.0059 |

**E5, data fusion:**

| Model | ROC-AUC | PR-AUC [90% CI] | PR-AUC ÷ base rate | Brier | POD | FAR | SEDI [90% CI] | POD / FAR ±1 week |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F1 Early fusion (M9) | 0.834 | 0.072 [0.058, 0.091] | 8.6× | 0.0081 | 0.16 | 0.87 | 0.45 [0.41, 0.50] | 0.18 / 0.81 |
| F2 Late fusion (mean) | 0.792 | 0.051 [0.037, 0.065] | 6.0× | 0.0082 | 0.19 | 0.93 | 0.41 [0.35, 0.47] | 0.24 / 0.89 |
| F3 Stacking | 0.542 | 0.019 [0.010, 0.035] | 2.3× | 0.0083 | 0.11 | 0.93 | 0.33 [0.29, 0.36] | 0.13 / 0.90 |
| F4 NFCC expert weights | 0.776 | 0.032 [0.025, 0.040] | 3.8× | 0.1877 | 0.18 | 0.96 | 0.32 [0.27, 0.37] | 0.23 / 0.94 |

**E6, degradation of M9** (a source missing at prediction time = its training median; stale = last week's values):

| Condition | PR-AUC | Change |
| --- | --- | --- |
| All sources | 0.072 | 0.000 |
| Rainfall missing | 0.048 | -0.024 |
| Rainfall one week stale | 0.038 | -0.034 |
| Soil moisture missing | 0.073 | 0.001 |
| Soil moisture one week stale | 0.072 | 0.000 |
| River (runoff, discharge) missing | 0.074 | 0.002 |
| River (runoff, discharge) one week stale | 0.067 | -0.006 |
| Geographic + exposure missing | 0.022 | -0.050 |

### 5.7 Calibration (E7) and explanations (E9)

**E7** (M9; test years 2018–2025):

| Method | Brier | ECE | PR-AUC |
| --- | --- | --- | --- |
| Raw | 0.00809 | 0.00298 | 0.072 |
| Platt scaling | 0.00806 | 0.00063 | 0.076 |
| Isotonic | 0.00813 | 0.00115 | 0.069 |

**E9** (M9; trained ≤ 2021, tested 2023-2025).

Mean absolute SHAP value, top 10 features:

| Feature | Mean |SHAP| |
| --- | --- |
| `built_frac` | 0.4134 |
| `rain_week_sum` | 0.2836 |
| `slope_mean` | 0.2296 |
| `runoff_week_sum` | 0.2063 |
| `rain_week_sum_p95` | 0.2036 |
| `log_pop_density` | 0.1764 |
| `q_ratio` | 0.1691 |
| `rain_week_max` | 0.1372 |
| `rain_prev4w_sum` | 0.1359 |
| `woy_cos` | 0.1108 |

Fidelity: the change in predicted probability when the top-k SHAP features are replaced with training medians, against k random features:

| k | Top-SHAP features removed | Random features removed |
| --- | --- | --- |
| 1 | 0.0504 | 0.0085 |
| 3 | 0.0604 | 0.0289 |
| 5 | 0.0622 | 0.0384 |

Stability of global feature rankings across 5 bootstrap retrainings: mean Spearman ρ 0.81 (minimum 0.69, 10 pairs).

### 5.8 Label audit with Sentinel-1

**Design.** Every news-reported onset was checked, plus two matched no-flood controls:

- the same week in a randomly chosen other district;
- the same district and week of the year in another year.

**Method.** UN-SPIDER Recommended Practice change detection on Sentinel-1 GRD, VH polarisation, ascending passes, over ±1 week:

- **Reference:** the dry-season (January–February) median of the same year.
- **Water:** after/reference > 1.25 (in dB) and after < −20 dB.
- **Masks:** JRC permanent water (≥10 months a year), slope ≥ 5° (HydroSHEDS), and clusters smaller than 8 pixels, on a 100 m grid.
- **Confirmed:** at least 1 km² of new water in a district that was at least half imaged.

| Districts | Sample | Sampled | Imaged | Radar detection rate |
| --- | --- | --- | --- | --- |
| All | News-reported flood onset | 898 | 895 | 18.2% |
| All | Control: another district, same week | 898 | 887 | 14.8% |
| All | Control: same district, another year | 898 | 883 | 12.2% |
| Rural | News-reported flood onset | 342 | 342 | 32.5% |
| Rural | Control: another district, same week | 686 | 678 | 16.4% |
| Rural | Control: same district, another year | 342 | 333 | 17.4% |
| Urban | News-reported flood onset | 556 | 553 | 9.4% |
| Urban | Control: another district, same week | 212 | 209 | 9.6% |
| Urban | Control: same district, another year | 556 | 550 | 9.1% |

**Odds of radar detection at onsets versus controls:**

- vs another district in the same week: **1.28** (90% CI 1.04–1.59);
- vs the same district in another year: **1.60** (90% CI 1.28–1.99).

"Urban" means the top quarter of districts by built-up share (≥ 0.012). Radar cannot see most urban flooding, because buildings scatter the signal back, so urban labels are **unverified** rather than refuted.

### 5.9 Sensitivity study (2000–2018, satellite-mapped labels)

Test years 2008–2018.

| Model | ROC-AUC | PR-AUC [90% CI] | PR-AUC ÷ base rate | Brier | POD | FAR | SEDI [90% CI] | POD / FAR ±1 week |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M1 Climatology | 0.621 | 0.005 [0.000, 0.020] | 5.7× | 0.0009 | 0.22 | 1.00 | 0.14 [-0.20, 0.58] | 0.22 / 1.00 |
| M2 Persistence | 0.511 | 0.001 [0.000, 0.002] | 1.1× | 0.0068 | 0.24 | 1.00 | -0.21 [-0.53, 0.78] | 0.24 / 1.00 |
| M3 NFCC rainfall rule | 0.765 | 0.003 [0.001, 0.007] | 3.0× | 0.1410 | 0.09 | 1.00 | 0.15 [-0.47, 0.57] | 0.10 / 1.00 |
| M4 River-discharge percentile | 0.804 | 0.004 [0.001, 0.016] | 4.7× | 0.4181 | 0.53 | 0.99 | 0.67 [0.32, 0.87] | 0.57 / 0.99 |
| M5 Logistic regression, rainfall | 0.631 | 0.003 [0.000, 0.009] | 3.1× | 0.0009 | 0.08 | 1.00 | 0.08 [-0.56, 0.47] | 0.10 / 1.00 |
| M6 Random forest, rainfall | 0.613 | 0.002 [0.000, 0.005] | 2.0× | 0.0009 | 0.09 | 1.00 | -0.02 [-0.54, 0.34] | 0.09 / 1.00 |
| M7 XGBoost, rainfall | 0.643 | 0.002 [0.000, 0.007] | 2.1× | 0.0009 | 0.19 | 1.00 | 0.16 [-0.63, 0.45] | 0.25 / 1.00 |
| M8 XGBoost, rainfall history + soil | 0.652 | 0.002 [0.000, 0.005] | 1.8× | 0.0009 | 0.10 | 1.00 | 0.01 [-0.64, 0.44] | 0.13 / 1.00 |
| M9 XGBoost, multi-source | 0.780 | 0.004 [0.001, 0.015] | 5.2× | 0.0009 | 0.12 | 1.00 | 0.23 [-0.55, 0.61] | 0.30 / 0.99 |

These labels come from MODIS satellite maps and mostly record large river floods.

### 5.10 Operational model (M12) and weekly shadow forecast

**Training:**

- **Data:** M12 is trained on 2015–2024, with 2025 used for early stopping (best iteration 259).
- **Calibration:** Platt scaling, fitted on the out-of-fold forecasts for 2018–2025.
- **Inputs:** listed in section 4.1.
- **Artifact:** `research/flood_experiments/model/` (`model.json`, `meta.json`, `MODEL_CARD.md`).

**Out-of-fold performance (2018–2025):**

| Measure | Value |
| --- | --- |
| Onsets | 750 |
| Base rate | 0.0084 |
| ROC-AUC | 0.810 |
| PR-AUC | 0.051 (6.1× chance) |
| Brier | 0.00817 |
| ECE | 0.0010 |
| Within-district AUC | 0.726 |

**Warning levels.** With calibrated probabilities, acting is worthwhile when P exceeds the action's cost-loss ratio (Murphy 1977). There are two levels:

| Level | Rule | Alerts per year (all 216 districts) | POD | FAR | POD / FAR ±1 week |
| --- | --- | --- | --- | --- | --- |
| WATCH | P ≥ 5% | 217 | 0.19 | 0.92 | 0.21 / 0.84 |
| WARNING | P ≥ 20% | 9 | 0.02 | 0.84 | 0.02 / 0.68 |

**Reliability (calibrated):**

| Mean predicted P | Observed onset rate | District-weeks |
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

**Weekly shadow forecast.** `operational.py shadow` runs every Monday on GitHub Actions and scores all 216 districts:

- **Inputs:** GPM IMERG rain for the past 4 weeks (rescaled to CHIRPS), ERA5-Land, and GloFAS discharge at each main river.
- **Context:** the 51-member ECMWF IFS ensemble forecast is reported alongside, not used as an input.
- **Output:** a CSV per week, on the repository's `shadow-log` branch.
- **Alerts:** none are ever sent.

For the week of 2 November 2026, no district reached WATCH. The highest probabilities were Central Tongu 2.3%, Accra Metropolis 2.0%, Ga South 2.0% and North Tongu 1.6%.

## 6. Partner data: availability

| Dataset | Availability | Open substitute used |
| --- | --- | --- |
| TAHMO station rainfall | Not obtained | CHIRPS v2.0 (training), GPM IMERG V07 (live), ECMWF IFS (forecasts) |
| Ghana Meteorological Agency (GMet) records | Not obtained | Same as above |
| Ghana Hydrological Authority (HSD) river gauges | Not obtained | GloFAS v4 discharge; DAHITI altimetry |
| VRA (Akosombo, Kpong) and SONABEL (Bagre) dam releases | Not obtained | None. The dam pathway uses DAHITI Lake Volta levels and a fixed formula; E2 "+ Dam" not run |
| NADMO flood incident records (dates, districts, people affected) | Not obtained. A request letter is prepared (`research/flood_experiments/nadmo_data_request.md`) and the loader is implemented (`nadmo.py`) | Groundsource news-reported floods. E8 not run |

## 7. Accessible models, datasets and results

Repository: **github.com/NFCC-Ghana/nfcc-platform** (public).

| Item | Location | How to reproduce |
| --- | --- | --- |
| Operational model M12 and model card | `research/flood_experiments/model/` | `python -m research.flood_experiments.operational fit` |
| Model definitions M1–M12, F1–F4 | `research/flood_experiments/models.py`, `experiments.py` | – |
| Main and sensitivity datasets | Rebuilt into `research/flood_experiments/data/` (not stored in git) | `python -m research.flood_experiments.build_dataset` (`NFCC_STUDY=v1_gfd` for v1) |
| Sentinel-1 label audit | `data/v2/raw/sar_audit.csv` | `python -m research.flood_experiments.sar_labels` |
| Archived ECMWF forecasts | `data/v2/raw/forecast_weekly.csv` | `python -m research.flood_experiments.forecast_archive` |
| All experiment results | `research/flood_experiments/results/v2/` and `results/v1_gfd/` (`results.json`, `summary.md`, `figures.png`) | `python -m research.flood_experiments.experiments`, then `... .report` |
| Weekly shadow forecasts | Branch `shadow-log` | GitHub Actions *Weekly Shadow Flood Forecast* |
| Live platform code | `src/` (API), `hackathon/app/` (dashboard) | – |
| Documented flood events (8, 2007–2023) | `src/hydrology/flood_polygons.py` | – |

## 8. Limitations to state in the manuscript

1. **Label completeness and bias.**
   - News-derived labels follow media coverage: urban districts and recent years are over-represented (Groundsource has 124 Ghana events in 2015 and 338 in 2022).
   - Satellite radar confirms rural labels but cannot verify urban ones.
   - MODIS-based labels (v1) miss most urban and flash floods.
2. **Place versus timing.** Much of M11's advantage comes from knowing which districts flood (built-up share is the leading SHAP feature). For timing alone (within-district AUC), the NFCC rainfall rule (M3) is as good as the best model.
3. **Lead time.** Most results use observed rain for the target week (a perfect-forecast hindcast). With real forecasts (E3c), feeding the forecast directly lowers skill. The best real-time model uses no rain forecast, and the NFCC rule applied to real forecasts has almost no skill.
4. **Resolution.** The unit is the district-week. Sub-daily flash-flood timing and street-level extent are not modelled.
5. **Boundaries.** FAO GAUL 2015 (216 districts). Ghana has had 261 districts since 2018.
6. **Missing drivers.** Dam releases, station rainfall and river gauges are unavailable (section 6).
7. **Rare events.** 898 onsets (v2) and 203 (v1). Intervals are wide, especially for single years and the E3c two-year test.
8. **Expert-set parts of the live platform.** The live platform's fusion weights, the drainage factors and the dam formula are expert-set, not validated.

## 9. Results that must not be cited

- **R² = 0.993 for the early Accra XGBoost regressor** (notebook `04_flood_risk_model.ipynb`). Its target was a formula built from its own inputs, so the figure is circular; that model is not part of the system.
- **"100% accuracy" of the dam spillage formula.** It rests on 3 spill events and no non-spill cases.
- **Outcome labels in the live prediction log.** The ReliefWeb keyword search matches national reports to every district.
- **Any skill figure for the NFCC rule (M3) other than those in sections 5.2, 5.4 and 5.9.**

## 10. References

- Alfieri, L. et al. (2013). GloFAS – global ensemble streamflow forecasting and flood early warning. *Hydrology and Earth System Sciences* 17, 1161–1175. doi:10.5194/hess-17-1161-2013
- Breiman, L. (2001). Random forests. *Machine Learning* 45, 5–32. doi:10.1023/A:1010933404324
- Brier, G. W. (1950). Verification of forecasts expressed in terms of probability. *Monthly Weather Review* 78, 1–3.
- Chen, T. & Guestrin, C. (2016). XGBoost: a scalable tree boosting system. *Proc. KDD '16*, 785–794. doi:10.1145/2939672.2939785
- Cox, D. R. (1958). The regression analysis of binary sequences. *Journal of the Royal Statistical Society B* 20, 215–242.
- Efron, B. & Tibshirani, R. J. (1993). *An Introduction to the Bootstrap*. Chapman & Hall.
- FAO (2015). Global Administrative Unit Layers (GAUL) 2015. Food and Agriculture Organization of the United Nations.
- Farr, T. G. et al. (2007). The Shuttle Radar Topography Mission. *Reviews of Geophysics* 45, RG2004. doi:10.1029/2005RG000183
- Ferro, C. A. T. & Stephenson, D. B. (2011). Extremal dependence indices: improved verification measures for deterministic forecasts of rare binary events. *Weather and Forecasting* 26, 699–713. doi:10.1175/WAF-D-10-05030.1
- Funk, C. et al. (2015). The climate hazards infrared precipitation with stations – a new environmental record for monitoring extremes. *Scientific Data* 2, 150066. doi:10.1038/sdata.2015.66
- Hanley, J. A. & McNeil, B. J. (1982). The meaning and use of the area under a receiver operating characteristic (ROC) curve. *Radiology* 143, 29–36.
- Harrigan, S. et al. (2020). GloFAS-ERA5 operational global river discharge reanalysis 1979–present. *Earth System Science Data* 12, 2043–2060. doi:10.5194/essd-12-2043-2020
- Huffman, G. J. et al. (2023). GPM IMERG Final Precipitation L3 Half Hourly 0.1 degree x 0.1 degree V07. NASA GES DISC. doi:10.5067/GPM/IMERG/3B-HH/07
- Lundberg, S. M. & Lee, S.-I. (2017). A unified approach to interpreting model predictions. *Advances in Neural Information Processing Systems* 30, 4765–4774.
- Lundberg, S. M. et al. (2020). From local explanations to global understanding with explainable AI for trees. *Nature Machine Intelligence* 2, 56–67. doi:10.1038/s42256-019-0138-9
- Mayo, R. et al. (2026). Groundsource: a dataset of flood events from news. EarthArXiv preprint. Data: doi:10.5281/zenodo.18647054
- Mitchell, M. et al. (2019). Model cards for model reporting. *Proc. FAT* '19*, 220–229. doi:10.1145/3287560.3287596
- Muñoz-Sabater, J. et al. (2021). ERA5-Land: a state-of-the-art global reanalysis dataset for land applications. *Earth System Science Data* 13, 4349–4383. doi:10.5194/essd-13-4349-2021
- Murphy, A. H. (1977). The value of climatological, categorical and probabilistic forecasts in the cost-loss ratio situation. *Monthly Weather Review* 105, 803–816.
- Naeini, M. P., Cooper, G. & Hauskrecht, M. (2015). Obtaining well calibrated probabilities using Bayesian binning. *Proc. AAAI '15*, 2901–2907.
- OASIS (2010). Common Alerting Protocol Version 1.2. OASIS Standard.
- Pearl, J. (1988). *Probabilistic Reasoning in Intelligent Systems*. Morgan Kaufmann.
- Pedregosa, F. et al. (2011). Scikit-learn: machine learning in Python. *Journal of Machine Learning Research* 12, 2825–2830.
- Pekel, J.-F. et al. (2016). High-resolution mapping of global surface water and its long-term changes. *Nature* 540, 418–422. doi:10.1038/nature20584
- Pesaresi, M. & Politis, P. (2023). GHS-BUILT-S R2023A – GHS built-up surface grid. European Commission, Joint Research Centre. doi:10.2905/9F06F36F-4B11-47EC-ABB0-4F8B7B1D72EA
- Platt, J. (1999). Probabilistic outputs for support vector machines and comparisons to regularized likelihood methods. *Advances in Large Margin Classifiers*, 61–74.
- Reichle, R. H. et al. (2019). Version 4 of the SMAP Level-4 soil moisture algorithm and data product. *Journal of Advances in Modeling Earth Systems* 11, 3106–3130. doi:10.1029/2019MS001729
- Richardson, D. S. (2000). Skill and relative economic value of the ECMWF ensemble prediction system. *Quarterly Journal of the Royal Meteorological Society* 126, 649–667. doi:10.1002/qj.49712656313
- Saito, T. & Rehmsmeier, M. (2015). The precision-recall plot is more informative than the ROC plot when evaluating binary classifiers on imbalanced datasets. *PLoS ONE* 10, e0118432. doi:10.1371/journal.pone.0118432
- Schwatke, C. et al. (2015). DAHITI – an innovative approach for estimating water level time series over inland waters using multi-mission satellite altimetry. *Hydrology and Earth System Sciences* 19, 4345–4364. doi:10.5194/hess-19-4345-2015
- Tatem, A. J. (2017). WorldPop, open data for spatial demography. *Scientific Data* 4, 170004. doi:10.1038/sdata.2017.4
- Tellman, B. et al. (2021). Satellite imaging reveals increased proportion of population exposed to floods. *Nature* 596, 80–86. doi:10.1038/s41586-021-03695-w
- Torres, R. et al. (2012). GMES Sentinel-1 mission. *Remote Sensing of Environment* 120, 9–24. doi:10.1016/j.rse.2011.05.028
- UN-SPIDER (2019). Recommended Practice: Flood mapping and damage assessment using Sentinel-1 SAR data in Google Earth Engine. United Nations Office for Outer Space Affairs.
- Wilks, D. S. (2011). *Statistical Methods in the Atmospheric Sciences*, 3rd ed. Academic Press.
- Yamazaki, D. et al. (2019). MERIT Hydro: a high-resolution global hydrography map based on latest topography dataset. *Water Resources Research* 55, 5053–5073. doi:10.1029/2019WR024873
- Zadrozny, B. & Elkan, C. (2002). Transforming classifier scores into accurate multiclass probability estimates. *Proc. KDD '02*, 694–699. doi:10.1145/775047.775151
- Zippenfenig, P. (2023). Open-Meteo.com Weather API. Zenodo. doi:10.5281/zenodo.7970649
