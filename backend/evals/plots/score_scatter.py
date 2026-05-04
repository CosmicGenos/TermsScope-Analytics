"""Score correlation scatter plot — TermsScope vs Judge overall_score."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from evals.plots.style import PALETTE, savefig


def plot_score_scatter(suite: dict, run_dir: Path) -> Path | None:
    rows = []
    for p in suite["platforms"]:
        if p.get("error"):
            continue
        rows.append({
            "platform": p["platform"],
            "ts": p["ts_overall_score"],
            "judge": p["judge_overall_score"],
        })
    if not rows:
        return None
    df = pd.DataFrame(rows)
    df.to_csv(run_dir / "plots" / "score_scatter.csv", index=False)

    fig, ax = plt.subplots(figsize=(7, 6))
    sns.scatterplot(data=df, x="ts", y="judge", s=120, color=PALETTE["termsscope"], ax=ax)
    for _, row in df.iterrows():
        ax.annotate(
            row["platform"],
            (row["ts"], row["judge"]),
            xytext=(7, 4),
            textcoords="offset points",
            fontsize=9,
        )
    ax.plot([0, 100], [0, 100], "--", color="gray", alpha=0.6, label="y = x")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xlabel("TermsScope overall_score")
    ax.set_ylabel("Judge overall_score")

    sm = suite["global"]["score_summary"]
    title = "Overall score: TermsScope vs Judge"
    if sm.get("pearson_r") is not None:
        title += f"\nPearson r = {sm['pearson_r']:.2f}, MAE = {sm['mae']:.1f}, bias = {sm['bias']:+.1f}"
    ax.set_title(title)
    ax.legend(loc="lower right")
    return savefig(fig, "score_scatter", run_dir)
