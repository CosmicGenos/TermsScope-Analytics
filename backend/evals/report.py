"""Render REPORT.md from metrics.json + plot paths."""

from __future__ import annotations

import json
from pathlib import Path

from evals.plots.category_heatmap import plot_category_heatmap
from evals.plots.confusion_heatmap import plot_confusion_matrix
from evals.plots.coverage_stacked import plot_coverage_stacked
from evals.plots.prf1_bars import plot_prf1_bars
from evals.plots.radar import plot_radar
from evals.plots.score_scatter import plot_score_scatter
from evals.plots.style import init_style


def render_plots(run_dir: Path, suite: dict) -> dict[str, Path | None]:
    init_style()
    return {
        "score_scatter":     plot_score_scatter(suite, run_dir),
        "category_heatmap":  plot_category_heatmap(suite, run_dir),
        "confusion_matrix":  plot_confusion_matrix(suite, run_dir),
        "prf1_bars":         plot_prf1_bars(suite, run_dir),
        "coverage_stacked":  plot_coverage_stacked(suite, run_dir),
        "radar":             plot_radar(suite, run_dir),
    }


def render_report(run_dir: Path) -> Path:
    suite_path = run_dir / "metrics.json"
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    plot_paths = render_plots(run_dir, suite)

    g = suite["global"]
    sm = g["score_summary"]

    md: list[str] = []
    md.append("---")
    md.append(f"run_id: {suite['run_id']}")
    md.append(f"judge: {suite['judge_model']}")
    md.append(f"ts: {suite['ts_model']}")
    md.append(f"embedding_model: {suite['embedding_model']}")
    md.append(f"git_sha: {suite['git_sha']}")
    md.append(f"n_platforms: {suite['n_platforms_succeeded']}/{suite['n_platforms_attempted']}")
    md.append("---\n")

    md.append("# TermsScope LLM-as-Judge Validation Report\n")
    md.append(f"_Generated {suite['generated_at']}_\n")

    md.append("## Headline numbers\n")
    md.append("| Metric | Value | 95% CI |")
    md.append("|---|---|---|")
    md.append(f"| Overall-score Pearson r | {_fmt(sm.get('pearson_r'))} | — |")
    md.append(f"| Overall-score Spearman ρ | {_fmt(sm.get('spearman_rho'))} | — |")
    md.append(f"| Overall-score MAE | {_fmt(sm.get('mae'), 1)} | "
              f"{_fmt_ci(sm.get('mae_ci95'))} |")
    md.append(f"| Overall-score bias (TS−Judge) | {_fmt(sm.get('bias'), 1, signed=True)} | — |")
    md.append(f"| Clause F1 (micro, flagged-only) | {_fmt(g['micro_f1'])} | — |")
    md.append(f"| Clause precision (micro) | {_fmt(g['micro_precision'])} | — |")
    md.append(f"| Clause recall (micro) | {_fmt(g['micro_recall'])} | — |")
    md.append(f"| Risk-level Cohen's κ | {_fmt(g.get('aggregate_kappa'))} | — |")
    halluc = g["hallucination"]
    if halluc.get("mean_ts_hallucination_rate") is not None:
        md.append(f"| TS hallucination rate | {_fmt(halluc['mean_ts_hallucination_rate'])} | "
                  f"{_fmt_ci(halluc.get('ts_hallucination_rate_ci95'))} |")
    md.append("")

    md.append("## Per-category macro F1\n")
    md.append("| Category | macro F1 |")
    md.append("|---|---|")
    for cat, val in g["macro_f1_by_category"].items():
        md.append(f"| {cat} | {_fmt(val)} |")
    md.append("")

    md.append("## Per-platform breakdown\n")
    md.append("| Platform | TS score | Judge score | Δ | Precision | Recall | F1 | κ | Halluc% |")
    md.append("|---|---|---|---|---|---|---|---|---|")
    for p in suite["platforms"]:
        if p.get("error"):
            md.append(f"| {p['platform']} | error | — | — | — | — | — | — | {p['error']} |")
            continue
        cm = p.get("clause_metrics", {})
        kappa = p.get("risk_level_agreement", {}).get("kappa")
        halluc_pct = p.get("hallucination", {}).get("ts_hallucination_rate")
        delta = p["ts_overall_score"] - p["judge_overall_score"]
        md.append(
            f"| {p['platform']} | {p['ts_overall_score']} | {p['judge_overall_score']} "
            f"| {delta:+d} | {_fmt(cm.get('precision'))} | {_fmt(cm.get('recall'))} "
            f"| {_fmt(cm.get('f1'))} | {_fmt(kappa)} "
            f"| {_fmt(halluc_pct)} |"
        )
    md.append("")

    md.append("## Plots\n")
    for name, path in plot_paths.items():
        if path is None:
            continue
        rel = path.relative_to(run_dir).as_posix()
        md.append(f"### {name}\n")
        md.append(f"![{name}]({rel})\n")

    md.append("## Methodology\n")
    md.append(
        "- **Pass 1 (blind)**: judge sees only the document and produces an analysis "
        "in the same schema as TermsScope.\n"
        "- **Pass 2 (A/B verdict)**: judge sees both analyses (random A/B assignment) "
        "and decides matches, hallucinations, and quality scores.\n"
        "- **Clause matching** for precision/recall: OpenAI text-embedding-3-small + "
        "Hungarian assignment per category, threshold 0.75.\n"
        "- **Headline F1** is on flagged clauses only (risk_level ≠ neutral).\n"
        "- **Hallucination** = clauses that, in Pass 2, the judge labels as not actually "
        "present in the document or materially misinterpreted.\n"
        "- All judge calls use temperature 0.0; A/B assignment per platform is "
        f"deterministic from seed={suite['seed']}.\n"
    )

    out = run_dir / "REPORT.md"
    out.write_text("\n".join(md), encoding="utf-8")
    return out


def _fmt(val, digits: int = 2, *, signed: bool = False) -> str:
    if val is None:
        return "—"
    if isinstance(val, (int,)):
        if signed:
            return f"{val:+d}"
        return str(val)
    fmt = f"{{:+.{digits}f}}" if signed else f"{{:.{digits}f}}"
    try:
        return fmt.format(val)
    except (ValueError, TypeError):
        return str(val)


def _fmt_ci(ci) -> str:
    if not ci:
        return "—"
    return f"[{ci[0]:.2f}, {ci[1]:.2f}]"
