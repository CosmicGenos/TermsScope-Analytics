"""Per-platform radar charts of category risk_scores — TS vs Judge overlaid."""

from __future__ import annotations

from math import pi
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from evals.plots.style import PALETTE, savefig

_CATS = ["privacy", "financial", "data_rights", "cancellation", "liability"]


def plot_radar(suite: dict, run_dir: Path) -> Path | None:
    rows = [p for p in suite["platforms"] if not p.get("error") and p.get("per_category_scores")]
    if not rows:
        return None

    n = len(rows)
    cols = min(4, n)
    rows_grid = (n + cols - 1) // cols
    fig, axes = plt.subplots(
        rows_grid, cols,
        figsize=(4.5 * cols, 4.5 * rows_grid),
        subplot_kw=dict(polar=True),
        squeeze=False,
    )

    angles = np.linspace(0, 2 * pi, len(_CATS), endpoint=False).tolist()
    closed_angles = angles + [angles[0]]

    for i, p in enumerate(rows):
        ax = axes[i // cols][i % cols]
        ts_by = {r["category"]: r["ts_score"] for r in p["per_category_scores"]}
        jg_by = {r["category"]: r["judge_score"] for r in p["per_category_scores"]}
        ts_vals = [ts_by.get(c, 0) for c in _CATS]
        jg_vals = [jg_by.get(c, 0) for c in _CATS]

        ax.plot(closed_angles, ts_vals + [ts_vals[0]],
                color=PALETTE["termsscope"], label="TermsScope", linewidth=2)
        ax.fill(closed_angles, ts_vals + [ts_vals[0]],
                color=PALETTE["termsscope"], alpha=0.20)
        ax.plot(closed_angles, jg_vals + [jg_vals[0]],
                color=PALETTE["judge"], label="Judge", linewidth=2)
        ax.fill(closed_angles, jg_vals + [jg_vals[0]],
                color=PALETTE["judge"], alpha=0.20)

        ax.set_xticks(angles)
        ax.set_xticklabels(_CATS, fontsize=8)
        ax.set_ylim(0, 100)
        ax.set_yticks([25, 50, 75])
        ax.set_yticklabels([], fontsize=7)
        ax.set_title(p["platform"], y=1.08)

    # Hide any unused axes
    for j in range(n, rows_grid * cols):
        axes[j // cols][j % cols].axis("off")

    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Category risk-score profile per platform — TermsScope vs Judge", y=1.02)
    return savefig(fig, "radar", run_dir)
