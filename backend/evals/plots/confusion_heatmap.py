"""Risk-level confusion matrix (4x4) — raw counts + row-normalised."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from evals.plots.style import savefig

_LABELS = ["critical", "moderate", "positive", "neutral"]


def plot_confusion_matrix(suite: dict, run_dir: Path) -> Path | None:
    cm = suite["global"].get("aggregate_confusion_matrix")
    if not cm:
        return None
    arr = np.array(cm, dtype=int)
    pd.DataFrame(arr, index=_LABELS, columns=_LABELS).to_csv(
        run_dir / "plots" / "confusion_matrix.csv"
    )

    row_sums = arr.sum(axis=1, keepdims=True)
    norm = np.where(row_sums > 0, arr / np.maximum(row_sums, 1), 0.0)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    sns.heatmap(arr, annot=True, fmt="d", cmap="Blues",
                xticklabels=_LABELS, yticklabels=_LABELS, ax=axes[0])
    axes[0].set_title("Risk-level confusion (raw counts)")
    axes[0].set_xlabel("Judge label")
    axes[0].set_ylabel("TermsScope label")

    sns.heatmap(norm, annot=True, fmt=".2f", cmap="Blues",
                xticklabels=_LABELS, yticklabels=_LABELS, vmin=0, vmax=1, ax=axes[1])
    kappa = suite["global"].get("aggregate_kappa")
    title2 = "Row-normalised"
    if kappa is not None:
        title2 += f"\nCohen's κ = {kappa:.2f}"
    axes[1].set_title(title2)
    axes[1].set_xlabel("Judge label")
    axes[1].set_ylabel("TermsScope label")
    return savefig(fig, "confusion_matrix", run_dir)
