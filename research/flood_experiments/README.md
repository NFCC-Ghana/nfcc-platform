# Flood-prediction experiments

This folder implements the computational experiments in the
*NFCC CivicFlood Researcher Manuscript Writing Guide*, using only open
data. It also adds the checks a reviewer would ask for: label quality, a
true forecast mode, and event-tolerant scoring. It is separate from the
live platform: nothing in `src/` imports it.

## Two studies

| Study | Period | Flood labels | Role |
| --- | --- | --- | --- |
| `v2` (default) | 2015–2025 | Groundsource news events (Mayo et al. 2026), our documented events and NADMO records if supplied (`flood_news`). Audited with Sentinel-1 radar (case-control). | Main study |
| `v1_gfd` | 2000–2018 | Global Flood Database (MODIS, Tellman et al. 2021) and documented events | Sensitivity analysis |

v1 had 203 flood onsets in 19 years and no Ghana events at all in
2012–2014 or 2016–2017. That is too few, and too gappy, to train or test
data-driven models. v2 replaces the label source; v1 is kept so the
change of labels can itself be reported.

```
pip install -r requirements.txt -r requirements-research.txt
earthengine authenticate                                       # once
python -m research.flood_experiments.build_dataset dynamic     # these three can run in parallel
python -m research.flood_experiments.build_dataset discharge
python -m research.flood_experiments.build_dataset news
python -m research.flood_experiments.build_dataset             # merge into data/<study>/panel.parquet
python -m research.flood_experiments.sar_labels                # v2: Sentinel-1 label audit (~30 min)
python -m research.flood_experiments.experiments               # results/<study>/results.json
python -m research.flood_experiments.report                    # results/<study>/summary.md + figures
```

Set `NFCC_STUDY=v1_gfd` to run the sensitivity study. To re-run a
single experiment, pass its ID: `python -m research.flood_experiments.experiments E4`.

## Study design (v2)

| Item | Choice |
| --- | --- |
| Unit | GAUL 2015 district × Monday-start week |
| Coverage | 216 districts in all 10 (2015) regions, January 2015 – December 2025 |
| Target | Flood **onset**: flooded this week, not flooded last week. Weeks right after a flooded week are excluded. |
| News label | A Groundsource event in the district overlapping the week. Events are placed by centroid. Events over 1,000 km² are region- or country-level mentions and are dropped. |
| Label audit | Sentinel-1 VH change detection (UN-SPIDER recommended practice) over ±1 week at every news onset and at two matched no-flood controls per onset (another district in the same week; the same district in another year). Radar-confirmed = at least 1 km² of new water in a district at least half imaged. Mapping every district-week is tens of compute-hours on the free Earth Engine tier, so the labels are audited rather than replaced. |
| Inputs | Nowcast: known by the end of the target week (perfect-forecast hindcast). Forecast (E3b): known when the week starts. No input uses labels. |
| Test years | 2018–2025, forward-chaining (train ≤ y−2, validate y−1) |

## Data sources

| Group | Variables | Source |
| --- | --- | --- |
| Rainfall | Weekly total and wettest day: district mean and 95th-percentile pixel; 4-week antecedent total; lags 1–4 | CHIRPS v2.0 daily (Funk et al. 2015) |
| Soil moisture | Top-layer volumetric water: week mean and start of week | ERA5-Land daily (Muñoz-Sabater et al. 2021) |
| River | Surface runoff; GloFAS v4 discharge at the district's main river (the MERIT Hydro cell with the largest upstream area), as log and as ratio to the pre-test median | ERA5-Land; GloFAS v4 via the Open-Meteo Flood API (Harrigan et al. 2020); MERIT Hydro (Yamazaki et al. 2019) |
| Geographic | Mean elevation and slope; permanent-water share; built-up share | SRTM; JRC Global Surface Water; GHSL 2010 |
| Exposure | Log population density, 2010 | WorldPop 100 m |
| News labels | Flood events from news, geocoded and dated | Groundsource (Mayo et al. 2026), `projects/sat-io/open-datasets/groundsource_2026` |
| Label audit | New-water and imaged km² per sampled district-week | Sentinel-1 GRD, `sar_labels.py` |
| NADMO labels | Incident date, district, deaths, people affected | Requested from NADMO; see `nadmo_data_request.md` |
| Boundaries | Districts and regions | FAO GAUL 2015 level 2 |

We could not obtain TAHMO or GMet station rainfall, HSD river gauges, or
VRA dam records. The "+ Dam" ablation step is therefore reported as not
runnable rather than filled with simulated values.

## Experiments

