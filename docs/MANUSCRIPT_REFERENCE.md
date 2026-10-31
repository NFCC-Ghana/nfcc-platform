# NFCC flood early-warning system: full system report

*State of the system on 31 October 2026. Prepared for the NFCC manuscript team. This is a complete technical description and critical review of the whole system: the deployed platform, its data, models, software, infrastructure, operating record and research framework. Every results number is generated from the project's result files (`research/flood_experiments/results/`); the operating record is generated from a snapshot of the production database (`results/operations/snapshot.json`, aggregate counts only).*

**How the review was done.** Every module of the platform (`src/`, 90 modules), the dashboard, the scheduled jobs and the infrastructure configuration were read; every one of the 54 API operations was listed from the OpenAPI specification with its access control; the production database, logs and job history were queried; and data flows were checked against the live external services. The review is organised the way operational early-warning systems are assessed and published: the four pillars of the WMO/UNDRR Multi-Hazard Early Warning Systems (MHEWS) checklist (risk knowledge; detection, monitoring and forecasting; warning dissemination; preparedness and response), with the forecasting models reported against TRIPOD+AI (Collins et al. 2024), model cards (Mitchell et al. 2019) and datasheets for datasets (Gebru et al. 2021). Defects found are listed with evidence and status in section 9.

## How to read this document

NFCC has two parts, and the manuscript should keep them distinct:

1. **The operational platform:** the live, rule-based flood-risk and alerting system. It runs on Google Cloud Run for 9 tracked districts and is used through a Streamlit dashboard. It is described in section 2 and its operating record in section 8.
2. **The research and forecasting framework:** a reproducible machine-learning study on all 216 districts of Ghana (FAO GAUL 2015 boundaries), with an operational model that runs weekly in *shadow mode* (scored and logged, never used for alerts). It is described in sections 3–5.

Section 1 summarises the system and its readiness; section 9 is the critical review (every defect found, with evidence); section 10 maps the document to the MHEWS pillars and to TRIPOD+AI.

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
| 2 | Is the dashboard connected to all data sources? | **Partly.** It is integrated with 10 real sources (one of them, DAHITI, has returned no data since 22 Sep 2026 because its API key is rejected; section 9, F3): GPM IMERG V07, CHIRPS v2.0, Open-Meteo forecast, GloFAS v4, NASA SMAP L4, Sentinel-1 GRD, DAHITI altimetry (Lake Volta, White Volta, Nakambé), ReliefWeb, GDELT and citizen reports. It is **not** connected to Ghana Hydrological Authority river gauges, VRA or SONABEL dam operator data, Google Flood Hub, TAHMO or GMet; those require data agreements or API approval (section 6). All external APIs and services are listed in section 2.6. "Phase 2" items in the project plan (nowcasting, inundation model, insurance trigger API, SMS at scale) are not built. Section 2.2. |
| 3 | Do the experiments cover Accra alone or many districts? | **All 216 districts in all 10 (2015) regions**, for 2015–2025 (main study) and 2000–2018 (sensitivity study). The live platform tracks 9 districts. Sections 3.1 and 5.1. |
| 4 | Were TAHMO, GMet and river-gauge data available? | **No.** None was obtained. Open satellite and reanalysis products were used instead (CHIRPS, IMERG, ERA5-Land, GloFAS). Section 6. |
| 5 | What models, datasets and results are accessible? | Everything in this document is in the public repository **NFCC-Ghana/nfcc-platform** and can be regenerated from open data. Section 7 lists each item and where it is. |

## 1. Executive summary and readiness

**What the system is.** NFCC is a flood early-warning system for Ghana in two parts. The *operational platform* computes a rule-based flood-risk score from rainfall for 9 tracked districts every few hours, combines it with river, reservoir, satellite-radar and citizen evidence, and places any assessment of MODERATE risk or above in a review queue; a person must approve an alert before it is sent by WhatsApp or Telegram, and every alert is also available in the OASIS Common Alerting Protocol (CAP 1.2). The *research framework* is a reproducible study of weekly flood-onset prediction for all 216 districts (2015–2025), comparing 11 models and 4 data-fusion methods, with a calibrated XGBoost model running weekly in shadow mode.

**What the evidence supports.**

- **Forecast skill (research, test years 2018–2025).** The best model (M11, multi-source XGBoost with local-climate rainfall) reaches PR-AUC 0.081 against a base rate of 0.0084 (9.6× chance) and SEDI 0.49. The live platform's rainfall rule (M3) reaches PR-AUC 0.030 (3.6× chance), below the seasonal climatology baseline (0.048). For *timing* within a district the rule is as good as any model (within-district AUC 0.80 vs 0.78); M11's advantage is mostly in knowing *which* districts flood (section 5.3).
- **Rainfall inputs.** At Ghana's 22 synoptic stations, satellite rainfall agrees poorly with gauges day by day (Pearson r 0.26 CHIRPS, 0.33 IMERG) and detects under a third of ≥20 mm gauge days, but agrees well week by week (r 0.75–0.76 on fully reported gauge weeks; 0.66 when days without a rain report are counted as dry). This supports the study's weekly design and argues against daily heavy-rain thresholds on satellite rain (section 5.11).
- **Operational use.** The platform has run in production since September 2026 but has not yet been used operationally: 58 assessments queued, none reviewed by an operator; 0 alert subscribers; 4 citizen reports, all tests (section 8).

**Readiness.** The platform is a working, documented prototype, not yet an operational warning service. The review found defects that must be corrected or disclosed before any operational or published claim (section 9), most importantly:

1. the outcome labels in the live prediction log are invalid (940 of the 943 predictions checked so far were marked "flood confirmed" on evidence that did not concern the district);
2. the live rainfall forecast input read only large-scale rain, 35–44% of total precipitation in Ghana;
3. the river and dam pathway has had no data since 22 September 2026 (the DAHITI API key is rejected);
4. the dashboard opened on a fixed 75 mm "EXTREME" scenario, and showed illustrative impact figures on dry days;
5. citizen reporters' phone numbers were publicly readable through the API.

