"""Write results/summary.md (manuscript-ready tables) and figures from
results/results.json. Run: python -m research.flood_experiments.report
"""

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from research.flood_experiments import config as C  # noqa: E402


def _f(x, nd=3):
    return "–" if x is None or x != x else f"{x:.{nd}f}"


def _ci(ci):
    return f"[{_f(ci[0])}, {_f(ci[1])}]"


def _skill_table(rows, label="Model"):
    head = (
        f"| {label} | ROC-AUC | PR-AUC (90% CI) | Brier | Precision | Recall | F1 "
        "| FAR | MER | SEDI (90% CI) | POD ±1 wk | FAR ±1 wk |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
    )
    body = ""
    for r in rows:
        if "not_run" in r:
            body += f"| {r['model']} | not run: {r['not_run']} |" + " |" * 10 + "\n"
            continue
        body += (
            f"| {r['model']} | {_f(r['roc_auc'])} | {_f(r['pr_auc'])} "
            f"{_ci(r['pr_auc_90ci'])} | {_f(r['brier'], 4)} | {_f(r['precision'])} "
            f"| {_f(r['recall_pod'])} | {_f(r['f1'])} | {_f(r['false_alarm_ratio'])} "
            f"| {_f(r['missed_event_rate'])} | {_f(r['sedi'])} {_ci(r['sedi_90ci'])} "
            f"| {_f(r.get('tol_pod'))} | {_f(r.get('tol_far'))} |\n"
        )
    return head + body


def _bar(ax, labels, values, errs=None, title="", ref=None):
    y = range(len(labels))
    xerr = None
    if errs:
        xerr = [
            [v - e[0] for v, e in zip(values, errs)],
            [e[1] - v for v, e in zip(values, errs)],
        ]
    ax.barh(y, values, xerr=xerr, color="#4a7ab5", ecolor="#555")
    ax.set_yticks(list(y), labels)
    ax.invert_yaxis()
    ax.set_title(title, fontsize=10)
    if ref is not None:
        ax.axvline(ref, color="#999", ls="--", lw=1)


