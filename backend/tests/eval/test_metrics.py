"""Unit tests for evals/metrics — hand-computed fixtures."""

from __future__ import annotations

import numpy as np
import pytest

from evals.metrics.aggregate import _kappa_from_cm
from evals.metrics.scoring import overall_score_metrics

pytestmark = pytest.mark.eval


def test_overall_score_metrics_perfect_correlation():
    pairs = [(50, 50), (60, 60), (70, 70), (80, 80)]
    m = overall_score_metrics(pairs)
    assert m["pearson_r"] == pytest.approx(1.0)
    assert m["spearman_rho"] == pytest.approx(1.0)
    assert m["mae"] == pytest.approx(0.0)
    assert m["rmse"] == pytest.approx(0.0)
    assert m["bias"] == pytest.approx(0.0)


def test_overall_score_metrics_constant_bias():
    pairs = [(60, 50), (70, 60), (80, 70), (90, 80)]
    m = overall_score_metrics(pairs)
    assert m["bias"] == pytest.approx(10.0)
    assert m["mae"] == pytest.approx(10.0)
    assert m["rmse"] == pytest.approx(10.0)
    assert m["pearson_r"] == pytest.approx(1.0)


def test_overall_score_metrics_anti_correlation():
    pairs = [(10, 90), (30, 70), (70, 30), (90, 10)]
    m = overall_score_metrics(pairs)
    assert m["pearson_r"] == pytest.approx(-1.0)


def test_kappa_perfect_agreement():
    cm = [[10, 0, 0, 0], [0, 5, 0, 0], [0, 0, 3, 0], [0, 0, 0, 7]]
    assert _kappa_from_cm(cm) == pytest.approx(1.0)


def test_kappa_all_disagree():
    # Off-diagonal-only confusion matrix -> kappa should be negative
    cm = [[0, 4, 0, 0], [3, 0, 0, 0], [0, 0, 0, 5], [0, 0, 6, 0]]
    k = _kappa_from_cm(cm)
    assert k < 0


def test_kappa_chance_agreement():
    # Uniformly distributed predictions and labels => kappa ~ 0
    cm = [[2, 2, 2, 2], [2, 2, 2, 2], [2, 2, 2, 2], [2, 2, 2, 2]]
    assert _kappa_from_cm(cm) == pytest.approx(0.0)


def test_overall_score_metrics_empty():
    m = overall_score_metrics([])
    assert m["n"] == 0
    assert m["pearson_r"] is None
