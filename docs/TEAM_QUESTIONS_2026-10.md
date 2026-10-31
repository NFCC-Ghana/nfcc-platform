# NFCC: answers to the team's five questions

*Updated 31 October 2026. For the NFCC team and the PhD supervisory
committee. The first answers (29 October) described the code as it was
then. Each section below gives that answer, then what has changed since:
new experiments on 216 districts, more models and two production fixes.*

| # | Question | Short answer (31 Oct 2026) |
| --- | --- | --- |
| 1 | Did we use only XGBoost, or other models? | Until 29 October, XGBoost was the only trained model, and it was invalid (circular target, removed in September). The live alert system is rule-based. Since then the research framework has compared 11 models and 4 ways of combining data sources on real flood records. The best calibrated model is now in weekly test use, not yet for alerts. |
| 2 | Is the dashboard connected to all data sources? | Partly. Eight sources are real. River gauges and VRA dam telemetry are simulated or absent, Flood Hub awaits access, and TAHMO and GMet are absent. "Phase 2" items (nowcasting, 3D terrain, insurance API, SMS at scale) are planned, not built. |
| 3 | Accra only, or many districts? | The live platform tracks 9 districts. The research experiments now cover all 216 districts (2015 boundaries) in all 10 regions: 2000–2018 and 2015–2025. Before 29 October they covered only Accra and Tamale. |
| 4 | Were TAHMO, GMet and river-gauge data available for training? | No. None was ever obtained or used. Open satellite and reanalysis data replaced them, and that limits what we can claim. |
| 5 | What models, datasets and results are accessible to us? | All of it is in the public repository and reproducible with open data: the 2015–2025 and 2000–2018 district-week datasets (rebuildable), 11 compared models, every experiment's results, a calibrated operational model with a model card, and weekly forecast logs. |

## 1. Did we use only XGBoost, or other models?

### Before 29 October: one model, and it was invalid

XGBoost was the only learned model ever trained.

- **What it was:** `notebooks/04_flood_risk_model.ipynb` trained an XGBoost regressor on 365 days of CHIRPS rainfall at one Accra point (2024).
- **Why it was invalid:** its target, `flood_risk_score`, was a formula built from the model's own inputs. Its R² of 0.993 only measured how well it copied that formula.
- **What happened to it:** it was removed on 21 September 2026 (commit `9020e16`).

The live alert system has always been rule-based:

- a rainfall curve (`calculate_score`);
- hand-weighted fusion of rainfall, river, dam, satellite and citizen evidence;
- a fixed dam-spillage formula.

### Since then: a full model comparison on real flood records

