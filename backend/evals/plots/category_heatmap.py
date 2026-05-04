"""Heatmap of per-category score differences (TS - Judge) across platforms."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from evals.plots.style import savefig

_CATS = ["privacy", "financial", "data_rights", "cancellation", "liability"]


def plot_category_heatmap(suite: dict, run_dir: Path) -> Path | None:
    matrix: list[dict] = []
    for p in suite["platforms"]:
        if p.get("error"):
            continue
        row = {"platform": p["platform"]}
        for r in p.get("per_category_scores", []):
            row[r["category"]] = r["ts_score"] - r["judge_score"]
        matrix.append(row)
    if not matrix:
        return None
    df = pd.DataFrame(matrix).set_index("platform")[_CATS]
    df.to_csv(run_dir / "plots" / "category_heatmap.csv")

    fig, ax = plt.subplots(figsize=(8, max(3, 0.55 * len(df) + 2)))
    sns.heatmap(
        df, annot=True, fmt=".0f", cmap="RdBu_r", center=0,
        cbar_kws={"label": "TS − Judge risk_score"}, ax=ax,
        vmin=-50, vmax=50,
    )
    ax.set_title("Per-category risk-score difference (TS − Judge)\nred = TS rates riskier, blue = TS rates safer")
    ax.set_xlabel("")
    ax.set_ylabel("")
    return savefig(fig, "category_heatmap", run_dir)