| ID | What |
| --- | --- |
| E1 | Model hierarchy: climatology; persistence; the live rainfall rule; a river-percentile (GloFAS-style) benchmark; logistic regression; random forest; XGBoost on rainfall; temporal XGBoost; multi-source XGBoost |
| E2 | Cumulative ablation: Baseline → +Soil → +River → +Dam → +Geographic → +Exposure |
| E3 | Forward-chaining by year |
| E3b | One week ahead: forecast-mode models vs the nowcast |
| E4 | Leave-one-region-out *and* separated in time. A purely spatial split leaks, because one flood event covers several regions in the same weeks (v1: PR-AUC 0.31 leaky vs 0.001 clean). |
| E5 | Early fusion vs late fusion vs stacking vs the platform's hand-set weights |
| E6 | One source missing (training median) or one week stale, at prediction time only |
| E7 | Raw vs Platt scaling vs isotonic regression |
| E8 | Impact layers: Spearman ρ of NADMO people-affected counts with exposure. Runs only once NADMO records are supplied. |
| E9 | SHAP fidelity (deletion test vs random) and stability (Spearman ρ across bootstrap retrainings) |
| LA | Label audit: radar detection rate at news onsets vs matched controls, overall and for urban vs rural districts, with odds ratios |

The human-decision, warning-policy and "incorrect AI" studies need
recruited participants and ethics approval, so they are not in code.

## Modelling and evaluation choices

- **Monotone XGBoost.** Rain, soil, runoff and discharge inputs can only raise risk. With a few hundred events, unconstrained trees learn physically impossible shapes. Trees are shallow (depth 3) and regularised.
- **Thresholds.** The decision threshold maximises F1 on the validation year. When that year has fewer than 5 onsets, the threshold is chosen on the training years instead.
- **Event-tolerant scores.** POD and FAR at ±1 week sit alongside strict week-matching, because news and satellite dating can be a week off.
- **Metrics.** ROC-AUC, PR-AUC, Brier, ECE, precision, recall (POD), F1, FAR, MER, POFD and SEDI (Ferro & Stephenson 2011), with year-block bootstrap 90% intervals.

## Known limitations

- **News labels follow media coverage.** Groundsource recall is lower where digital news is scarce (rural north). Reporting also grows over time: 124 Ghana events in 2015 vs 338 in 2022. Models may partly learn where and when floods get reported. The label audit measures how often reported onsets are real; it does not remove the bias.
- **Radar misses some floods.** Sentinel-1 images each district every 6–12 days. It misses short flash floods between passes, floods under dense vegetation and floods in built-up areas (buildings scatter the signal back). A news onset that radar does not confirm is therefore not necessarily false, especially in cities; the audit reports urban and rural districts separately for this reason.
- **Coarse event timing.** A record's dates are when it was reported or imaged, not necessarily when the flood started.
- **Perfect-forecast hindcast.** The nowcast uses observed rainfall for the target week. E3b shows the operational one-week-ahead case.
- **GAUL 2015 districts.** Ghana has had 261 districts since 2018. Records for new districts map to their 2015 parent.

## References

- Farr, T. G. et al. (2007). The Shuttle Radar Topography Mission. *Reviews of Geophysics* 45, RG2004. doi:10.1029/2005RG000183
- Ferro, C. A. T. & Stephenson, D. B. (2011). Extremal dependence indices: improved verification measures for deterministic forecasts of rare binary events. *Weather and Forecasting* 26, 699–713. doi:10.1175/WAF-D-10-05030.1
- Funk, C. et al. (2015). The climate hazards infrared precipitation with stations. *Scientific Data* 2, 150066. doi:10.1038/sdata.2015.66
- Harrigan, S. et al. (2020). GloFAS-ERA5 operational global river discharge reanalysis 1979–present. *Earth System Science Data* 12, 2043–2060. doi:10.5194/essd-12-2043-2020
- Lundberg, S. M. et al. (2020). From local explanations to global understanding with explainable AI for trees. *Nature Machine Intelligence* 2, 56–67. doi:10.1038/s42256-019-0138-9
- Mayo, R. et al. (2026). Groundsource: a dataset of flood events from news. EarthArXiv preprint; data doi:10.5281/zenodo.18647054
- Muñoz-Sabater, J. et al. (2021). ERA5-Land: a state-of-the-art global reanalysis dataset for land applications. *Earth System Science Data* 13, 4349–4383. doi:10.5194/essd-13-4349-2021
- Pekel, J.-F. et al. (2016). High-resolution mapping of global surface water and its long-term changes. *Nature* 540, 418–422. doi:10.1038/nature20584
- Pesaresi, M. & Politis, P. (2023). GHS-BUILT-S R2023A. European Commission, JRC. doi:10.2905/9F06F36F-4B11-47EC-ABB0-4F8B7B1D72EA
- Platt, J. (1999). Probabilistic outputs for support vector machines. *Advances in Large Margin Classifiers*, 61–74.
- Tatem, A. J. (2017). WorldPop, open data for spatial demography. *Scientific Data* 4, 170004. doi:10.1038/sdata.2017.4
- Tellman, B. et al. (2021). Satellite imaging reveals increased proportion of population exposed to floods. *Nature* 596, 80–86. doi:10.1038/s41586-021-03695-w
- UN-SPIDER (2019). Recommended Practice: Flood mapping and damage assessment using Sentinel-1 SAR data in Google Earth Engine.
- Yamazaki, D. et al. (2019). MERIT Hydro: a high-resolution global hydrography map based on latest topography dataset. *Water Resources Research* 55, 5053–5073. doi:10.1029/2019WR024873
- Zadrozny, B. & Elkan, C. (2002). Transforming classifier scores into accurate multiclass probability estimates. *KDD '02*, 694–699.