The research framework (`research/flood_experiments/`, PRs #57 and #59) trained and tested these models. Each is trained only on earlier years and tested on later ones. The results below are for 2015–2025: 216 districts, test years 2018–2025, 898 flood onsets.

| Model | Type | PR-AUC (× chance) | SEDI |
| --- | --- | --- | --- |
| Climatology (each district's usual flood rate by month) | Baseline | 0.048 (6.5×) | 0.40 |
| Persistence (flooded recently) | Baseline | 0.018 (2.4×) | 0.42 |
| Live rainfall rule (production) | Rule | 0.030 (4.1×) | 0.28 |
| River percentile (GloFAS-style) | Hydrological benchmark | 0.025 (3.4×) | 0.32 |
| Logistic regression (rainfall) | Statistical | 0.043 (5.8×) | 0.29 |
| Random forest (rainfall) | Machine learning | 0.028 (3.8×) | 0.28 |
| XGBoost (rainfall) | Machine learning | 0.025 (3.4×) | 0.34 |
| Temporal XGBoost (rain history + soil) | Machine learning | 0.022 (3.0×) | 0.27 |
| Multi-source XGBoost | Machine learning | 0.072 (9.7×) | 0.45 |
| Timing-only XGBoost (no place features) | Machine learning | 0.034 (4.6×) | 0.40 |
| **Final: multi-source + local climate XGBoost** | Machine learning | **0.081 (10.9×)** | **0.49** |

Fusion strategies were compared too: one model on all inputs, the mean of per-source models, stacking, and the platform's hand-set weights. One model on all inputs did best.

**The model in use today** is the calibrated operational model (`research/flood_experiments/model/`, with `MODEL_CARD.md`). It is the XGBoost variant that uses only information available when the week starts, because that version scored best with real forecasts (see question 5). It runs every Monday in **shadow mode**: it scores all 216 districts and never sends alerts. The first successful run, on 31 October, scored the week of 2 November in under 4 minutes; no district reached WATCH, with the highest risk about 2% in the Lower Volta and Accra. **Live alerts still use the rule-based system.**

**Planned models from the Project Overview:**

| Planned model | Status |
| --- | --- |
| Model 1: flood probability | Built and evaluated, at district-week level (not a 100 m grid) |
| Model 2: rainfall nowcasting (0–6 h) | Not built |
| Model 3: dam spillage | Still a fixed formula. There are no dam release records to fit a model |
| Model 4: urban inundation | Not built. Rewritten as a phased plan, starting with a susceptibility map (issue #27) |
| Hydrological routing (HBV/GR4J + LSTM) | Not built |

## 2. Is the dashboard connected to all data sources?

Partly. The dashboard (`hackathon/app/pages/dashboard.py`) reads everything through the production API and never calls data providers directly, so a source counts as connected only if the API uses it.

| Source | Status in production (31 Oct 2026) |
| --- | --- |
| Recent rainfall (last 3 days) | **Changed 30 Oct (PR #60, deployed):** now GPM IMERG, 2–4 days behind real time, rescaled to CHIRPS. Before, it read CHIRPS, which was a month out of date. |
| Open-Meteo rainfall forecast | Real. **Changed 30 Oct (PR #58, deployed):** an outage now shows "unavailable". Before, it showed invented rainfall that could raise risk scores. |
| Open-Meteo GloFAS river discharge | Real. Its "elevated" threshold (1.5×) is illustrative, not calibrated. |
| NASA SMAP soil moisture | Real |
| Sentinel-1 radar flood detection | Real when Earth Engine responds. Otherwise it shows **randomly generated** values labelled "Sentinel-1 (simulated)". These are excluded from risk decisions (the decision card counts only real "Sentinel-1 SAR" detections) but are still displayed. Recommended fix: show "unavailable", as was done for the forecast. |
| DAHITI satellite altimetry | Real but narrow: Lake Volta and one White Volta station |
| ReliefWeb, GDELT | Real, but country-level only |
| Community reports | Real |
| Urban drainage | Static table with no cited source; Accra only |
| Google Flood Hub | Client written; waiting on API access |
| Ghana river gauges (HSD) | Not connected; simulated readings |
| VRA dam telemetry | Not connected; simulated data |
| TAHMO, GMet | Not connected; not in the code |

**What "Phase 2" means.** The term appears in two planning documents, and neither Phase 2 is built yet.

- **Project Overview:** Phase 2 is months 10–12, the "Operational System". None of its items exist in the code today. It includes:
  - a rainfall nowcasting model (0–6 h), using telecom microwave links if a telecom partnership is secured;
  - an urban inundation surrogate calibrated on drone elevation models;
  - an insurance trigger API;
  - dashboard v2 with a nowcasting layer, 3D terrain and mobile support;
  - SMS and voice alerts to 5,000+ subscribers through Africa's Talking.
- **"Current NFCC platform state":** Phase 2 is "ML/data improvements": real-time weather feeds, better rainfall forecasting, river-level prediction and faster satellite ingestion. Of these:
  - **Done:** real-time recent rainfall (IMERG), and a model tested on real forecasts.
  - **Not done:** river-level prediction needs gauge data.

**Sources the research uses but the dashboard doesn't (yet):** ERA5-Land soil moisture and runoff, GloFAS reanalysis at each district's main river, MERIT Hydro, Groundsource flood records, Sentinel-1 (label audit), archived ECMWF forecasts and the live 51-member ensemble, WorldPop, GHSL, SRTM and JRC surface water. The weekly shadow forecast uses several of these, but its results are not shown on the dashboard yet.

## 3. Do the experiments cover Accra alone or multiple districts?

**Before 29 October:**
- The XGBoost notebook used one Accra point.
- The skill evaluation covered Accra (3 neighbouring districts) and Tamale.

**Now:** the experiments cover **all 216 districts** (FAO GAUL 2015 boundaries) **in all 10 regions**.

| Study | Districts | Period | Flood onsets | Labels |
| --- | --- | --- | --- | --- |
| Main study (v2) | 216, all regions | 2015–2025 (123,768 district-weeks) | 898 in 167 districts | News-reported floods (Groundsource), audited with satellite radar |
| Sensitivity study (v1) | 216, all regions | 2000–2018 (211,464 district-weeks) | 203 in 68 districts | Satellite flood maps (Global Flood Database, MODIS) |
| Weekly shadow forecast | 216 | Each week from 2 Nov 2026 | – | – |
| Live platform | 9 tracked districts | Live | – | – |

**Flood onsets by region (2015–2025):**

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

The experiments also test **transfer to unseen regions** (leave-one-region-out): the model still works on a region it never trained on (PR-AUC 0.053).

Three caveats for the manuscript:

1. **Urban flood records can't be independently verified yet.** Satellite radar confirms rural news-reported floods: it sees new water at 32.5% of them, against 16–17% of matched weeks with no report. It cannot see urban floods, so Greater Accra's 251 onsets rest on news reports alone until NADMO records arrive.
2. **The boundaries are the 2015 ones (216 districts).** Ghana has had 261 districts since 2018.
3. **The model works at weekly district scale.** It does not predict street-level flooding or within-day timing.

**Recommended wording:** "a national, district-level flood-onset evaluation for Ghana (216 districts, 2015–2025), using news-derived flood records audited with satellite radar, with Greater Accra and the northern river basins as the most flood-active areas."

## 4. Were TAHMO, GMet and river-gauge data available for training?

**No.** None was ever obtained, and no model or experiment used them. The Project Overview's fallback, "use CHIRPS / satellite only", is what the project ran on.

| Dataset | Status | Open substitute used |
| --- | --- | --- |
| TAHMO station rainfall | Never obtained | CHIRPS (training); GPM IMERG (live); ECMWF forecasts |
| GMet records | Never obtained | Same as above |
| HSD river gauges | Never connected; the client was deleted in Sept 2026 | GloFAS v4 discharge at each district's main river; DAHITI altimetry |
| VRA / SONABEL dam releases | Never obtained | None. The "+ Dam" experiment is reported as not runnable |
| NADMO incident records | Not yet requested; the request letter is ready (`research/flood_experiments/nadmo_data_request.md`) | Groundsource news-reported floods |

**Why this matters:**
- **Station rainfall** would test satellite rain bias over Accra's short, intense storms.
- **River gauges** would let us calibrate GloFAS locally.
- **Dam release records** would make the dam pathway real. Bagre spillage drives northern floods.
- **NADMO records** would verify the urban flood records and enable impact-based warnings.

These four partnerships are the main path from "credible" to "leading".

## 5. Which models, datasets and results are accessible to us?

Everything below is in the public repository (`NFCC-Ghana/nfcc-platform`) or rebuildable from open data with one command per step.

**Models**

| Item | Where | Use in the manuscript |
| --- | --- | --- |
| Operational flood-onset model (calibrated XGBoost) | `research/flood_experiments/model/` (`model.json`, `meta.json`, `MODEL_CARD.md`) | Yes: the deployable model, in shadow test |
| All 11 compared models and the fusion strategies | `research/flood_experiments/models.py` (retrained on demand) | Yes: the model comparison |
| Live rule-based score and fusion | `src/alerts/formatter.py`, `src/models/multi_source_confidence.py` | Yes, as the operational baseline |
| Original Accra XGBoost | Git history (commit `9020e16^`) | Only as a documented negative result |
| Dam spillage formula | `src/models/dam_spillage.py` | No: its validation is circular |

**Datasets**

| Dataset | Coverage | How to get it |
| --- | --- | --- |
| Main district-week panel | 216 districts, 2015–2025; rainfall (mean and wettest pixel), soil moisture, runoff, discharge, terrain, population, flood labels | `python -m research.flood_experiments.build_dataset` (git-ignored; rebuilt from Earth Engine and Open-Meteo) |
| Sensitivity panel | 216 districts, 2000–2018 | same, with `NFCC_STUDY=v1_gfd` |
| Groundsource flood events | 2,686 in Ghana; 2,527 placed in a district | Earth Engine `projects/sat-io/open-datasets/groundsource_2026` |
| Sentinel-1 label audit | 2,694 district-weeks (898 onsets + 2 matched controls each) | `python -m research.flood_experiments.sar_labels` |
| Archived ECMWF forecasts | 216 districts, 2024–2025, issued before each week | `python -m research.flood_experiments.forecast_archive` |
| Documented flood events | 8 events, 2007–2023 | `src/hydrology/flood_polygons.py` |
| Production database | Observations, risk history, prediction log | Cloud Run, backed up to GCS (restore verified) |
| Weekly shadow forecasts | 216 districts per week, from 2 Nov 2026 | Branch `shadow-log` |

**Results we can cite**

- **Full results:** `research/flood_experiments/results/v2/summary.md` (2015–2025) and `results/v1_gfd/summary.md` (2000–2018), each with tables and figures.
- **Best model with observed rain:** PR-AUC 0.081, about 11× chance; SEDI 0.49 (90% CI 0.44–0.53).
- **Real lead time (2024–2025, archived ECMWF forecasts):**
  - The live rule applied to real forecasts has almost no skill (SEDI 0.07).
  - The model with no rain forecast scores best (PR-AUC 0.089). Adding the forecast directly lowers skill (0.050).
- **Operational model:** calibrated (calibration error 0.001). WATCH level: about 217 alerts a year nationwide, catching 21% of flood onsets within a week.
- **Label audit:** rural news-reported floods are confirmed by radar (32.5% vs 16–17%); urban ones can't be verified.
- **2000–2018 satellite-labelled floods (mostly rivers):** only the river benchmark has clear skill (SEDI 0.67).

**Results we must not cite**

- **The original XGBoost R² of 0.993:** circular.
- **The early "SEDI 0.44" for the live rule:** a threshold artefact. The corrected values are 0.15 (2000–2018) and 0.28 (2015–2025).
- **The production prediction log's outcome labels:** the ReliefWeb search marks most predictions "confirmed".
- **The dam model's "100% accuracy":** 3 spill events, no non-spill cases.

**The headline for the manuscript:**
- NFCC is a credible, honestly evaluated district-level flood-onset system for Ghana.
- It is not yet a validated early-warning system for urban floods or dam releases.
- The missing pieces are partner data, not code.
