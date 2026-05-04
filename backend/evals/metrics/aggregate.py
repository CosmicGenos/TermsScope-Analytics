"""Combine per-platform metrics into the suite-level metrics.json structure."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field, asdict
from typing import Any

import numpy as np
from scipy.stats import bootstrap

from evals.metrics.clause_metrics import aggregate_confusion_matrices
from evals.metrics.scoring import overall_score_metrics, per_category_correlation


@dataclass
class PlatformMetrics:
    platform: str
    ts_overall_score: int
    judge_overall_score: int
    ts_clause_count: int
    judge_clause_count: int
    score_metrics: dict = field(default_factory=dict)
    clause_metrics: dict = field(default_factory=dict)
    per_category_clause_metrics: dict = field(default_factory=dict)
    per_category_scores: list[dict] = field(default_factory=list)
    risk_level_agreement: dict = field(default_factory=dict)
    coverage: dict = field(default_factory=dict)
    hallucination: dict = field(default_factory=dict)
    error: str | None = None


def build_suite_metrics(
    platform_metrics: list[PlatformMetrics],
    *,
    run_id: str,
    judge_model: str,
    ts_model: str,
    embedding_model: str,
    git_sha: str | None,
    seed: int,
) -> dict[str, Any]:
    """Aggregate per-platform metrics into a single JSON-friendly dict."""
    successful = [pm for pm in platform_metrics if pm.error is None]
    score_pairs = [(pm.ts_overall_score, pm.judge_overall_score) for pm in successful]

    score_summary = overall_score_metrics(score_pairs)

    all_score_rows: list[dict] = []
    for pm in successful:
        all_score_rows.extend(pm.per_category_scores)
    cat_corr = per_category_correlation(all_score_rows)

    # Aggregate clause-level metrics (micro across platforms)
    micro_tp = sum(pm.clause_metrics.get("tp", 0) for pm in successful)
    micro_fp = sum(pm.clause_metrics.get("fp", 0) for pm in successful)
    micro_fn = sum(pm.clause_metrics.get("fn", 0) for pm in successful)
    micro_p = micro_tp / (micro_tp + micro_fp) if (micro_tp + micro_fp) else 0.0
    micro_r = micro_tp / (micro_tp + micro_fn) if (micro_tp + micro_fn) else 0.0
    micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r) if (micro_p + micro_r) else 0.0

    # Macro F1 by category — average of per-category F1 across platforms
    cat_f1: dict[str, list[float]] = {}
    for pm in successful:
        for cat, m in pm.per_category_clause_metrics.items():
            cat_f1.setdefault(cat, []).append(m.get("f1", 0.0))
    macro_f1_by_cat = {cat: float(np.mean(v)) if v else 0.0 for cat, v in cat_f1.items()}

    cms = [pm.risk_level_agreement.get("confusion_matrix")
           for pm in successful
           if pm.risk_level_agreement.get("confusion_matrix")]
    agg_cm = aggregate_confusion_matrices(cms) if cms else None

    # Recompute aggregate kappa from the summed confusion matrix.
    agg_kappa = _kappa_from_cm(agg_cm) if agg_cm else None

    # Hallucination rate aggregate
    halluc_ts = [pm.hallucination.get("ts_hallucination_rate")
                 for pm in successful if pm.hallucination]
    halluc_ts = [x for x in halluc_ts if x is not None]
    halluc_summary = {
        "mean_ts_hallucination_rate": float(np.mean(halluc_ts)) if halluc_ts else None,
        "ts_hallucination_rate_ci95": (_ci(halluc_ts) if len(halluc_ts) >= 4 else None),
        "platforms_with_pass2": len(halluc_ts),
    }

    # Coverage rate (recall on flagged clauses) aggregate
    recalls = [pm.clause_metrics.get("recall") for pm in successful]
    recalls = [r for r in recalls if r is not None]
    f1_summary = {
        "mean_f1": float(np.mean([pm.clause_metrics.get("f1", 0.0) for pm in successful])),
        "mean_precision": float(np.mean([pm.clause_metrics.get("precision", 0.0) for pm in successful])),
        "mean_recall": float(np.mean(recalls)) if recalls else 0.0,
    }

    suite = {
        "run_id": run_id,
        "generated_at": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "judge_model": judge_model,
        "ts_model": ts_model,
        "embedding_model": embedding_model,
        "git_sha": git_sha,
        "seed": seed,
        "n_platforms_attempted": len(platform_metrics),
        "n_platforms_succeeded": len(successful),
        "n_platforms_errored": len(platform_metrics) - len(successful),
        "global": {
            "score_summary": score_summary,
            "per_category_score_correlation": cat_corr,
            "micro_precision": micro_p,
            "micro_recall": micro_r,
            "micro_f1": micro_f1,
            "macro_f1_by_category": macro_f1_by_cat,
            "f1_means": f1_summary,
            "aggregate_confusion_matrix": agg_cm,
            "aggregate_kappa": agg_kappa,
            "hallucination": halluc_summary,
        },
        "platforms": [_platform_to_dict(pm) for pm in platform_metrics],
    }
    return suite


def _platform_to_dict(pm: PlatformMetrics) -> dict:
    d = asdict(pm)
    return d


def _kappa_from_cm(cm: list[list[int]]) -> float:
    """Compute Cohen's kappa from a confusion matrix."""
    arr = np.array(cm, dtype=float)
    n = arr.sum()
    if n == 0:
        return 0.0
    po = arr.trace() / n
    rows = arr.sum(axis=1) / n
    cols = arr.sum(axis=0) / n
    pe = float((rows * cols).sum())
    if pe == 1.0:
        return 0.0
    return float((po - pe) / (1 - pe))


def _ci(data: list[float]) -> list[float]:
    res = bootstrap((np.array(data, dtype=float),), np.mean,
                    n_resamples=2000, confidence_level=0.95,
                    method="percentile", random_state=42)
    return [float(res.confidence_interval.low), float(res.confidence_interval.high)]
