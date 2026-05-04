"""Shared seaborn theme and savefig helper."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
import seaborn as sns

PALETTE = {
    "termsscope": "#2E86AB",
    "judge": "#A23B72",
    "match": "#3CB371",
    "miss": "#D7263D",
    "extra": "#F4A300",
}


def init_style() -> None:
    sns.set_theme(context="paper", style="whitegrid", font_scale=1.1)


def savefig(fig, name: str, run_dir: Path) -> Path:
    plots_dir = run_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    out_path = plots_dir / f"{name}.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out_path