Fixes for 1, 2, 4 and 5 are written and tested (pull requests #68–#72, awaiting merge and deployment); 3 needs a new DAHITI key from the account owner.

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
| 3 | Open-Meteo Forecast API (`api.open-meteo.com/v1/forecast`, default "best match" model selection) | Open-Meteo | Hourly; 3-day horizon | 24/48/72-hour rainfall forecast, rain probability, current weather | Connected. Reports "unavailable" with no values when unreachable. Defect: reads the `rain` variable (large-scale rain only) instead of `precipitation`, and counts hours from 00:00 GMT; fix in PR #68 (section 9, F2) |
| 4 | GloFAS v4 river discharge (`flood-api.open-meteo.com/v1/flood`) | Copernicus Emergency Management Service, via Open-Meteo | 0.05°; daily | River pathway: discharge relative to the day's long-term mean (≥1.5× = elevated; illustrative, not a calibrated flood stage) | Connected |
| 5 | NASA SMAP L4 surface and root-zone soil moisture (`NASA/SMAP/SPL4SMGP/008`) | NASA, via Earth Engine | 9 km, 3-hourly; 2–3 days latency | Soil saturation | Connected |
| 6 | Sentinel-1 GRD C-band SAR (`COPERNICUS/S1_GRD`), IW mode, VV and VH | ESA Copernicus, via Earth Engine | 10 m; revisit 6–12 days over Ghana | Flood detection by change detection (section 2.4) | Connected. Reports "unavailable" (no detection, no area) when Earth Engine is unreachable or there is no image in the last 12 days |
| 7 | DAHITI satellite altimetry (`dahiti.dgfi.tum.de`, API v2; requires an API key) | DGFI-TUM | Water-level time series per target, at each satellite overpass | Three targets: Lake Volta, for Akosombo Dam (target 97); White Volta river level for Tamale only (target 9087, about 45.5 km away); Nakambé River (target 19006, about 22.4 km from Bagre Dam, Burkina Faso), an upstream proxy for Bagre releases, reported separately from the dam's own (unavailable) status | **Not working since 22 Sep 2026:** the API key is rejected (HTTP 403, "Login failed"), so no river or dam level has been read since (section 9, F3) |
| 8 | ReliefWeb API v2 (`api.reliefweb.int/v2/reports`) | UN OCHA | Reports, country-tagged | Post-event outcome evidence | Connected. Defect: the query matched unrelated reports, so its outcome labels are invalid; fix in PR #69 (section 9, F1). After the fix it can confirm a district only when a report title names the town |
| 9 | GDELT DOC 2.0 API (`api.gdeltproject.org/api/v2/doc/doc`) | GDELT Project | News articles | Post-event outcome evidence | Connected (city-level at best) |
| 10 | Citizen flood reports | NFCC community reporting (database `community_reports`) | Event-level | Direct-observation pathway, after verification | Connected; no real report received yet (4 test reports, none verified) |
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

**Where the drainage multiplier applies.** Only the dashboard's `/situation` call passes the district to `calculate_score`. The 3-hourly assessment (`/v1/alerts/assess`), `/score`, `/v1/districts/{district}/risk` and the risk history score the same rainfall without it, so for the three Accra districts the dashboard and the alert queue can show different scores for the same rain (section 9, F10).

**What the input rainfall is.** The 3-hourly assessment scores three signals separately for each district: (a) the next-24-hour Open-Meteo forecast; (b) the 3-day antecedent total, from GPM IMERG via the API (since 30 Oct 2026; before that CHIRPS, which was 18–30 days out of date, so every assessment fell back to Open-Meteo's past-72-hour model rainfall); and (c) the river/dam pathway score. The review threshold S ≥ 30 corresponds to 10 mm of rain in 24 hours, a common wet-season amount.

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

where rainfall is normalised over 0–200 mm, reservoir level over 0–100% and inflow over 0–500 m³/s. It is a formula, not a fitted model. It is exposed only through `/api/dam/spillage`, which, with no inputs supplied, evaluates fixed defaults (180 mm, 95%, 450 m³/s for Akosombo), so it returns the same result on every call; it is not used in the risk score or the alerts.

**River and dam pathway score** (`src/hydrology/fluvial_pathway.py`, `altimetry_thresholds.py`). Each DAHITI water body is classified against percentiles of its own history and mapped to a score: below the 75th percentile NORMAL = 15; 75th–90th WARNING = 45; 90th–95th DANGER = 75; above the 95th FLOOD = 95. Because WARNING (45) exceeds the review threshold (30), any river or lake above its 75th percentile, a normal wet-season level, queues a MODERATE alert (section 9, F9).

### 2.5 Alerting, explanation and infrastructure

- **Human-in-the-loop alerting:** risk assessments create *pending* alerts, which an operator approves, dismisses or retracts on the dashboard.
- **Alert channels:** WhatsApp (Twilio) and Telegram (Bot API) are configured in production; SMS (Twilio) and email (SMTP) are implemented but disabled. Recipients are a configured list plus citizens who opted in by sending "ALERTS ON" on WhatsApp or Telegram.
- **Approval:** approving, cancelling or dismissing a real alert needs the API key and, when configured, a second alert-approval key. Approving an exercise alert never reaches the sending code.
- **Alert format:** each alert is also served as an OASIS Common Alerting Protocol (CAP 1.2) document.
- **Exercise mode:** produces practice alerts that are never sent.
- **AI copilot:** answers questions about districts by calling the platform's own tools. Model: Google Gemini (`gemini-flash-lite-latest`).
- **Hosting:** FastAPI service on Google Cloud Run (europe-west1; exactly one instance, 1 vCPU, 2 GiB, 4 uvicorn workers; CPU allocated only during requests), with two SQLite databases (`alerts.db`, `community_reports.db`, WAL mode) continuously replicated to Google Cloud Storage by Litestream 0.5.17. API rate limits and alert cooldowns are designed to be shared through Upstash Redis; the Redis database no longer exists, so each worker currently keeps its own in-memory counters (section 9, F7).
- **Dashboard:** Streamlit, on Streamlit Community Cloud.

**Scheduled jobs (GitHub Actions):**

| Job | Schedule |
| --- | --- |
| Risk assessment for all tracked districts | Every 3 hours (about 4 runs a day actually execute; GitHub drops scheduled runs) |
| Prediction outcome verification | Daily, 06:00 UTC |
| CHIRPS ingestion (Accra box, saved as a build artifact; not read by the platform) | Daily, 08:00 UTC |
| Rule validation report | Monthly, 1st, 07:00 UTC |
| Resilience tests | Daily, 02:00 UTC |
| Weekly shadow flood forecast (section 5.10) | Mondays, 05:17 UTC |

### 2.6 Complete list of external APIs and services

| Service | Endpoint / interface | Used for | Authentication | Used by |
| --- | --- | --- | --- | --- |
| Google Earth Engine | `earthengine-api` (Python) | Platform: CHIRPS, GPM IMERG, NASA SMAP, Sentinel-1. Research: all gridded predictors and labels (section 3.3) | Google Cloud service account | Platform, research |
| Open-Meteo Forecast API | `api.open-meteo.com/v1/forecast` | Rainfall forecast, current weather | None (free tier) | Platform |
| Open-Meteo Flood API (GloFAS v4) | `flood-api.open-meteo.com/v1/flood` | River discharge | None (free tier) | Platform, research |
| Open-Meteo Ensemble API (ECMWF IFS, 51 members) | `ensemble-api.open-meteo.com/v1/ensemble` | Next-week rain context in the shadow forecast | None (free tier) | Research (shadow run) |
| Open-Meteo Previous Runs API (ECMWF IFS 0.25°) | `previous-runs-api.open-meteo.com/v1/forecast` | Archived forecasts for experiment E3c | None (free tier) | Research |
| DAHITI API v2 | `dahiti.dgfi.tum.de/api/v2/download-water-level` | Lake Volta, White Volta and Nakambé water levels | API key | Platform |
| ReliefWeb API v2 | `api.reliefweb.int/v2/reports` | Flood reports (outcome evidence) | Registered application name | Platform |
| GDELT DOC 2.0 API | `api.gdeltproject.org/api/v2/doc/doc` | News articles (outcome evidence) | None | Platform |
| Google Flood Forecasting API | `floodforecasting.googleapis.com/v1` | River flood forecasts | API key (not yet issued) | Platform (inactive) |
| Twilio | Twilio Python SDK | WhatsApp and SMS alerts | Account SID + auth token | Platform (alerting) |
| Telegram Bot API | `api.telegram.org` | Telegram alerts and subscriptions | Bot token + webhook secret | Platform (alerting) |
| SMTP email (Gmail) | Python `smtplib` | Email alerts | SMTP user + app password | Platform (alerting) |
| Google Gemini API | `google-genai` SDK, model `gemini-flash-lite-latest` | AI copilot | API key | Platform (copilot) |
| Upstash Redis | Redis protocol | Shared API rate limits | Connection URL with password | Platform |
| Google Cloud Run, Cloud Storage, Secret Manager, Cloud Build | Google Cloud | API hosting; Litestream database replicas; secrets; container builds | Google Cloud service accounts | Platform |
| Streamlit Community Cloud | – | Dashboard hosting | – | Platform |
| GitHub Actions | – | Scheduled jobs (section 2.5) | Repository secrets | Platform, research |

**Dams covered:**
- **Akosombo (Volta, Ghana):** Lake Volta level from DAHITI; no VRA operator data.
- **Bagre (Nakambé, Burkina Faso):** no operator data; DAHITI upstream river proxy only.
- **Kompienga (Burkina Faso):** no data source.

### 2.7 Software architecture and code base

| Component | Location | Size (lines of Python) | Role |
| --- | --- | --- | --- |
| Platform API (FastAPI) | `src/` (90 modules) | 14,513 | Scoring, evidence fusion, data adapters, alerting, verification, copilot |
| Operations dashboard (Streamlit) | `hackathon/app/pages/dashboard.py`, `modules/v4/` | 4,795 | Operator interface, public kiosk view, alert review queue |
| Scheduled jobs and tools | `scripts/` | 2,423 | 3-hourly assessment, outcome verification, CHIRPS ingestion, validation reports |
| Research framework | `research/flood_experiments/` | 4,685 | Dataset building, experiments, operational model, this report |
| Tests | `tests/` | 12,082 | 623 test functions |

The repository has 283 commits between 3 May and 31 October 2026. The platform API is organised in layers: data adapters (`src/hydrology/`: one module per external source, each returning an explicit "unavailable" result instead of a substitute value when its source fails), models (`src/models/`: score timelines, evidence fusion, verification), exposure data (`src/exposure/`), alerting (`src/alerts/`: tiering, cooldown, rate limit, providers), persistence (`src/database/`), verification (`src/verification/`) and HTTP routes (`src/api/`).

**Data flow of an alert.** GitHub Actions job (every 3 h) → fetch forecast (Open-Meteo), antecedent rain and river/dam score (platform API) → `POST /v1/alerts/assess` per signal → if S ≥ 30, a row in `pending_alerts` with CAP severity, urgency and certainty, affected communities and response guidance → operator approves in the dashboard → `AlertEngine.process` checks cooldown (30 min) and rate limit (3 alerts per district per hour) → WhatsApp/Telegram providers → row in `alerts`. Each run also writes a risk-history point, three observation-archive rows and one prediction-ledger entry per district.

### 2.8 API and access control

The API has **54 operations** (OpenAPI specification generated from `src/api/main.py`). Access control:

- **API key required (17):** every operation that writes data or can send, approve, cancel or dismiss an alert; the alert queue and CAP export; the alert subscriber list; the copilot; and `POST /situation` and `POST /decision/card`.
- **Second key (alert-approval key):** additionally required to approve, cancel or dismiss a real (non-exercise) alert, when configured.
- **Signed webhooks (2):** `POST /webhooks/whatsapp` checks Twilio's request signature; `POST /webhooks/telegram` checks Telegram's secret token (constant-time comparison).
- **Public (35):** health checks, district registry, read-only risk, forecast, evidence, resources, decision, history, observations, predictions, data quality, verification and backtest results, the public scoring and explanation endpoints, and the dam spillage endpoints.

Request rate limits (slowapi) are set on only two operations: `/situation` (30 per minute) and `/v1/copilot/ask` (10 per minute). Public operations that run the full evidence pipeline (for example `GET /v1/districts/{district}/decision`) are not limited (section 9, F15). If `API_KEY` is not set, the key check accepts every request; production has it set (F14).

### 2.9 Data stores

All tables are SQLite, in `data/alerts.db` except community reports (`data/community_reports.db`).

| Table | Content | Written by |
| --- | --- | --- |
| `pending_alerts` | Review queue: district, score, tier, rainfall, message, CAP severity/urgency/certainty/status, affected communities, response guidance, signal (basis), review status and reviewer | `POST /v1/alerts/assess`, `/exercise` |
| `alerts` | Every send attempt: district, score, tier, rainfall, sent flag, provider, recipient | Alert engine |
| `channel_subscriptions` | Citizen opt-ins: channel, identifier (phone number or chat id), district, minimum tier, active | WhatsApp/Telegram webhooks |
| `risk_history` | Time series of score and tier per district | 3-hourly job |
| `observation_history` | Every raw reading fetched by the 3-hourly job, with unit and quality flag | 3-hourly job |
| `prediction_ledger` | Full decision-card snapshot per district per run, with outcome, outcome source and time once verified | 3-hourly job; outcome verifier |
| `community_reports` | Citizen reports: district, community, type, depth, description, reporter contact, time, location, urgency, validation | Webhooks; operator validation |

### 2.10 Operator dashboard and AI copilot

**Dashboard panels** (`hackathon/app/pages/dashboard.py`): header and data-source status; control panel (district, rainfall); executive summary; national map; evidence and confidence; impact assessment; operations (shelters, resources); decision centre (decision card); risk timeline (+6/+12/+18/+24 h); recorded risk history; AI copilot; alert review queue (approve, dismiss, retract, CAP download, exercise alerts); community-report triage; a full-screen public kiosk view (live forecast, auto-refreshing); and a demonstration mode that plays a scripted sequence of rainfall values through the real API.

**What the dashboard's figures mean.** Every panel except the kiosk is computed from the rainfall value in the control panel, so the dashboard is a scenario tool around the live forecast, not a display of measured conditions. The slider opened at a fixed 75 mm (score 100, EXTREME) whatever the weather; it now opens at the live 24-hour forecast and labels any other value "SCENARIO" (PR #72). The impact panel's illustrative generator (`state_fallback.py`) was shown whenever the real estimate was zero, that is on every dry day; it is now shown only when the API returns no estimate (PR #71).

**Impact estimate** (`src/exposure/impact_estimator.py`). Population exposed = district population × (S/100) × 0.6; children, elderly, disabled and pregnant shares and school, hospital and market counts are project planning estimates; power substations = population/75,000. Populations for Tema, Kumasi, Tamale, Cape Coast, Ho and Sunyani are 2021 census figures; the three Accra districts are project estimates (they are not official units). It is a score-proportional planning heuristic, not an exposure model (no hazard map is overlaid on population).

**AI copilot** (`src/copilot/`). Google Gemini through the `google-genai` SDK, model alias `gemini-flash-lite-latest` (not a pinned version), with 8 tools that call the platform's own data (tracked districts, risk overview, decision card, evidence, forecast, resources, data-source health, data quality), at most 8 tool calls per question. The system instruction forbids stating any figure not returned by a tool in the same conversation. The answer is returned with the list of tool calls that produced it. Its accuracy and grounding have not been evaluated (F20).

### 2.11 Data quality control

`GET /v1/data-quality` applies tests from the QARTOD real-time quality-control manuals (US IOOS): a gross-range test (rainfall 0–500 mm/day; soil moisture 0–0.9 m³/m³; water level −50–500 m) and a freshness test (altimetry 35 days + 2 days processing; SMAP 72 h), for the Open-Meteo forecast (Accra Central), the Tamale river level, the Lake Volta level and SMAP soil moisture. Flat-line and spike tests are implemented (`src/data_quality/quality_checks.py`) but not applied, and IMERG, GloFAS and Sentinel-1 are not checked (F16). `GET /v1/health/data-sources` reports whether each source is configured; it does not test that a configured key still works, so DAHITI shows "configured" while every call fails (F3).

### 2.12 Verification and archives

- **Rule validation** (`src/models/rare_event_verification.py`, `historical_backtest.py`; `GET /v1/verification`, `/v1/backtest`): the rule scored on 36.7 years of CHIRPS rainfall at each district, and its behaviour before 8 documented floods (2007–2023, `src/hydrology/flood_polygons.py`). These are descriptive checks; the skill of the rule is measured properly in the research framework (M3, sections 5.2–5.4).
- **Prediction ledger and outcome verifier** (`src/verification/outcome_verifier.py`): 3–30 days after each prediction, four sources are searched for a flood in that district in the following 14 days (ReliefWeb, GDELT news, at least 3 verified citizen reports, a Sentinel-1 detection); any one confirms. The ReliefWeb search matched unrelated reports, so the recorded outcomes are invalid (F1). Even when correct, the design gives a weak verification sample: a prediction every 3 hours with overlapping 14-day windows, and evidence sources that mostly cannot resolve a district (F22).

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

### 5.11 Satellite rainfall against station gauges

**Why.** Every rainfall input in the study (CHIRPS v2.0) and the live platform (GPM IMERG V07 for antecedent rain) is satellite-based. Neither TAHMO nor GMet data were available (section 6), but GMet's synoptic stations are exchanged internationally through the WMO and republished by NOAA in the Global Surface Summary of the Day (GSOD). This checks both products against those gauges.

**Data and method** (`research/flood_experiments/station_check.py`):

- **Gauges:** NOAA GSOD daily precipitation for the 22 Ghana stations active since 2015, 2015-01-01 to 2025-08-31.
- **Gauge quality control:** of 62,545 station-days, only complete 24-hour totals are used (flags D, F, G: 16,668 days). Flag I (38,028 days) means no precipitation report, not a measured zero; A, B, C, E and H are partial-day sums; 99.99 is missing.
- **Satellite:** the value of the 0.05° CHIRPS cell and the 0.1° IMERG cell containing each station (IMERG daily total = sum of the 48 half-hourly rates × 0.5 h; days with fewer than 48 half-hours dropped).
- **Day alignment:** a lag test gave correlations of 0.22 (same day) and 0.33 (gauge day matched to the previous satellite day) for IMERG, so the gauge's 24-hour total ends in the morning and gauge day *d* is compared with satellite day *d* − 1.
- **Weeks:** Monday-to-Sunday totals, only for weeks with all 7 gauge days.
- **Two gauge definitions:** *strict* (D/F/G only) and *I as dry* (also counting flag I as 0 mm). The stations send the 24-hour group mainly on rainy days (3% of January days have a complete flag, 45% of September days), so strict days are skewed wet and give few complete weeks (156); counting I as dry gives 2,355 weeks. On I days both products average about 1.5 mm, against about 4.6 mm on strict 0.0 mm days, so I days are mostly, but not all, dry.
- **Metrics:** Pearson r and Spearman ρ; volume ratio (satellite total ÷ gauge total); POD, FAR and CSI for rain ≥ 1 mm, for ≥ 20 mm, and for each series' own station-wise 95th percentile of wet days (a detection test that a volume bias cannot distort); for weeks, r, the correlation of anomalies from each station's week-of-year mean, and detection of each series' own wettest 10% of weeks.

**Results: strict gauges** (16,668 station-days, 156 complete weeks):


| Product | Daily r | Daily ρ | Volume ratio (sat ÷ gauge) | Rain ≥1 mm POD / FAR / CSI | ≥20 mm POD / FAR | Own 95th pct POD / FAR | Weekly r | Weekly anomaly r | Wettest 10% of weeks POD / FAR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CHIRPS v2.0 | 0.26 | 0.27 | 0.88 | 0.62 / 0.41 / 0.43 | 0.22 / 0.69 | 0.13 / 0.87 | 0.75 | 0.52 | 0.38 / 0.62 |
| GPM IMERG V07 | 0.33 | 0.36 | 0.97 | 0.71 / 0.40 / 0.48 | 0.33 / 0.63 | 0.23 / 0.80 | 0.76 | 0.61 | 0.54 / 0.46 |


**Results: flag I counted as dry** (54,678 station-days, 2,355 complete weeks):


| Product | Daily r | Daily ρ | Volume ratio (sat ÷ gauge) | Rain ≥1 mm POD / FAR / CSI | ≥20 mm POD / FAR | Own 95th pct POD / FAR | Weekly r | Weekly anomaly r | Wettest 10% of weeks POD / FAR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CHIRPS v2.0 | 0.30 | 0.34 | 1.38 | 0.62 / 0.68 / 0.27 | 0.22 / 0.77 | 0.18 / 0.91 | 0.66 | 0.53 | 0.54 / 0.46 |
| GPM IMERG V07 | 0.35 | 0.40 | 1.43 | 0.71 / 0.65 / 0.30 | 0.33 / 0.72 | 0.27 / 0.86 | 0.66 | 0.57 | 0.53 / 0.47 |


**By climate zone** (daily and volume ratio: strict; weekly: I as dry):


| Zone | Stations | CHIRPS daily r | IMERG daily r | CHIRPS weekly r | IMERG weekly r | CHIRPS volume ratio | IMERG volume ratio |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Coast (<6°N) | 7 | 0.35 | 0.40 | 0.71 | 0.73 | 0.86 | 0.99 |
| Forest-transition (6-8°N) | 10 | 0.23 | 0.32 | 0.61 | 0.60 | 0.88 | 0.94 |
| Northern savanna (>=8°N) | 5 | 0.17 | 0.24 | 0.69 | 0.70 | 0.92 | 1.02 |


**Stations nearest the tracked districts** (Cape Coast has no synoptic station; Saltpond is 30 km east). Per-station results for all 22 stations: `results/station_check/by_station.csv`.


| District | Station | Gauge days (strict) | CHIRPS daily r | IMERG daily r | Weeks (I as dry) | CHIRPS weekly r | IMERG weekly r |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Accra Central/West/East | Kotoka Intl | 964 | 0.34 | 0.35 | 231 | 0.65 | 0.69 |
| Tema | Tema | 541 | 0.22 | 0.34 | 104 | 0.44 | 0.64 |
| Kumasi | Kumasi | 937 | 0.33 | 0.45 | 99 | 0.56 | 0.43 |
| Tamale | Tamale | 735 | 0.27 | 0.30 | 159 | 0.77 | 0.73 |
| Cape Coast | Saltpond | 825 | 0.26 | 0.33 | 114 | 0.64 | 0.66 |
| Ho | Ho | 549 | 0.28 | 0.46 | 48 | 0.57 | 0.58 |
| Sunyani | Sunyani | 930 | 0.13 | 0.33 | 157 | 0.64 | 0.70 |


**Interpretation.**

1. **Daily point agreement is low** for both products (r about 0.26–0.33), and heavy-rain days are poorly detected: of gauge days with ≥ 20 mm, CHIRPS also had ≥ 20 mm on 22% and IMERG on 33%, with false-alarm ratios of 0.69 and 0.63. Part of this is the mismatch between a rain gauge (a point) and a 5–11 km grid cell during convective storms, not satellite error alone.
2. **Weekly agreement is good** (r 0.75–0.76 strict, 0.66 with I as dry) and survives removal of the seasonal cycle (anomaly r 0.53–0.57). This supports the district-week design of the study.
3. **IMERG matches the gauges at least as well as CHIRPS** on every daily measure, which supports using IMERG for the platform's live antecedent rainfall.
4. **Volume:** on strict days the satellite totals are close to the gauges (ratio 0.88 CHIRPS, 0.97 IMERG). With flag I counted as dry the satellites exceed the gauges by about 40%, which is the upper bound of the bias, since some I days had rain.
5. **For the live rule:** a daily threshold applied to satellite or model rainfall (the rule's 10 mm review threshold) will miss most heavy local rain and raise many false alarms at the scale of a town.

**Caveats.** CHIRPS blends GTS station reports, which include these stations, so its agreement is partly built in; IMERG Final is adjusted to monthly GPCC gauge totals. Neither comparison is fully independent; IMERG is the closer to it. GSOD ends on 24 Aug 2025 for most stations and has no data for Ada after 2022.


## 6. Partner data: availability

None of these datasets has a public, real-time interface. Each needs a data-sharing agreement or an API approval from its owner before the platform can connect to it.

| Dataset | Availability | What connecting it requires | Open substitute used |
| --- | --- | --- | --- |
| TAHMO station rainfall (Trans-African Hydro-Meteorological Observatory) | Not obtained | A research data agreement with TAHMO; TAHMO then issues API credentials | CHIRPS v2.0 (training), GPM IMERG V07 (live), ECMWF IFS (forecasts) |
| Ghana Meteorological Agency (GMet) station records | Not obtained | A data-sharing request to GMet | Same as above. GMet's main synoptic stations (e.g. Accra Kotoka, Tamale) are also exchanged internationally through the WMO and republished by NOAA (Global Surface Summary of the Day). That copy ends on 24 Aug 2025, so it serves for historical validation (section 5.11) but not as a live feed |
| Ghana Hydrological Authority river gauges | Not obtained | A data-sharing agreement with the Ghana Hydrological Authority | GloFAS v4 discharge; DAHITI altimetry |
| VRA dam data (Akosombo, Kpong) and SONABEL data (Bagre, Kompienga; Burkina Faso) | Not obtained | Data agreements with the Volta River Authority and SONABEL, or through the Volta Basin Authority | DAHITI Lake Volta level and Nakambé river level (Bagre proxy). The dam spillage index is a fixed formula. E2 "+ Dam" not run |
| Google Flood Hub forecasts | API not issued | Approval for the Google Flood Forecasting API pilot. The platform's client is already implemented and activates once an API key is set | GloFAS v4 discharge |
| NADMO flood incident records (dates, districts, people affected) | Not obtained | A data request to NADMO. The request letter is prepared (`research/flood_experiments/nadmo_data_request.md`) and the loader is implemented (`nadmo.py`) | Groundsource news-reported floods. E8 not run |

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
| Station-rainfall check | `research/flood_experiments/results/station_check/` (`results.json`, `by_station.csv`) | `python -m research.flood_experiments.station_check fetch`, `extract`, `analyse` |
| Operating record of the deployed platform | `research/flood_experiments/results/operations/snapshot.json` (aggregate counts only) | `python scripts/operations_snapshot.py` (needs the API key) |
| This report | `docs/MANUSCRIPT_REFERENCE.md` | `python -m research.flood_experiments.reference` |


## 8. Operating record of the deployed platform

Snapshot of the production database and job history taken 2026-10-31 03:39 UTC (`results/operations/snapshot.json`, produced by `scripts/operations_snapshot.py`; aggregate counts only).

**Alert review queue.** 58 assessments were queued between 2026-09-19 and 2026-10-16:

- by signal: 3-day antecedent rain, Open-Meteo fallback 41; River/dam pathway score (DAHITI) 11; Next-24 h forecast (Open-Meteo) 6;
- by tier: MODERATE 48; HIGH 8; EXTREME 2;
- by district: Tamale 29; Kumasi 11; Ho 11; Sunyani 5; Accra West 1; Accra Central 1;
- by CAP status: Actual 54; Exercise 4 (Exercise = training drills);
- by review status: pending 56; approved 2. The 2 approvals were made during deployment testing; **0 real assessments have been reviewed by an operator**.

No assessment has been queued since 2026-10-16. Rainfall eased, but two defects also suppressed assessments: the river/dam pathway has had no data since 22 September, and the forecast input read under half of the rain (section 9, F2, F3).

**Alerts sent.** 4 send attempts are recorded (telegram 2; whatsapp 2), of which 1 was delivered, during testing. **Alert subscribers: 0.**

**Citizen reports.** 4 reports (2026-09-21), all from deployment tests; 0 validated.

**Prediction ledger.** 1025 decision snapshots from 2026-09-19 to 2026-10-30. Risk tier: LOW 1024; MODERATE 1; fused tier: LOW 1013; MODERATE 10; HIGH 2. Recorded outcomes: flood_confirmed 940; None 82; no_evidence_found 3, by source ReliefWeb 923; None 82; ReliefWeb,GDELT 17; automated_check_no_signal 3. These outcomes are invalid (F1).

**Observation archive** (one row per signal per district per run):


| Signal | Rows | With a value | Share | Last value |
| --- | --- | --- | --- | --- |
| River/dam pathway score (DAHITI) | 1027 | 21 | 2% | 2026-09-21 |
| 3-day antecedent rain, Open-Meteo fallback | 925 | 925 | 100% | 2026-10-30 |
| Next-24 h forecast (Open-Meteo) | 1027 | 760 | 74% | 2026-10-30 |
| 3-day antecedent rain via API (CHIRPS, then IMERG) | 102 | 0 | 0% | never |


**Risk history:** 762 points, 2026-09-19 to 2026-10-30.

**Scheduled and automated jobs** (GitHub Actions, all runs on record):


| Job | Runs | Scheduled runs | Outcome | First | Last |
| --- | --- | --- | --- | --- | --- |
| 3-hourly risk assessment | 178 | 173 | success 178 | 2026-09-16 | 2026-10-30 |
| Outcome verification (daily) | 42 | 42 | success 41; failure 1 | 2026-09-19 | 2026-10-30 |
| CHIRPS ingestion (daily) | 161 | 157 | failure 112; success 48; cancelled 1 | 2026-05-27 | 2026-10-30 |
| Rule validation report (monthly) | 1 | 1 | success 1 | 2026-10-01 | 2026-10-01 |
| Weekly shadow forecast | 3 | 0 | success 1; cancelled 1; failure 1 | 2026-10-30 | 2026-10-31 |
| Resilience tests (daily and on pull requests) | 523 | 159 | failure 307; success 216 | 2026-05-24 | 2026-10-31 |
| Continuous integration (on push / pull request) | 358 | 0 | success 220; failure 137; in progress 1 | 2026-05-05 | 2026-10-31 |


The 3-hourly assessment should run 8 times a day; about 4 a day actually ran, because GitHub delays and drops scheduled runs at busy times. All CHIRPS-ingestion failures date from before 15 September 2026; every run since has succeeded. The most recent resilience-test failures are on automated dependency-update pull requests, not on the main branch.

## 9. Critical review: findings register

Severity: **Critical**, makes a reported result wrong; **High**, a live output is wrong or personal data is exposed; **Medium**, weakens validity or reliability; **Low**, hygiene. "Fix written and tested" means the change is in an open pull request with passing tests and is not yet deployed.


| ID | Area | Severity | Finding | Evidence | Status |
| --- | --- | --- | --- | --- | --- |
| F1 | Verification | Critical | The outcome verifier's ReliefWeb search used the default OR operator, so "Ghana flood <district>" matched any report containing any one word. 940 of 943 checked predictions were marked "flood confirmed" (923 by ReliefWeb alone), in all nine districts, 939 of them LOW-tier. | Production ledger; live query for Sunyani, 1–14 Oct 2026, returned Somali river-flood advisories and Ghanaian vaccine news | Fix written and tested (PR #69). After deployment, `scripts/verify_predictions.py --reverify-news` replaces the labels |
| F2 | Monitoring | High | The live rainfall forecast read Open-Meteo's `rain` (large-scale rain only) instead of `precipitation` (rain + convective showers), and counted hours from 00:00 GMT rather than from now. Over 67 days `rain` held 44% of the total at Accra, 36% at Kumasi, 35% at Tamale. | Open-Meteo API, 60 past + 7 forecast days at three districts | Fix written and tested (PR #68) |
| F3 | Monitoring | High | The DAHITI API key is rejected (HTTP 403 "Login failed") for every request, so the Tamale river level, Lake Volta level and Bagre proxy have returned nothing since 22 Sep 2026. The data-source health check still reports DAHITI "configured". | Production logs; observation archive (21 values, last 21 Sep); direct test of the stored key | Needs the account owner: a new key from dahiti.dgfi.tum.de, stored in Secret Manager (`dahiti-api-key`) |
| F4 | Security / privacy | High | `GET /v1/community-reports` was public and returned reporters' phone numbers, names and emails (personal data under Ghana's Data Protection Act, 2012, Act 843). | Unauthenticated production request returned a phone number | Fix written and tested (PR #70) |
| F5 | Dissemination | High | The dashboard opened every panel on a fixed 75 mm rainfall (score 100, EXTREME) whatever the weather, with no indication that the figures were a scenario. | `render_control_panel` default; headless render | Fix written and tested (PR #72) |
| F6 | Dissemination | High | The impact panel treated a real estimate of 0 people exposed (any dry day) as "API unavailable" and showed invented figures from `state_fallback.py` (from 10% of the population); `/situation` reported ≥1 power substation affected with nobody exposed. | `render_impact_panel`; `impact_estimator.estimate_impact` | Fix written and tested (PR #71) |
| F7 | Infrastructure / security | Medium | The Upstash Redis database no longer exists (hostname does not resolve), so rate limits and alert cooldowns are kept per worker in memory (4 workers). `REDIS_URL`, which contains the password, is a plain Cloud Run environment value rather than a Secret Manager reference. | `/health` (redis available: false); connection test | Needs the account owner: new Redis database; URL into Secret Manager |
| F8 | Dissemination | Medium | The review queue has no de-duplication or expiry: each run can queue three entries per district (one per signal), and entries stay pending indefinitely (56 pending, the oldest from 19 Sep). | `pending_alerts`; `alert_review.assess_district` | Open |
| F9 | Forecasting | Medium | River/dam WARNING (above the 75th percentile of a water body's own record, a normal wet-season level) scores 45, above the review threshold, so it queues a MODERATE alert. | `fluvial_pathway.ALTIMETRY_STATUS_RISK`; 11 queued river/dam alerts | Open: bands need calibration against flood dates |
| F10 | Forecasting | Medium | The urban drainage multiplier is applied only by `/situation`; other routes score the same rain without it, so Accra scores differ between the dashboard and the alert queue. The drainage values have no cited source. | Call sites of `calculate_score` | Open |
| F11 | Monitoring | Medium | Until 30 Oct 2026 the primary antecedent source (CHIRPS) was 18–30 days out of date, so all antecedent assessments used Open-Meteo's past-72-hour values, which are model output rather than observations. | Job logs; observation archive (0 values from the primary source) | Resolved by GPM IMERG (deployed 30 Oct); monitor |
| F12 | Infrastructure | Medium | GitHub Actions ran about half of the scheduled 3-hourly assessments, and 26% of the forecast fetches from the job failed (760 of 1,027 rows have a value). | Workflow history; observation archive | Open: move the schedule to Cloud Scheduler; add retries |
| F13 | Infrastructure | Medium | Cloud Run allocates CPU only during requests, so Litestream's background replication can stall between requests; writes made just before an instance is replaced can be lost. | Cloud Run service configuration | Owner decision: always-allocated CPU (small cost increase) |
| F18 | Forecasting | Medium | `/api/dam/spillage` returns a fixed result from default inputs, and its "validation" uses three spill events with unmeasured input values and no non-spill cases ("100% accuracy"). | `src/api/dam_router.py`, `src/models/dam_spillage.py` | Must not be cited; remove or label as illustrative |
| F19 | Risk knowledge | Medium | Exposure is a score-proportional heuristic (population × S/100 × 0.6); facility counts and vulnerable-group shares are project estimates; Accra populations are project estimates; the estimator's own tier cut-offs (20/40/60/80) differ from the platform's (30/50/70/85). | `src/exposure/impact_estimator.py` | Open: overlay a hazard map on WorldPop / census data |
| F21 | Forecasting | Medium | The live rule's review threshold (S ≥ 30, i.e. 10 mm in 24 h) is crossed by ordinary wet-season rain, and the rule has little skill at district-week scale (section 5.2) and almost none on real forecasts (section 5.4). | Research results M3 | Open: the shadow model M12 is the candidate replacement |
| F22 | Verification | Medium | Even with correct searches, the ledger is a weak verification sample: a prediction every 3 hours with overlapping 14-day windows, and evidence sources that rarely resolve a district. | `outcome_verifier.py` design | Open: verify weekly forecasts against NADMO records or Sentinel-1 |
| F14 | Security | Low | If `API_KEY` is unset, the key check accepts every request (fails open). Production sets it. | `src/api/auth.py` | Open: fail closed in production |
| F15 | Security | Low | Rate limits cover only `/situation` and the copilot; public operations that run the full evidence pipeline (decision, evidence, `/score/batch`) are unlimited. | OpenAPI inventory; `@limiter.limit` call sites | Open |
| F16 | Monitoring | Low | QARTOD flat-line and spike tests are implemented but not applied; IMERG, GloFAS and Sentinel-1 have no quality checks; the forecast is checked for one district only. | `/v1/data-quality` | Open |
| F17 | Monitoring | Low | The daily CHIRPS ingestion job saves an Accra-box file as a build artifact that nothing reads. | `scripts/daily_chirps_pull.py` | Open: remove or connect |
| F20 | Preparedness | Low | The copilot uses an unpinned model alias (`gemini-flash-lite-latest`), so its behaviour can change without a code change, and its answers have not been evaluated for accuracy or grounding. | `src/copilot/engine.py` | Open: pin a version; build a question set with expected answers |
| F23 | Documentation | Low | `/v1/health/data-sources` still says unavailable sources fall back to "simulated" readings; the code no longer simulates any value. | `src/api/v1/health.py` | Open |


**Strengths found by the review.** Every data adapter reports "unavailable" with a reason instead of inventing a value; no alert can be sent without a person approving it, and exercise alerts are separated from the sending code; alerts follow CAP 1.2; webhooks are signature-checked; secrets are in Secret Manager (except F7); the test suite (623 tests, coverage gate 80%) blocks merges; and the research framework is reproducible end to end from open data with time-separated validation.

## 10. Reporting-guideline map

### 10.1 WMO/UNDRR Multi-Hazard Early Warning Systems: the four pillars

| Pillar | What the system has | Main gaps |
| --- | --- | --- |
| 1. Disaster risk knowledge | District registry with census populations (9 districts); 8 documented historical floods; flood labels for 216 districts 2015–2025 (news-derived, radar-audited); built-up share, terrain and river-network features; named communities and candidate shelters | No flood-hazard or inundation map; exposure is a heuristic (F19); Accra sub-districts are not official units; no vulnerability data beyond planning shares |
| 2. Detection, monitoring, analysis and forecasting | Rainfall forecast, IMERG antecedent rain, GloFAS discharge, SMAP soil moisture, Sentinel-1 change detection, DAHITI water levels; rule-based score with multi-pathway fusion; research models with real-forecast hindcasts; weekly shadow forecast | No gauge, dam-operator or station data (section 6); DAHITI down (F3); forecast input defect (F2); rule has low skill (F21) |
| 3. Warning dissemination and communication | Human-approved alerts on WhatsApp and Telegram; CAP 1.2; tier-specific messages and response guidance; affected-community names; opt-in by chat; public kiosk view | No subscribers or institutional recipients yet; no SMS at scale; local-language messages not reviewed; queue not de-duplicated (F8) |
| 4. Preparedness and response capabilities | Exercise (drill) alerts; decision card with recommended action; copilot over platform data; candidate shelters (OpenStreetMap) | No standard operating procedures or agreed roles with NADMO; no drills held with responders; copilot not evaluated (F20) |

### 10.2 TRIPOD+AI (Collins et al. 2024) for the forecasting models

TRIPOD+AI was written for clinical prediction models; "participants" here are district-weeks and "outcome" is flood onset. Status: **Reported** (in this document), **Partly**, **Gap** (the manuscript must add it), **Team** (information only the authors can give).

| Item | Topic | Where / status |
| --- | --- | --- |
| 1 | Title: development and evaluation, population, outcome | Team (suggested: development and evaluation of weekly flood-onset prediction for Ghana's districts) |
| 2 | Abstract (TRIPOD+AI for Abstracts) | Team |
| 3a | Context and rationale; existing models | Partly: sections 1, 4.1 (GloFAS-style river benchmark M4); the manuscript needs a literature review of African flood early warning |
| 3b | Target population, intended use and users | Reported: section 1, 2.5, 5.10 (district emergency operators; shadow use) |
| 3c | Known inequalities between groups | Gap: urban/rural and north/south differences in label coverage (section 11, item 1) should be discussed as inequality |
| 4 | Objectives: development and/or validation | Reported: sections 3.1, 4.4 |
| 5a | Data sources for development and evaluation; representativeness | Reported: sections 3.2, 3.3, 5.1, 5.11 |
| 5b | Dates of data | Reported: sections 3.1, 5.1 |
| 6a | Setting; number and location of centres | Reported: 216 districts, 10 regions (sections 3.1, 5.1) |
| 6b | Eligibility criteria | Reported: all GAUL 2015 districts, all weeks (section 3.1) |
| 6c | Treatments (here: interventions such as dam releases) | Partly: dam operations not observed (section 6) |
| 7 | Data pre-processing and quality checking | Reported: sections 3.3, 3.4, 5.8, 5.11 |
| 8a | Outcome definition, time horizon, how assessed | Reported: sections 3.2, terms (onset, district-week) |
| 8b | Qualifications of outcome assessors | Partly: Groundsource events are extracted from news automatically (Mayo et al. 2026); state this |
| 8c | Blinding of outcome assessment | Gap: state that labels were assigned independently of predictors (news vs satellite) |
| 9a | Choice of predictors | Reported: sections 3.3, 3.4 |
| 9b | Definition and timing of all predictors | Reported: section 3.4; forecast-mode inputs, section 5.4 |
| 9c | Subjective predictor assessment | Not applicable (all predictors are instrumental) |
| 10 | Sample size justification | Gap: report the number of onsets per model parameter / events per fold (898 onsets, section 5.1) |
| 11 | Missing data | Partly: degradation experiment E6 (section 5.6); state missing-data handling per source |
| 12a | Data use and partitioning | Reported: section 4.2 (forward-chaining years; leave-region-out separated in time) |
| 12b | Predictor handling (transformations) | Reported: section 3.4 (local-climate percentiles, monotone constraints) |
| 12c | Model type, building steps, tuning, internal validation | Reported: sections 4.1, 4.2 |
| 12d | Heterogeneity across clusters | Reported: E4 regional transfer (section 5.6) |
| 12e | Performance measures and model comparison | Reported: section 4.3 |
| 12f | Model updating (recalibration) | Reported: Platt calibration of M12 (section 5.7, 5.10) |
| 12g | How predictions were calculated | Reported: code and model file (section 7) |
| 13 | Class imbalance methods | Partly: state that no resampling was used and metrics were chosen for rare events (PR-AUC, SEDI) |
| 14 | Fairness | Gap: report performance by region and urban/rural class |
| 15 | Model output and thresholds | Reported: probabilities; WATCH ≥ 5%, WARNING ≥ 20% (section 5.10) |
| 16 | Differences between development and evaluation data | Reported: v1 vs v2 labels (section 5.9); real vs perfect forecasts (5.4) |
| 17 | Ethical approval | Team: no human participants; public data only; state the waiver or that approval was not required |
| 18a–f | Funding; conflicts of interest; protocol; registration; data sharing; code sharing | Team for 18a–d; 18e–f reported (section 7) |
| 19 | Patient and public involvement (here: stakeholder involvement) | Team: NADMO or community engagement, or state none |
| 20a | Flow of units and events | Reported: section 5.1 |
| 20b | Characteristics of the data | Reported: section 5.1 |
| 20c | Evaluation vs development distributions | Partly: test-period base rate vs training (section 5.1); add predictor distributions |
| 21 | Numbers of units and events in each analysis | Reported: section 5.1, per-experiment tables |
| 22 | Full model specification | Reported: `model/model.json`, model card (section 7) |
| 23a | Performance with confidence intervals | Reported: bootstrap 90% intervals (sections 5.2–5.9) |
| 23b | Heterogeneity in performance across clusters | Reported: E4 (section 5.6) |
| 24 | Results of model updating | Reported: calibration before and after Platt scaling (section 5.7) |
| 25 | Interpretation, including fairness | Team, drawing on sections 1, 5.3, 11 |
| 26 | Limitations | Reported: section 11 |
| 27a | Handling poor or unavailable inputs in use | Reported: E6 degradation; platform "unavailable" behaviour (sections 5.6, 2.11) |
| 27b | User interaction and expertise needed | Reported: human review of every alert (sections 2.5, 2.10) |
| 27c | Next steps | Team, drawing on sections 6 and 9 |

## 11. Limitations to state in the manuscript

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
8. **Expert-set parts of the live platform.** The live platform's fusion weights, the drainage factors, the river/dam percentile bands and the dam formula are expert-set, not validated.
9. **Rainfall at the scale of a town.** Satellite rainfall agrees with station gauges week by week but poorly day by day, and detects under a third of heavy-rain gauge days (section 5.11).
10. **No operational record.** The platform has not yet been used by operators or the public (section 8); no claim about warning delivery, response or impact can be made.
11. **Verification of live predictions.** The live prediction log has no valid outcomes (section 9, F1); live skill can only be claimed from the research hindcasts.

## 12. Results that must not be cited

- **R² = 0.993 for the early Accra XGBoost regressor** (notebook `04_flood_risk_model.ipynb`). Its target was a formula built from its own inputs, so the figure is circular; that model is not part of the system.
- **"100% accuracy" of the dam spillage formula.** It rests on 3 spill events and no non-spill cases.
- **Outcome labels in the live prediction log** (any hit rate or calibration figure computed from them). The ReliefWeb search matched unrelated reports and marked 940 of 943 checked predictions "flood confirmed" (section 9, F1).
- **Dam spillage "validation"** (`/api/dam/spillage/validate`): three spill events with input values that were not measured, and no non-spill cases.
- **Exposure counts** (people, schools, hospitals exposed) as modelled exposure: they are a fixed share of population scaled by the risk score (section 2.10).
- **Any statement that alerts have reached the public** or that the system has been used in a flood response (section 8).
- **Any skill figure for the NFCC rule (M3) other than those in sections 5.2, 5.4 and 5.9.**

## 13. References

- Alfieri, L. et al. (2013). GloFAS – global ensemble streamflow forecasting and flood early warning. *Hydrology and Earth System Sciences* 17, 1161–1175. doi:10.5194/hess-17-1161-2013
- Breiman, L. (2001). Random forests. *Machine Learning* 45, 5–32. doi:10.1023/A:1010933404324
- Brier, G. W. (1950). Verification of forecasts expressed in terms of probability. *Monthly Weather Review* 78, 1–3.
- Chen, T. & Guestrin, C. (2016). XGBoost: a scalable tree boosting system. *Proc. KDD '16*, 785–794. doi:10.1145/2939672.2939785
- Cox, D. R. (1958). The regression analysis of binary sequences. *Journal of the Royal Statistical Society B* 20, 215–242.
- Collins, G. S. et al. (2024). TRIPOD+AI statement: updated guidance for reporting clinical prediction models that use regression or machine learning methods. *BMJ* 385, e078378. doi:10.1136/bmj-2023-078378
- Efron, B. & Tibshirani, R. J. (1993). *An Introduction to the Bootstrap*. Chapman & Hall.
- FAO (2015). Global Administrative Unit Layers (GAUL) 2015. Food and Agriculture Organization of the United Nations.
- Funk, C. et al. (2015). The climate hazards infrared precipitation with stations – a new environmental record for monitoring extremes. *Scientific Data* 2, 150066. doi:10.1038/sdata.2015.66
- Gebru, T. et al. (2021). Datasheets for datasets. *Communications of the ACM* 64(12), 86–92. doi:10.1145/3458723
- Farr, T. G. et al. (2007). The Shuttle Radar Topography Mission. *Reviews of Geophysics* 45, RG2004. doi:10.1029/2005RG000183
- Ferro, C. A. T. & Stephenson, D. B. (2011). Extremal dependence indices: improved verification measures for deterministic forecasts of rare binary events. *Weather and Forecasting* 26, 699–713. doi:10.1175/WAF-D-10-05030.1
- Funk, C. et al. (2015). The climate hazards infrared precipitation with stations – a new environmental record for monitoring extremes. *Scientific Data* 2, 150066. doi:10.1038/sdata.2015.66
- Hanley, J. A. & McNeil, B. J. (1982). The meaning and use of the area under a receiver operating characteristic (ROC) curve. *Radiology* 143, 29–36.
- Harrigan, S. et al. (2020). GloFAS-ERA5 operational global river discharge reanalysis 1979–present. *Earth System Science Data* 12, 2043–2060. doi:10.5194/essd-12-2043-2020
- Huffman, G. J. et al. (2023). GPM IMERG Final Precipitation L3 Half Hourly 0.1 degree x 0.1 degree V07. NASA GES DISC. doi:10.5067/GPM/IMERG/3B-HH/07
- Lundberg, S. M. & Lee, S.-I. (2017). A unified approach to interpreting model predictions. *Advances in Neural Information Processing Systems* 30, 4765–4774.
- Lundberg, S. M. et al. (2020). From local explanations to global understanding with explainable AI for trees. *Nature Machine Intelligence* 2, 56–67. doi:10.1038/s42256-019-0138-9
- Lott, J. N. (1998). The quality control of the integrated surface hourly database. NOAA National Climatic Data Center. (GSOD is derived from this database; data: NOAA NCEI Global Surface Summary of the Day, https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.ncdc:C00516)
- Mayo, R. et al. (2026). Groundsource: a dataset of flood events from news. EarthArXiv preprint. Data: doi:10.5281/zenodo.18647054
- Mitchell, M. et al. (2019). Model cards for model reporting. *Proc. FAT* '19*, 220–229. doi:10.1145/3287560.3287596
- Muñoz-Sabater, J. et al. (2021). ERA5-Land: a state-of-the-art global reanalysis dataset for land applications. *Earth System Science Data* 13, 4349–4383. doi:10.5194/essd-13-4349-2021
- Murphy, A. H. (1977). The value of climatological, categorical and probabilistic forecasts in the cost-loss ratio situation. *Monthly Weather Review* 105, 803–816.
- Naeini, M. P., Cooper, G. & Hauskrecht, M. (2015). Obtaining well calibrated probabilities using Bayesian binning. *Proc. AAAI '15*, 2901–2907.
- OASIS (2010). Common Alerting Protocol Version 1.2. OASIS Standard.
- U.S. IOOS (2020). Manual for real-time quality control of in-situ surface wave data and related QARTOD manuals. U.S. Integrated Ocean Observing System, NOAA.
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
- WMO (2018). Multi-hazard early warning systems: a checklist. Outcome of the first Multi-hazard Early Warning Conference, Cancún, Mexico, 22–23 May 2017. World Meteorological Organization.
- WMO (2022). Early Warnings for All: the UN Global Early Warning Initiative for the Implementation of Climate Adaptation. Executive Action Plan 2023–2027. World Meteorological Organization.
- Wilks, D. S. (2011). *Statistical Methods in the Atmospheric Sciences*, 3rd ed. Academic Press.
- Yamazaki, D. et al. (2019). MERIT Hydro: a high-resolution global hydrography map based on latest topography dataset. *Water Resources Research* 55, 5053–5073. doi:10.1029/2019WR024873
- Zadrozny, B. & Elkan, C. (2002). Transforming classifier scores into accurate multiclass probability estimates. *Proc. KDD '02*, 694–699. doi:10.1145/775047.775151
- Zippenfenig, P. (2023). Open-Meteo.com Weather API. Zenodo. doi:10.5281/zenodo.7970649
