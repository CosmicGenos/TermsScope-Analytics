"""Hungarian-assignment clause matcher with per-category blocks.

Matching is restricted to clauses with the SAME category in both outputs —
TermsScope's category routing is part of what we're evaluating, so a clause
landing in different categories on each side counts as a miss + a phantom.
A category-agnostic variant is also exposed for secondary metrics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import numpy as np
from scipy.optimize import linear_sum_assignment

from app.schemas.output import AnalysisResult, CategoryName, ClauseClassification


@dataclass
class FlatClause:
    """A clause with its flat index across the whole AnalysisResult."""
    flat_idx: int
    category: CategoryName
    clause: ClauseClassification


def flatten(result: AnalysisResult) -> list[FlatClause]:
    """Flatten in fixed category order: privacy, financial, data_rights, cancellation, liability."""
    order = [
        CategoryName.PRIVACY,
        CategoryName.FINANCIAL,
        CategoryName.DATA_RIGHTS,
        CategoryName.CANCELLATION,
        CategoryName.LIABILITY,
    ]
    cats_by_name = {c.category: c for c in result.categories}
    out: list[FlatClause] = []
    flat_idx = 0
    for name in order:
        cat = cats_by_name.get(name)
        if cat is None:
            continue
        for clause in cat.clauses:
            out.append(FlatClause(flat_idx=flat_idx, category=name, clause=clause))
            flat_idx += 1
    return out


@dataclass
class MatchResult:
    """Output of a clause-matching run."""
    pairs: list[tuple[int, int, float]] = field(default_factory=list)
    """List of (ts_flat_idx, judge_flat_idx, similarity)."""
    unmatched_ts: list[int] = field(default_factory=list)
    unmatched_judge: list[int] = field(default_factory=list)


def _solve_block(
    ts_indices: list[int],
    judge_indices: list[int],
    sim: np.ndarray,
    threshold: float,
) -> tuple[list[tuple[int, int, float]], set[int], set[int]]:
    """Hungarian-assignment over a single similarity block."""
    if not ts_indices or not judge_indices:
        return [], set(ts_indices), set(judge_indices)

    cost = -sim  # maximise similarity == minimise -sim
    row_ind, col_ind = linear_sum_assignment(cost)

    pairs: list[tuple[int, int, float]] = []
    matched_rows, matched_cols = set(), set()
    for r, c in zip(row_ind, col_ind, strict=True):
        s = float(sim[r, c])
        if s >= threshold:
            pairs.append((ts_indices[r], judge_indices[c], s))
            matched_rows.add(r)
            matched_cols.add(c)

    unmatched_ts = {ts_indices[r] for r in range(len(ts_indices)) if r not in matched_rows}
    unmatched_judge = {judge_indices[c] for c in range(len(judge_indices)) if c not in matched_cols}
    return pairs, unmatched_ts, unmatched_judge


def match_clauses(
    ts_flat: list[FlatClause],
    judge_flat: list[FlatClause],
    ts_emb: np.ndarray,
    judge_emb: np.ndarray,
    *,
    threshold: float = 0.75,
    cross_category: bool = False,
) -> MatchResult:
    """Match TermsScope clauses to judge clauses by per-category Hungarian assignment.

    Embeddings are assumed L2-normalised so dot product == cosine similarity.

    Parameters
    ----------
    cross_category : if True, allow matches across different categories
        (for the secondary "category-agnostic" F1 metric).
    """
    if ts_emb.shape[0] != len(ts_flat) or judge_emb.shape[0] != len(judge_flat):
        raise ValueError("Embedding count must equal flat clause count")

    if not ts_flat or not judge_flat:
        return MatchResult(
            pairs=[],
            unmatched_ts=[c.flat_idx for c in ts_flat],
            unmatched_judge=[c.flat_idx for c in judge_flat],
        )

    if cross_category:
        sim = ts_emb @ judge_emb.T
        ts_indices = [c.flat_idx for c in ts_flat]
        judge_indices = [c.flat_idx for c in judge_flat]
        pairs, u_ts, u_j = _solve_block(ts_indices, judge_indices, sim, threshold)
        return MatchResult(
            pairs=pairs,
            unmatched_ts=sorted(u_ts),
            unmatched_judge=sorted(u_j),
        )

    pairs: list[tuple[int, int, float]] = []
    unmatched_ts: set[int] = set()
    unmatched_judge: set[int] = set()
    seen_ts_cats: set[CategoryName] = set()
    seen_judge_cats: set[CategoryName] = set()

    for cat in _all_categories(ts_flat, judge_flat):
        ts_rows = [i for i, c in enumerate(ts_flat) if c.category == cat]
        judge_rows = [j for j, c in enumerate(judge_flat) if c.category == cat]
        if cat in (c.category for c in ts_flat):
            seen_ts_cats.add(cat)
        if cat in (c.category for c in judge_flat):
            seen_judge_cats.add(cat)

        if not ts_rows or not judge_rows:
            unmatched_ts.update(ts_flat[i].flat_idx for i in ts_rows)
            unmatched_judge.update(judge_flat[j].flat_idx for j in judge_rows)
            continue

        sub_sim = ts_emb[ts_rows] @ judge_emb[judge_rows].T
        ts_idx_block = [ts_flat[i].flat_idx for i in ts_rows]
        judge_idx_block = [judge_flat[j].flat_idx for j in judge_rows]
        block_pairs, b_u_ts, b_u_j = _solve_block(ts_idx_block, judge_idx_block, sub_sim, threshold)
        pairs.extend(block_pairs)
        unmatched_ts.update(b_u_ts)
        unmatched_judge.update(b_u_j)

    return MatchResult(
        pairs=pairs,
        unmatched_ts=sorted(unmatched_ts),
        unmatched_judge=sorted(unmatched_judge),
    )


def _all_categories(a: Iterable[FlatClause], b: Iterable[FlatClause]) -> list[CategoryName]:
    seen: list[CategoryName] = []
    for c in list(a) + list(b):
        if c.category not in seen:
            seen.append(c.category)
    return seen
