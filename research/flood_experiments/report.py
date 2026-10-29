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
        "| FAR | MER | SEDI (90% CI) |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
    )
    body = ""
    for r in rows:
        if "not_run" in r:
            body += f"| {r['model']} | not run: {r['not_run']} |" + " |" * 8 + "\n"
            continue
        body += (
            f"| {r['model']} | {_f(r['roc_auc'])} | {_f(r['pr_auc'])} "
            f"{_ci(r['pr_auc_90ci'])} | {_f(r['brier'], 4)} | {_f(r['precision'])} "
            f"| {_f(r['recall_pod'])} | {_f(r['f1'])} | {_f(r['false_alarm_ratio'])} "
            f"| {_f(r['missed_event_rate'])} | {_f(r['sedi'])} {_ci(r['sedi_90ci'])} |\n"
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
    md = [
        "# NFCC flood-prediction experiments: results",
        "",
        f"{d['districts']} districts in {d['regions']} regions, {d['weeks']} weeks "
        f"(2000–2018). {d['onset_events']} flood onsets in "
        f"{d['districts_with_onset']} districts, out of {d['rows_scored']:,} scored "
        f"district-weeks (base rate {d['onset_events'] / d['rows_scored']:.4f}).",
        "",
        "Onsets by region: "
        + ", ".join(f"{k} {v}" for k, v in sorted(d["onsets_by_region"].items())),
        "",
        "## E1 + E3. Model hierarchy, temporal forward-chaining (test 2008–2018)",
        "",
        _skill_table(R["E1_E3_hierarchy_temporal"]),
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
        f"## E9. SHAP fidelity and stability (train ≤ 2012, test {s['test_period']})",
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
        "",
        "## Not runnable",
        "",
        f"- E8 impact layers: {R['E8_impact']['not_run']}",
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
