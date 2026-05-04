"""Score-level (overall and per-category) statistical metrics."""

from __future__ import annotations

from typing import Iterable

import numpy as np
from scipy.stats import bootstrap, pearsonr, spearmanr

from app.schemas.output import AnalysisResult, CategoryName


def overall_score_metrics(pairs: Iterable[tuple[int, int]]) -> dict:
    """pairs = [(ts_overall, judge_overall), ...] across platforms."""
    arr = np.array(list(pairs), dtype=float)
    if arr.size == 0:
        return {"n": 0, "pearson_r": None, "spearman_rho": None, "mae": None,
                "rmse": None, "bias": None}
    ts, judge = arr[:, 0], arr[:, 1]
    diff = ts - judge

    pearson = float(pearsonr(ts, judge).statistic) if len(ts) >= 2 else None
    pearson_p = float(pearsonr(ts, judge).pvalue) if len(ts) >= 2 else None
    spearman = float(spearmanr(ts, judge).statistic) if len(ts) >= 2 else None

    mae = float(np.mean(np.abs(diff)))
    rmse = float(np.sqrt(np.mean(diff ** 2)))
    bias = float(np.mean(diff))

    out = {
        "n": int(len(ts)),
        "pearson_r": pearson,
        "pearson_p": pearson_p,
        "spearman_rho": spearman,
        "mae": mae,
        "rmse": rmse,
        "bias": bias,
    }

    # 95% bootstrap CIs (only when we have enough samples)
    if len(ts) >= 4:
        out["mae_ci95"] = _bootstrap_ci(np.abs(diff), np.mean)
    return out


def _bootstrap_ci(data: np.ndarray, statistic) -> list[float]:
    res = bootstrap((data,), statistic, n_resamples=2000, confidence_level=0.95,
                    method="percentile", random_state=42)
    return [float(res.confidence_interval.low), float(res.confidence_interval.high)]


def per_category_correlation(
    rows: list[dict],
) -> dict[str, dict]:
    """rows: [{platform, category, ts_score, judge_score}, ...]
    Returns: {category: {pearson_r, n, mae}}.
    """
    out: dict[str, dict] = {}
    for cat in CategoryName:
        sub = [r for r in rows if r["category"] == cat.value]
        if len(sub) < 2:
            out[cat.value] = {"n": len(sub), "pearson_r": None, "mae": None}
            continue
        ts = np.array([r["ts_score"] for r in sub], dtype=float)
        jg = np.array([r["judge_score"] for r in sub], dtype=float)
        out[cat.value] = {
            "n": len(sub),
            "pearson_r": float(pearsonr(ts, jg).statistic),
            "mae": float(np.mean(np.abs(ts - jg))),
            "ts_mean": float(np.mean(ts)),
            "judge_mean": float(np.mean(jg)),
        }
    return out


def collect_score_rows(platform: str, ts: AnalysisResult, judge: AnalysisResult) -> list[dict]:
    """Build per-category score rows for a single platform."""
    ts_by = {c.category.value: c for c in ts.categories}
    jg_by = {c.category.value: c for c in judge.categories}
    rows = []
    for cat in CategoryName:
        ts_cat = ts_by.get(cat.value)
        jg_cat = jg_by.get(cat.value)
        if ts_cat is None or jg_cat is None:
            continue
        rows.append({
            "platform": platform,
            "category": cat.value,
            "ts_score": ts_cat.risk_score,
            "judge_score": jg_cat.risk_score,
        })
    return rows
