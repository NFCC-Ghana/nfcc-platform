# NFCC flood early-warning system: critical review and upgrade

*30 October 2026 (status updated 31 October). For the NFCC team and the PhD supervisory committee.*

## Bottom line

NFCC is not yet the best flood early-warning system in Ghana, Africa or
the world. It has the ingredients to become a credible one. What it
lacks is the evidence that the world's leading systems publish for
themselves: skill measured against real outcomes, at real lead times,
with honest uncertainty.

This review closes most of that gap with open data:

- **Better flood records:** 898 flood onsets in 167 districts (2015–2025),
  against 203 in 68 districts before.
- **Independent check of the records:** satellite radar confirms the
  rural ones.
- **New evaluation:** "when vs where" skill and economic value to users.
- **A true lead-time test:** archived ECMWF forecasts.
- **A calibrated operational model:** chosen by its real-forecast
  skill, with a model card and a live shadow mode that reports the
  51-member ECMWF ensemble alongside it.
- **Production fixes:** the live system no longer invents rainfall when
  its weather feed fails (PR #58).

What remains needs partners, not code:

- NADMO incident records, to verify urban floods.
- GMet / TAHMO station rainfall.
- HSD river gauges.
- Dam release schedules from VRA (Akosombo, Kpong) and SONABEL (Bagre,
  Burkina Faso).

## How the leading systems work, and where NFCC stood

| Practice | Who does it | NFCC before | NFCC now |
| --- | --- | --- | --- |
| Skill published against observed events | GloFAS/EFAS, Google Flood Hub, US NWS | One SEDI backtest (Accra, Tamale) | Full verification for 216 districts, 2015–2025; ROC/PR-AUC, SEDI, POD/FAR, calibration, economic value |
| Thresholds relative to local climate (return periods) | GloFAS (2/5/20-yr), Flash Flood Guidance System, JMA soil-water index | One national rain curve: 30 mm/day means the same everywhere | Rain also as a percentile of each district's own 2000–2014 climate |
| Probabilistic, ensemble-based forecasts | ECMWF ENS, GloFAS, EFAS | One deterministic Open-Meteo forecast, scored as if certain | Calibrated probability from the model; the 51-member ECMWF ensemble's median and 90th percentile reported next to it. Fusing the two needs a MOS layer trained on more archived forecasts (E3c) |
| Honest lead-time evaluation | ECMWF, GloFAS reforecasts | None; only same-day rain | E3c tests on archived ECMWF forecasts issued before each week |
| Calibrated probabilities and decision thresholds | ECMWF, Red Cross forecast-based financing triggers | Hand-set 0–100 scores combined with noisy-OR | Platt-calibrated probability; WATCH and WARNING set by the cost-loss rule (act when P > cost/loss) |
| Separate hazard pathways | US NWS (dam vs rain), EFAS (riverine vs flash) | Pathways exist, but weights are guesses | Evidence that the pathways differ: river signal for river floods (2000–2018), rain for flash floods (2015–2025) |
| Impact-based warnings | WMO guidelines; UK, Philippines | Exposure layer, never validated | E8 ready; needs NADMO people-affected records |
| Shadow running before go-live | Every major agency | None | `operational.py shadow` scores every district weekly and never alerts |

## Critique: data

| # | Problem | Why it matters | What changed | Status |
| --- | --- | --- | --- | --- |
| D1 | Flood records came from MODIS only (Global Flood Database): 203 onsets in 19 years, none in 2012–2014 or 2016–2017 | MODIS misses most urban and flash floods; too few events to train or test | Main study switched to Groundsource news-reported floods (Google, 2026): 2,527 placed events | Done |
| D2 | News records follow media coverage | A model can learn where floods get reported instead of where they happen | Radar audit of every reported onset against matched no-flood weeks | Done. Rural confirmed (32.5% vs 16–17%); urban unverifiable by radar (9.4% vs 9–10%) |
| D3 | No ground-truth flood or impact records | Nobody can verify urban floods or train impact warnings | NADMO request letter and loader (`nadmo_data_request.md`, `nadmo.py`) | Letter not yet sent |
| D4 | Antecedent rain in production reads CHIRPS, which ends on 30 September in Earth Engine | The live "last 3 days" rain signal is a month old | Shadow run uses GPM IMERG (2 days behind), rescaled per district to CHIRPS | Done: production switched to IMERG in PR #60 (deployed 30 Oct, revision 00079) |
| D5 | District-mean rain dilutes storms | Flash floods come from convective cells | Wettest-pixel (95th percentile) rain per district | Done |
| D6 | Discharge read at district centroids | Often nowhere near the flooding river | Read at each district's main river (largest MERIT Hydro upstream area) | Done |
| D7 | Station rain, river gauges and dam releases never obtained | The strongest predictors of river and dam floods are missing; Bagre spillage drives Upper East and Northern floods | Not solvable with open data | Needs GMet, TAHMO, HSD, VRA and SONABEL |
| D8 | GAUL 2015 boundaries (216 districts) | Ghana has had 261 districts since 2018 | NADMO loader flags unmatched new districts for manual mapping | Open |

## Critique: models and evaluation

| # | Problem | Why it matters | What changed |
| --- | --- | --- | --- |
| M1 | The live risk score is one national rainfall curve | 40 mm is ordinary in Axim and extreme in Bolgatanga | Local-climate percentiles; the final model uses both |
| M2 | Hand-set fusion weights and noisy-OR of uncalibrated 0–100 scores | Noisy-OR assumes calibrated, independent probabilities; scores are neither, so risk inflates and false alarms follow. In E5 the hand-set weights score PR-AUC 0.032 | Calibrated probability from one learned model |
| M3 | Only perfect-forecast (observed-rain) evaluation | Overstates early-warning skill | E3b (antecedent only) and E3c (real archived ECMWF forecasts) |
| M4 | Skill pooled across districts | Hides whether a model knows *when*, or only *where* | Within-district AUC, and urban vs rural skill |
| M5 | F1-tuned thresholds | F1 ignores what an action costs users | Relative economic value (Richardson 2000); levels from the cost-loss rule |
| M6 | Unconstrained trees on a few hundred events | Can learn "more rain lowers risk" | Monotone, shallow, regularised XGBoost |
| M7 | Leave-region-out split leaked shared flood dates | Inflated spatial skill 300-fold (PR-AUC 0.31 vs 0.001) | Split separated in time |

## Critique: the live platform

| # | Problem | Status |
| --- | --- | --- |
| P1 | When Open-Meteo failed, the platform **invented rainfall** (15 mm plus a random draw in rainy months). It reached users, the risk timeline and the AI Copilot's risk tools | Fixed in PR #58 (deployed 30 Oct, revision 00079): an outage now returns "unavailable" with every value null |
| P2 | Antecedent rain is a month stale (D4) | Fixed in PR #60 (deployed 30 Oct, revision 00079): rain now 3 days old instead of about 30 |
| P3 | Single deterministic forecast, no uncertainty | Weekly ensemble shadow run scheduled (PR #61; network-retry fix in PR #63). Production adoption after a shadow season |
| P4 | Verification ledger outcomes come from ReliefWeb keyword search; 881 of 982 marked "confirmed" | Replace with Groundsource and the radar audit, and NADMO when available |
| P5 | Live system tracks 9 districts; the research covers 216 | The shadow run covers all 216 |
| P6 | **Security:** the production API key matches one in a public commit | Done 30 Oct: key rotated, leaked version disabled, GitHub leak alert closed. Next: activate the separate alert-approval key |

## Results (2015–2025, 216 districts, test years 2018–2025)

There are 898 onsets, a base rate of 0.0074 per district-week. Models are
trained only on earlier years. CIs are 90% year-block bootstrap.

| Model | PR-AUC (× chance) | SEDI | Within-district AUC (timing) | Rural PR-AUC (radar-confirmed labels) | Peak economic value |
| --- | --- | --- | --- | --- | --- |
| Climatology | 0.048 (6.5×) | 0.40 | 0.72 | 0.011 | 0.36 |
| Live rainfall rule | 0.030 (4.1×) | 0.28 | **0.80** | 0.019 | 0.41 |
| River percentile (GloFAS-style) | 0.025 (3.4×) | 0.32 | 0.77 | 0.019 | 0.40 |
| Logistic regression (rain) | 0.043 (5.8×) | 0.29 | **0.80** | **0.039** | 0.39 |
| Multi-source XGBoost | 0.072 (9.7×) | 0.45 | 0.78 | 0.019 | 0.55 |
| Timing-only XGBoost (no place features) | 0.034 (4.6×) | 0.40 | 0.76 | 0.025 | 0.44 |
| **Final: multi-source + local climate** | **0.081 (10.9×)** [0.063–0.099] | **0.49** [0.44–0.53] | 0.78 | 0.027 | **0.56** |

What the table shows:

1. **The final model is the best overall forecaster.** It has the highest
   PR-AUC, SEDI and economic value. It is useful to users whose action
   costs between 0.2% and 50% of the loss it prevents. The live rule is
   useful only up to 11%.
2. **For timing alone, the simple rainfall rule is as good as anything**
   (within-district AUC 0.80). Machine learning adds calibrated
   probabilities, place awareness and economic value, not better timing.
3. **Much of the final model's edge is in cities**: urban PR-AUC 0.116
   against a base rate of 0.021. Radar cannot verify urban labels, so
   until NADMO data arrives part of this edge may be media coverage.
4. **In rural districts, where radar confirms the labels, plain logistic
   regression on rain does best** (PR-AUC 0.039, 8.7× chance).
5. **Dynamic inputs matter; static ones dominate.** Removing rainfall
   costs a third of the skill; a week-old rainfall feed costs half.
   Removing place features costs 70%.
6. **Spatial transfer works.** On a region it never saw, the
   multi-source model keeps PR-AUC 0.053. Climatology fails completely.
7. **Explanations are trustworthy.** Deleting the top SHAP feature moves
   predictions six times more than deleting a random one. Rankings are
   stable (ρ 0.81).
8. **Calibrate.** Platt scaling cuts calibration error from 0.0030 to
   0.0006.

In 2000–2018, with satellite labels dominated by river floods, the
river-percentile benchmark was the only model with clear skill
(SEDI 0.67). River floods and flash floods need different signals.

### Real lead time (E3c)

This is the most important result in this review.

**Setup:**
- **Test weeks:** 2024–2025, 164 onsets. The forecast archive starts
  in 2024, so that is all the years available.
- **Forecast:** ECMWF IFS 0.25° rainfall issued *before* each week
  (Open-Meteo Previous Runs archive), rescaled per district.
- **Caution:** the intervals come from only two years, so treat them
  as indicative.

| How rain enters the model | PR-AUC | SEDI | Peak economic value |
| --- | --- | --- | --- |
| Perfect forecast (observed rain), upper bound | 0.084 | 0.48 | 0.55 |
| Real ECMWF forecast, model trained on observed rain ("perfect prog") | 0.050 | 0.41 | 0.54 |
| MOS blend: antecedent model + forecast, cross-fitted on the other year | 0.075 | 0.45 | 0.57 |
| **No rain forecast: only what is known when the week starts** | **0.089** | **0.51** | **0.59** |
| Climatology | 0.060 | 0.46 | 0.47 |
| **Live rule on the real forecast (what production does)** | **0.013** | **0.07** | 0.33 |

What this means:

1. **Production's core alert logic has almost no skill with real
   forecasts.** The live rainfall curve applied to a real forecast scores
   SEDI 0.07, with an interval that includes zero. Its apparent skill
   elsewhere comes from using rain that has *already fallen*.
2. **The forecast is not useless.** On its own it ranks onset weeks
   nearly as well as observed rain (ROC-AUC 0.70 vs 0.75). In onset
   weeks it predicts 39 mm against 26 mm in other weeks. But a model
   trained on observed extremes misreads smoother, noisier forecasts.
3. **The best real-world model today uses no rain forecast.** It uses
   antecedent rain, soil, river and place. It is the deployed
   operational model. The ECMWF ensemble is shown next to it as context
   until 2027+, when there will be enough archived forecasts to train a
   MOS layer that beats it.

### Operational model and first shadow run

The deployed model (`research/flood_experiments/model/`, with
`MODEL_CARD.md`):

- **Inputs:** the antecedent-only model, 17 inputs known when the week
  starts.
- **Training:** XGBoost, monotone in every rain, soil and river input.
- **Calibration:** Platt scaling on out-of-fold forecasts for 2018–2025.

**Out-of-fold performance (2018–2025, 750 onsets):**

| Measure | Value |
| --- | --- |
| ROC-AUC | 0.81 |
| PR-AUC | 0.051 (6× chance) |
| Within-district AUC | 0.73 |
| Calibration error (ECE) | 0.001 |

The probabilities are well calibrated: when it says 4%, floods start
about 4% of the time.

**Warning levels** follow the cost-loss rule (act when P > cost/loss):

| Level | Rule | Alerts / year (whole country) | POD ±1 wk | FAR ±1 wk |
| --- | --- | --- | --- | --- |
| WATCH | P ≥ 5% | 217 (about 1 per district) | 0.21 | 0.84 |
| WARNING | P ≥ 20% | 9 | 0.02 | 0.68 |

These numbers are the honest limit of week-ahead district flood-onset
prediction with open data. WATCH is useful for cheap preparedness, such
as alerting officers and clearing drains. WARNING is too rare to rely on
yet.

**First live shadow run (week of 2 November 2026):**

- **Coverage:** all 216 districts scored from live data:
  - GPM IMERG rain for the past four weeks; last week was 2 of 7 days
    observed, a limitation recorded in the output;
  - ERA5-Land;
  - GloFAS discharge at each main river;
  - the 51-member ECMWF ensemble as context.
- **Highest risk:** Central Tongu (2.3%), Accra Metropolis (2.0%), Ga
  South (2.0%) and North Tongu (1.6%).
- **Levels:** no district reached WATCH, which is plausible as the
  southern rainy season ends. The ensemble expects ordinary rain (median
  wettest day near the 50th percentile of local climate).
- **Output:** `results/v2/shadow/2026-11-02.csv`. Comparing it with what
  happens that week is the first entry of the shadow verification log.

## Roadmap to a leading African system

**Now (weeks), code and decisions only:**

1. **Done:** PR #58 merged (the system never invents data) and the
   leaked API key rotated. **Still to do:** activate the alert-approval
   key.
2. **Working:** `operational.py shadow` runs every Monday (PR #61). The
   first two runs failed on slow Open-Meteo responses from GitHub's
   servers. Retries (PR #63) and batched requests (PR #65, 432 calls down
   to 12) fixed it: on 31 Oct it scored all 216 districts in under 4
   minutes and saved the results to the `shadow-log` branch. Keep it
   running through the 2027 rainy season, and compare it with the live
   rule and with what happened.
3. **Done:** production antecedent rain switched to IMERG (PR #60).
4. **Done:** deployed 30 Oct (revision 00079); PRs #58 and #60 are live.
5. **Send the NADMO request.**

**Next season, with partners:**

6. **NADMO incident records:** verify urban labels and run E8
   impact-based warnings (people affected).
7. **VRA and SONABEL dam release notices:** a dam pathway with real
   data. Bagre spillage is the main driver of floods on the White Volta
   in the north.
8. **GMet and TAHMO station rain:** bias-correct satellite rain and
   detect convective extremes.
9. **HSD gauges:** calibrate GloFAS locally (Google Flood Hub's approach).

**Within a year, to be recognised as leading:**

10. Separate flash-flood (sub-daily, Accra/Kumasi drainage) and riverine
   (Volta, Oti, White Volta) models with their own lead times.
11. A public skill dashboard updated from the shadow log, like ECMWF's
    and Google's published reliability.
12. Align with WMO impact-based forecasting and the IFRC Ghana flood
    Early Action Protocol, so NFCC can provide its trigger.
13. Peer-reviewed publication of the methods and results in this
    document.

## What we can and cannot claim today

We can claim:

- **Coverage:** an open, reproducible, nationwide (216-district)
  evaluation of flood-onset prediction in Ghana. To our knowledge it is
  the first to use news-derived labels audited with radar.
- **Skill:** a calibrated model about 11 times better than chance at
  ranking flood-onset weeks, with documented economic value.
- **Honest lead-time testing:** measured on real archived forecasts.

We cannot yet claim:

- **Verified urban skill:** the labels are unverified.
- **Impact forecasting.**
- **Dam-release flood prediction.**
- **Superiority over GloFAS or Google Flood Hub:** they forecast river
  discharge, not district flood onsets. No head-to-head on the same
  target exists yet.

## Where everything is

- **Code:** `research/flood_experiments/` (experiments, `operational.py`,
  `sar_labels.py`, `forecast_archive.py`, `nadmo.py`).
- **Results:** `research/flood_experiments/results/v2/summary.md` and
  `results/v1_gfd/summary.md`.
- **Model:** `research/flood_experiments/model/`, with `MODEL_CARD.md`.
- **Production fix:** PR #58.
