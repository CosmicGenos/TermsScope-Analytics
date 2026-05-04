"""Clause-level metrics: precision, recall, F1, Cohen's kappa, confusion matrix."""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from sklearn.metrics import cohen_kappa_score, confusion_matrix

from app.schemas.output import AnalysisResult, CategoryName, RiskLevel
from evals.matching.matcher import FlatClause, MatchResult, flatten

_RISK_ORDER = ["critical", "moderate", "positive", "neutral"]


def _is_flagged(level: RiskLevel) -> bool:
    return level != RiskLevel.NEUTRAL


def filter_flagged(flat: list[FlatClause]) -> set[int]:
    return {f.flat_idx for f in flat if _is_flagged(f.clause.risk_level)}


def precision_recall_f1(
    match: MatchResult,
    ts_flat: list[FlatClause],
    judge_flat: list[FlatClause],
    *,
    flagged_only: bool = True,
) -> dict:
    """Compute P/R/F1.

    "Flagged" = risk_level != neutral on either side. Default headline metric
    is flagged-only since neutral classifications are not meaningful findings.

    Matched pairs count as TP only when BOTH sides count toward the population
    (e.g. for flagged_only=True, both sides must be flagged).
    """
    ts_pop = set(filter_flagged(ts_flat) if flagged_only else {f.flat_idx for f in ts_flat})
    judge_pop = set(filter_flagged(judge_flat) if flagged_only else {f.flat_idx for f in judge_flat})

    pair_set_ts = {p[0] for p in match.pairs if p[0] in ts_pop and p[1] in judge_pop}
    pair_set_jg = {p[1] for p in match.pairs if p[0] in ts_pop and p[1] in judge_pop}

    tp = len(pair_set_ts)
    fp = len(ts_pop - pair_set_ts)        # TS-flagged with no judge counterpart
    fn = len(judge_pop - pair_set_jg)     # Judge-flagged with no TS counterpart

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": precision, "recall": recall, "f1": f1,
        "ts_population": len(ts_pop),
        "judge_population": len(judge_pop),
    }


def per_category_prf1(
    match: MatchResult,
    ts_flat: list[FlatClause],
    judge_flat: list[FlatClause],
    *,
    flagged_only: bool = True,
) -> dict[str, dict]:
    """Per-category P/R/F1 — useful for spotting weak categories."""
    pair_lookup = {(a, b) for a, b, _ in match.pairs}
    out: dict[str, dict] = {}
    for cat in CategoryName:
        ts_idx = {f.flat_idx for f in ts_flat if f.category == cat
                  and (not flagged_only or _is_flagged(f.clause.risk_level))}
        jg_idx = {f.flat_idx for f in judge_flat if f.category == cat
                  and (not flagged_only or _is_flagged(f.clause.risk_level))}
        tp = len({a for (a, b) in pair_lookup if a in ts_idx and b in jg_idx})
        fp = len(ts_idx) - tp
        fn = len(jg_idx) - tp
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        out[cat.value] = {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": precision, "recall": recall, "f1": f1,
            "ts_n": len(ts_idx), "judge_n": len(jg_idx),
        }
    return out


def risk_level_agreement(
    match: MatchResult,
    ts_flat: list[FlatClause],
    judge_flat: list[FlatClause],
) -> dict:
    """Cohen's kappa + confusion matrix on matched clauses' risk_level labels."""
    ts_by_idx = {f.flat_idx: f for f in ts_flat}
    jg_by_idx = {f.flat_idx: f for f in judge_flat}

    ts_labels: list[str] = []
    jg_labels: list[str] = []
    for ts_i, jg_i, _sim in match.pairs:
        ts_labels.append(ts_by_idx[ts_i].clause.risk_level.value)
        jg_labels.append(jg_by_idx[jg_i].clause.risk_level.value)

    if not ts_labels:
        return {
            "n": 0, "kappa": None,
            "confusion_matrix": _zero_matrix(),
            "confusion_matrix_normalised": _zero_matrix(float),
            "labels": _RISK_ORDER,
        }

    cm = confusion_matrix(ts_labels, jg_labels, labels=_RISK_ORDER).tolist()
    cm_arr = np.array(cm, dtype=float)
    row_sums = cm_arr.sum(axis=1, keepdims=True)
    cm_norm = np.where(row_sums > 0, cm_arr / np.maximum(row_sums, 1), 0.0).tolist()

    kappa = float(cohen_kappa_score(ts_labels, jg_labels, labels=_RISK_ORDER))
    return {
        "n": len(ts_labels),
        "kappa": kappa,
        "confusion_matrix": cm,
        "confusion_matrix_normalised": cm_norm,
        "labels": _RISK_ORDER,
    }


def _zero_matrix(dtype=int) -> list[list]:
    return [[dtype(0) for _ in _RISK_ORDER] for _ in _RISK_ORDER]


def aggregate_confusion_matrices(per_platform: list[list[list[int]]]) -> list[list[int]]:
    """Sum 4x4 confusion matrices element-wise across platforms."""
    if not per_platform:
        return _zero_matrix()
    arr = np.zeros((4, 4), dtype=int)
    for cm in per_platform:
        arr = arr + np.array(cm, dtype=int)
    return arr.tolist()


def coverage_breakdown(
    match: MatchResult,
    ts_flat: list[FlatClause],
    judge_flat: list[FlatClause],
) -> dict:
    """Counts for the stacked-bar plot: matched / missed / extra."""
    ts_flagged = filter_flagged(ts_flat)
    judge_flagged = filter_flagged(judge_flat)
    matched = {a for a, b, _ in match.pairs if a in ts_flagged and b in judge_flagged}
    return {
        "matched": len(matched),
        "missed": len(judge_flagged) - len({b for a, b, _ in match.pairs
                                            if a in ts_flagged and b in judge_flagged}),
        "extra": len(ts_flagged) - len(matched),
    }
