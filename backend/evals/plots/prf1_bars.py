"""Grouped bar chart of precision / recall / F1 per category."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from evals.plots.style import savefig

_CATS = ["privacy", "financial", "data_rights", "cancellation", "liability"]


def plot_prf1_bars(suite: dict, run_dir: Path) -> Path | None:
    rows: list[dict] = []
    for p in suite["platforms"]:
        if p.get("error"):
            continue
        for cat, m in p.get("per_category_clause_metrics", {}).items():
            rows.append({
                "platform": p["platform"], "category": cat,
                "precision": m["precision"], "recall": m["recall"], "f1": m["f1"],
            })
    if not rows:
        return None
    df = pd.DataFrame(rows)
    agg = df.groupby("category")[["precision", "recall", "f1"]].mean().reindex(_CATS)
    agg.to_csv(run_dir / "plots" / "prf1_bars.csv")

    long = agg.reset_index().melt(id_vars="category", var_name="metric", value_name="value")

    fig, ax = plt.subplots(figsize=(9, 5))
    sns.barplot(data=long, x="category", y="value", hue="metric",
                palette={"precision": "#4C72B0", "recall": "#DD8452", "f1": "#55A868"},
                ax=ax)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Score")
    ax.set_xlabel("")
    ax.set_title("Per-category precision / recall / F1\n(averaged across platforms, flagged-only)")
    ax.legend(title="")
    return savefig(fig, "prf1_bars", run_dir)