def main():
    R = json.loads((C.RESULTS_DIR / "results.json").read_text())
    d = R["dataset"]
    years = f"{min(d['onsets_by_year'])}–{max(d['onsets_by_year'])}"
    md = [
        f"# NFCC flood-prediction experiments: results ({d.get('study', 'v1_gfd')})",
        "",
        f"{d['districts']} districts in {d['regions']} regions, {d['weeks']} weeks "
        f"(onsets {years}). {d['onset_events']} flood onsets in "
        f"{d['districts_with_onset']} districts, out of {d['rows_scored']:,} scored "
        f"district-weeks (base rate {d['onset_events'] / d['rows_scored']:.4f}).",
        "",
        "Onsets by region: "
        + ", ".join(f"{k} {v}" for k, v in sorted(d["onsets_by_region"].items())),
        "",
        "Onsets by year: "
        + ", ".join(f"{k} {v}" for k, v in sorted(d["onsets_by_year"].items())),
        "",
    ]
    if "flood_weeks_by_label" in d:
        md += [
            f"Groundsource events in Ghana: {d['news_events_in_ghana']}; placed in a "
            f"district: {d['news_events_placed']}; dropped as region- or "
            f"country-level: {d['news_events_too_large_to_place']}. Flood weeks by "
            "label: "
            + ", ".join(f"{k} {v}" for k, v in d["flood_weeks_by_label"].items())
            + ".",
            "",
        ]
    md += [
        "## E1 + E3. Model hierarchy, temporal forward-chaining",
        "",
        "POD/FAR ±1 wk count an alert one week early or late as a hit.",
        "",
        _skill_table(R["E1_E3_hierarchy_temporal"]),
        "## E3b. One week ahead (inputs known when the week starts)",
        "",
        _skill_table(R.get("E3b_forecast", [])),
        "## E2. Source ablation (XGBoost, temporal)",
        "",
        _skill_table(R["E2_ablation"], "Configuration"),
        "## E4. Spatial holdout (leave-one-region-out)",
        "",
        _skill_table(R["E4_spatial"]["pooled"]),
        "| Model | Held-out region | Onsets | PR-AUC | Base rate |",
        "| --- | --- | --- | --- | --- |",
    ]
    md += [
        f"| {r['model']} | {r['region']} | {r['events']} | {_f(r['pr_auc'])} "
        f"| {_f(r['base_rate'], 4)} |"
        for r in R["E4_spatial"]["per_region"]
    ]
    md += [
        "",
        "## E5. Fusion strategy (temporal)",
        "",
        _skill_table(R["E5_fusion"], "Strategy"),
        "## E6. Source degradation (multi-source XGBoost, temporal)",
        "",
        "| Condition | PR-AUC | Δ PR-AUC |",
        "| --- | --- | --- |",
    ]
    md += [
        f"| {r['condition']} | {_f(r['pr_auc'])} | {_f(r['delta_pr_auc'])} |"
        for r in R["E6_degradation"]
    ]
    md += [
        "",
        "## E7. Calibration (multi-source XGBoost, temporal)",
        "",
        "| Method | Brier | ECE | PR-AUC |",
        "| --- | --- | --- | --- |",
    ]
    md += [
        f"| {r['method']} | {_f(r['brier'], 5)} | {_f(r['ece'], 5)} | {_f(r['pr_auc'])} |"
        for r in R["E7_calibration"]
    ]
    s = R["E9_shap"]
    md += [
        "",
        f"## E9. SHAP fidelity and stability (train ≤ "
        f"{int(s['test_period'][:4]) - 2}, test {s['test_period']})",
        "",
        "| Feature | Mean abs SHAP |",
        "| --- | --- |",
    ]
    md += [f"| {k} | {_f(v, 4)} |" for k, v in s["global_mean_abs_shap"].items()]
    md += [
        "",
        "| Features removed (k) | Mean abs change, top-SHAP | Mean abs change, random |",
        "| --- | --- | --- |",
    ]
    md += [
        f"| {r['k']} | {_f(r['mean_abs_change_top_shap'], 4)} "
        f"| {_f(r['mean_abs_change_random'], 4)} |"
        for r in s["fidelity_deletion"]
    ]
    st = s["stability_spearman"]
    md += [
        "",
        f"Global-importance rank stability across bootstrap retrainings: mean "
        f"Spearman ρ {_f(st['mean'])} (min {_f(st['min'])}, {st['pairs']} pairs).",
    ]
    la = R.get("label_audit")
    if la and "not_run" not in la:
        names = {
            "onset": "News flood onset",
            "control_same_week": "Control: other district, same week",
            "control_same_place": "Control: same district, other year",
        }
        md += [
            "",
            "## Label audit: Sentinel-1 at news onsets vs matched controls (±1 week)",
            "",
            "A sampled district-week counts as radar-confirmed when at least "
            "1 km² of new water is detected in a district that was at least half "
            "imaged.",
            "",
            "| Sample | Setting | Sampled | Imaged | Radar detection rate | Median new water (km²) |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for k, r in la["by_kind"].items():
            md.append(
                f"| {names[k]} | all | {r['sampled']} | {r['observed']} "
                f"| {_f(r['detection_rate'])} | {_f(r['median_flood_km2'], 2)} |"
            )
        for setting, kinds in la["by_setting"].items():
            for k, r in kinds.items():
                md.append(
                    f"| {names[k]} | {setting} | {r['sampled']} | {r['observed']} "
                    f"| {_f(r['detection_rate'])} | {_f(r['median_flood_km2'], 2)} |"
                )
        for ctrl in ["control_same_week", "control_same_place"]:
            o = la[f"odds_ratio_vs_{ctrl}"]
            md.append(
                f"\nOdds of radar detection, onset vs {names[ctrl].lower()}: "
                f"{_f(o[0], 2)} (90% CI {_f(o[1], 2)}–{_f(o[2], 2)})."
            )
        md.append("")
    e8 = R["E8_impact"]
    if "not_run" not in e8:
        md += [
            "## E8. Impact layers (NADMO)",
            "",
            f"{e8['records']} records. Spearman ρ of people affected with population "
            f"density {_f(e8['spearman_affected_vs_density'])}; with population × "
            f"built-up share {_f(e8['spearman_affected_vs_built_exposure'])}.",
            "",
        ]
    md += [
        "",
        "## Not runnable",
        "",
    ]
    if "not_run" in e8:
        md.append(f"- E8 impact layers: {e8['not_run']}")
    md += [
        "- + Dam ablation step: no historical dam or reservoir record for Ghana.",
        "- Human decision, warning-policy and incorrect-AI studies: need recruited "
        "participants and ethics approval.",
        "",
    ]
    (C.RESULTS_DIR / "summary.md").write_text("\n".join(md), encoding="utf-8")

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    h = R["E1_E3_hierarchy_temporal"]
    _bar(
        axes[0][0],
        [r["model"] for r in h],
        [r["pr_auc"] for r in h],
        [r["pr_auc_90ci"] for r in h],
        "E1/E3 PR-AUC by model (dashed: base rate)",
        ref=h[0]["base_rate"],
    )
    a = [r for r in R["E2_ablation"] if "not_run" not in r]
    _bar(
        axes[0][1],
        [r["model"] for r in a],
        [r["pr_auc"] for r in a],
        [r["pr_auc_90ci"] for r in a],
        "E2 cumulative ablation, PR-AUC",
    )
    g = R["E6_degradation"]
    _bar(
        axes[1][0],
        [r["condition"] for r in g],
        [r["delta_pr_auc"] for r in g],
        None,
        "E6 change in PR-AUC under degradation",
        ref=0,
    )
    ax = axes[1][1]
    for r in R["E7_calibration"]:
        b = r["reliability"]
        ax.plot(
            [x["mean_predicted"] for x in b],
            [x["observed_rate"] for x in b],
            marker="o",
            label=f"{r['method']} (ECE {r['ece']:.4f})",
        )
    lim = max(
        x["mean_predicted"] for r in R["E7_calibration"] for x in r["reliability"]
    )
    ax.plot([0, lim], [0, lim], color="#999", ls="--", lw=1)
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Observed onset rate")
    ax.set_title("E7 reliability (equal-count bins)", fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(C.RESULTS_DIR / "figures.png", dpi=150)
    print(f"wrote {C.RESULTS_DIR / 'summary.md'} and figures.png")


if __name__ == "__main__":
    main()
