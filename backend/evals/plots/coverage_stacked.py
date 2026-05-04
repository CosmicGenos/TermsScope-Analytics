"""Per-platform stacked bar: matched / missed / extra clauses."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from evals.plots.style import PALETTE, savefig


def plot_coverage_stacked(suite: dict, run_dir: Path) -> Path | None:
    rows = []
    for p in suite["platforms"]:
        if p.get("error"):
            continue
        cov = p.get("coverage", {})
        rows.append({
            "platform": p["platform"],
            "matched": cov.get("matched", 0),
            "missed": cov.get("missed", 0),
            "extra": cov.get("extra", 0),
        })
    if not rows:
        return None
    df = pd.DataFrame(rows).sort_values("matched", ascending=False)
    df.to_csv(run_dir / "plots" / "coverage_stacked.csv", index=False)

    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(df))
    ax.bar(x, df["matched"], color=PALETTE["match"], label="Matched (TP)")
    ax.bar(x, df["missed"], bottom=df["matched"], color=PALETTE["miss"], label="Missed by TS (FN)")
    ax.bar(x, df["extra"], bottom=df["matched"] + df["missed"],
           color=PALETTE["extra"], label="TS-only (FP/extra)")
    ax.set_xticks(x)
    ax.set_xticklabels(df["platform"], rotation=30, ha="right")
    ax.set_ylabel("Flagged clauses")
    ax.set_title("Clause coverage per platform — matched / missed / extra")
    ax.legend()
    return savefig(fig, "coverage_stacked", run_dir)
