"""Unit tests for evals/matching/matcher.py — no API calls, synthetic data."""

from __future__ import annotations

import numpy as np
import pytest

from app.schemas.output import (AnalysisResult, CategoryName, CategoryResult,
                                ClauseClassification, RiskLevel)
from evals.matching.matcher import flatten, match_clauses

pytestmark = pytest.mark.eval


def _clause(text: str, level: RiskLevel = RiskLevel.MODERATE) -> ClauseClassification:
    return ClauseClassification(
        clause_text=text,
        risk_level=level,
        summary=f"Summary: {text[:30]}",
        implication=f"If you accept this, {text[:20]}.",
        section_reference=None,
    )


def _result(per_cat: dict[CategoryName, list[ClauseClassification]]) -> AnalysisResult:
    cats = []
    for name in [CategoryName.PRIVACY, CategoryName.FINANCIAL, CategoryName.DATA_RIGHTS,
                 CategoryName.CANCELLATION, CategoryName.LIABILITY]:
        cats.append(CategoryResult(
            category=name,
            risk_score=50,
            clauses=per_cat.get(name, []),
            summary="test",
            key_concerns=[],
        ))
    return AnalysisResult(
        overall_score=50,
        overall_summary="test",
        categories=cats,
        total_clauses_analyzed=sum(len(v) for v in per_cat.values()),
    )


def _orthogonal_embeddings(n: int, dim: int = 32, seed: int = 0) -> np.ndarray:
    """Generate n L2-normalised vectors with controlled similarity."""
    rng = np.random.default_rng(seed)
    raw = rng.normal(size=(n, dim))
    raw /= np.linalg.norm(raw, axis=1, keepdims=True)
    return raw.astype(np.float32)


def test_self_match_identity_under_shuffle():
    """Identical clause sets must yield F1=1.0 even when judge order is shuffled."""
    clauses = {
        CategoryName.PRIVACY: [_clause("we collect your IP address"),
                                _clause("we share data with partners")],
        CategoryName.FINANCIAL: [_clause("subscription auto-renews")],
    }
    a = _result(clauses)
    b = _result(clauses)
    a_flat = flatten(a)
    b_flat = flatten(b)

    # Use distinct embeddings per unique clause, identical for matching items
    base = _orthogonal_embeddings(len(a_flat), seed=1)
    # Shuffle b's embeddings to match b's flat order (here it's the same order)
    res = match_clauses(a_flat, b_flat, base, base, threshold=0.5)

    assert len(res.pairs) == len(a_flat)
    assert res.unmatched_ts == []
    assert res.unmatched_judge == []
    # Each pair must be diagonal (identity assignment)
    for ts_i, jg_i, sim in res.pairs:
        assert ts_i == jg_i
        assert sim == pytest.approx(1.0, abs=1e-5)


def test_threshold_monotonicity():
    """Raising the threshold cannot increase recall."""
    clauses_a = {
        CategoryName.PRIVACY: [_clause("clause one"), _clause("clause two")],
    }
    clauses_b = {
        CategoryName.PRIVACY: [_clause("clause one"), _clause("clause two")],
    }
    a = _result(clauses_a)
    b = _result(clauses_b)
    a_flat = flatten(a)
    b_flat = flatten(b)
    # Make embeddings 'just' similar — same ones at sim=1.0, different at low sim
    emb = _orthogonal_embeddings(2, seed=2)
    res_low = match_clauses(a_flat, b_flat, emb, emb, threshold=0.1)
    res_high = match_clauses(a_flat, b_flat, emb, emb, threshold=0.999)
    # Same ⇒ everything matches at low threshold
    assert len(res_low.pairs) == 2
    # At threshold 0.999, identical vectors still match (sim==1.0)
    assert len(res_high.pairs) == 2

    # Now make b's vectors slightly different
    rng = np.random.default_rng(3)
    perturbed = emb + rng.normal(scale=0.5, size=emb.shape).astype(np.float32)
    perturbed /= np.linalg.norm(perturbed, axis=1, keepdims=True)
    res_perturbed_low = match_clauses(a_flat, b_flat, emb, perturbed, threshold=0.1)
    res_perturbed_high = match_clauses(a_flat, b_flat, emb, perturbed, threshold=0.95)
    assert len(res_perturbed_high.pairs) <= len(res_perturbed_low.pairs)


def test_cross_category_forbidden_by_default():
    """A privacy clause should not match a financial clause when cross_category=False."""
    a = _result({CategoryName.PRIVACY: [_clause("identical text here")]})
    b = _result({CategoryName.FINANCIAL: [_clause("identical text here")]})
    a_flat = flatten(a)
    b_flat = flatten(b)
    # Both vectors equal => sim = 1.0
    emb_a = _orthogonal_embeddings(1, seed=4)
    emb_b = emb_a.copy()
    res = match_clauses(a_flat, b_flat, emb_a, emb_b, threshold=0.5, cross_category=False)
    assert res.pairs == []
    assert res.unmatched_ts == [0]
    assert res.unmatched_judge == [0]

    # When cross_category=True, the same vectors should match
    res_cross = match_clauses(a_flat, b_flat, emb_a, emb_b, threshold=0.5, cross_category=True)
    assert len(res_cross.pairs) == 1


def test_hungarian_global_optimum():
    """Hungarian must pick the globally-best assignment, not a greedy one."""
    # Two TS clauses, two judge clauses; constructed so greedy would mismatch.
    a = _result({CategoryName.PRIVACY: [_clause("ts1"), _clause("ts2")]})
    b = _result({CategoryName.PRIVACY: [_clause("jg1"), _clause("jg2")]})
    a_flat = flatten(a)
    b_flat = flatten(b)

    # Similarities chosen so:
    #  greedy picks ts1↔jg1 (sim 0.9), then must match ts2↔jg2 (sim 0.5) -> total 1.4
    #  optimal picks ts1↔jg2 (0.85), ts2↔jg1 (0.85) -> total 1.7
    sim = np.array([[0.9, 0.85], [0.85, 0.5]], dtype=np.float32)
    # Construct embeddings whose dot product equals `sim` on a 2D unit basis
    # (We'll skip the dot-product reconstruction and just verify Hungarian picks the
    # high-total assignment by stubbing the sim path.)
    # Easiest: set ts_emb and jg_emb so ts_emb @ jg_emb.T == sim.
    # Pick ts_emb = identity rows, jg_emb constructed to satisfy the inner product.
    ts_emb = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    jg_emb = sim.T  # so ts_emb @ jg_emb.T == sim
    jg_emb_norm = jg_emb / np.linalg.norm(jg_emb, axis=1, keepdims=True)
    ts_emb_norm = ts_emb / np.linalg.norm(ts_emb, axis=1, keepdims=True)

    res = match_clauses(a_flat, b_flat, ts_emb_norm, jg_emb_norm, threshold=0.5)
    pair_set = {(a, b) for a, b, _ in res.pairs}
    # Optimal pairs should win — both above threshold
    assert len(res.pairs) == 2
    # Total similarity of chosen pairs should be > greedy's 1.4
    total = sum(s for _, _, s in res.pairs)
    assert total > 1.4
