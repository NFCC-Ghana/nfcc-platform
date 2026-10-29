# Flood-prediction experiments (E1–E7, E9)

This folder implements the computational experiments in the
*NFCC CivicFlood Researcher Manuscript Writing Guide*, using only open
data. It is separate from the live platform: nothing in `src/` imports it.

```
pip install -r requirements.txt -r requirements-research.txt
earthengine authenticate                                   # once
python -m research.flood_experiments.build_dataset         # about 1 hour, cached
python -m research.flood_experiments.experiments           # results/results.json
python -m research.flood_experiments.report                # results/summary.md + figures
```

## Study design

| Item | Choice |
| --- | --- |
| Unit | GAUL 2015 district × Monday-start week |
| Coverage | 216 districts in all 10 (2015) regions, March 2000 – December 2018 |
| Target | Flood **onset**: flooded this week, not flooded last week. Weeks right after a flooded week are excluded. |
| Labels | Global Flood Database event extents (≥ 1 km² of non-permanent water in the district, all weeks overlapping the event), plus the platform's 8 documented events in `src/hydrology/flood_polygons.py` |
| Inputs | Known by the end of the target week (perfect-forecast hindcast); no input uses labels |

The study period ends in 2018 because the Global Flood Database ends on
10 Dec 2018. It is the only satellite flood record with district-level
extents for Ghana.

## Data sources

| Group | Variables | Source |
| --- | --- | --- |
| Rainfall | weekly total, wettest day, 4-week antecedent total, weekly lags 1–4 | CHIRPS v2.0 daily, `UCSB-CHG/CHIRPS/DAILY` (Funk et al. 2015) |
| Soil moisture | top-layer volumetric water, week mean and start-of-week | ERA5-Land daily, `ECMWF/ERA5_LAND/DAILY_AGGR` (Muñoz-Sabater et al. 2021) |
| River | surface runoff (week, 4-week antecedent); GloFAS v4 discharge at the district centroid, as log and as ratio to the 2000–2007 median | ERA5-Land; GloFAS v4 reanalysis via the Open-Meteo Flood API (method: Harrigan et al. 2020) |
| Geographic | mean elevation and slope; permanent-water share; built-up share | SRTM 30 m (Farr et al. 2007); JRC Global Surface Water occurrence ≥ 75% (Pekel et al. 2016); GHSL GHS-BUILT-S 2010 (Pesaresi & Politis 2023) |
| Exposure | log population density, 2010 | WorldPop 100 m (Tatem 2017) |
| Labels | flood extent per event | Global Flood Database v1 (Tellman et al. 2021), `GLOBAL_FLOOD_DB/MODIS_EVENTS/V1` |
| Boundaries | districts and regions | FAO GAUL 2015 level 2 |

Not available, so not used: TAHMO and GMet station rainfall, HSD river
gauges and VRA dam records. No partnership data was ever obtained. The
"+ Dam" ablation step is reported as not runnable, rather than filled
with simulated values.

## Experiments

| Guide ID | What | Split |
| --- | --- | --- |
| E1 | Model hierarchy: climatology, persistence, live rainfall rule, logistic regression, random forest, XGBoost (rainfall only), temporal XGBoost (rain lags + soil state), multi-source XGBoost | Temporal (E3) |
| E2 | Cumulative ablation: Baseline → +Soil → +River → +Dam → +Geographic → +Exposure | Temporal |
| E3 | Forward chaining: for each test year *y* in 2008–2018, train on ≤ *y*−2, validate on *y*−1 | — |
| E4 | Leave-one-region-out, with 1/7 of training districts held out for validation | — |
| E5 | Early fusion vs late fusion (mean of per-source models) vs stacking vs the platform's hand-set weights | Temporal |
| E6 | One source missing (training median) or one week stale, at prediction time only | Temporal |
| E7 | Raw vs Platt scaling vs isotonic regression, fitted on each validation year | Temporal |
| E9 | SHAP fidelity (deletion test vs random) and stability (Spearman ρ across 5 bootstrap retrainings) | Train ≤ 2012, test 2014–2018 |

Not runnable in code: E8 (impact layers) needs people-affected counts per
district per event, which no open source has for Ghana. The
human-decision, warning-policy and "incorrect AI" studies need recruited
participants and ethics approval.

**Metrics:** ROC-AUC, PR-AUC, Brier score, expected calibration error,
precision, recall (POD), F1, false-alarm ratio (FAR), missed-event rate
(MER), POFD and SEDI (Ferro & Stephenson 2011). Decision thresholds
maximise F1 on the validation fold and are then applied unchanged to the
test fold. The 90% intervals come from a bootstrap that resamples whole
years.

## Known limitations

- **Incomplete labels.** MODIS (250 m, cloud-limited) misses most short
  urban flash floods, so "no flood" weeks include unrecorded floods. This
  biases precision and FAR toward looking worse, never better.
- **Coarse event timing.** A Global Flood Database event's dates span its
  whole observed period, so onset week can be off by the event's
  detection lag.
- **Perfect-forecast hindcast.** Using the target week's observed rainfall
  stands in for a perfect forecast. Operational skill will be lower by
  the forecast error.
- **Discharge at centroids.** The river nearest a district centroid is not
  always the one that floods it.

## References

- Farr, T. G. et al. (2007). The Shuttle Radar Topography Mission. *Reviews of Geophysics* 45, RG2004. doi:10.1029/2005RG000183
- Ferro, C. A. T. & Stephenson, D. B. (2011). Extremal dependence indices: improved verification measures for deterministic forecasts of rare binary events. *Weather and Forecasting* 26, 699–713. doi:10.1175/WAF-D-10-05030.1
- Funk, C. et al. (2015). The climate hazards infrared precipitation with stations. *Scientific Data* 2, 150066. doi:10.1038/sdata.2015.66
- Harrigan, S. et al. (2020). GloFAS-ERA5 operational global river discharge reanalysis 1979–present. *Earth System Science Data* 12, 2043–2060. doi:10.5194/essd-12-2043-2020
- Lundberg, S. M. et al. (2020). From local explanations to global understanding with explainable AI for trees. *Nature Machine Intelligence* 2, 56–67. doi:10.1038/s42256-019-0138-9
- Muñoz-Sabater, J. et al. (2021). ERA5-Land: a state-of-the-art global reanalysis dataset for land applications. *Earth System Science Data* 13, 4349–4383. doi:10.5194/essd-13-4349-2021
- Pekel, J.-F. et al. (2016). High-resolution mapping of global surface water and its long-term changes. *Nature* 540, 418–422. doi:10.1038/nature20584
- Pesaresi, M. & Politis, P. (2023). GHS-BUILT-S R2023A. European Commission, JRC. doi:10.2905/9F06F36F-4B11-47EC-ABB0-4F8B7B1D72EA
- Platt, J. (1999). Probabilistic outputs for support vector machines. *Advances in Large Margin Classifiers*, 61–74.
- Tatem, A. J. (2017). WorldPop, open data for spatial demography. *Scientific Data* 4, 170004. doi:10.1038/sdata.2017.4
- Tellman, B. et al. (2021). Satellite imaging reveals increased proportion of population exposed to floods. *Nature* 596, 80–86. doi:10.1038/s41586-021-03695-w
- Zadrozny, B. & Elkan, C. (2002). Transforming classifier scores into accurate multiclass probability estimates. *KDD '02*, 694–699.
