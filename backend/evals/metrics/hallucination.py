"""Hallucination rate from Pass-2 verdict, attributed to TermsScope vs judge."""

from __future__ import annotations

from evals.judge.schemas import Pass2Verdict


def attribute_hallucinations(
    verdict: Pass2Verdict,
    *,
    a_is_termsscope: bool,
    n_ts_clauses: int,
    n_judge_clauses: int,
) -> dict:
    """Split Pass-2 unmatched/invalid findings into TS-side and judge-side."""
    ts_label = "A" if a_is_termsscope else "B"
    jg_label = "B" if a_is_termsscope else "A"

    ts_halluc = [u for u in verdict.unmatched if u.output == ts_label and not u.is_valid_finding]
    jg_halluc = [u for u in verdict.unmatched if u.output == jg_label and not u.is_valid_finding]
    ts_valid_extra = [u for u in verdict.unmatched if u.output == ts_label and u.is_valid_finding]
    jg_valid_extra = [u for u in verdict.unmatched if u.output == jg_label and u.is_valid_finding]

    ts_quality = verdict.quality_a if a_is_termsscope else verdict.quality_b
    jg_quality = verdict.quality_b if a_is_termsscope else verdict.quality_a

    return {
        "ts_hallucination_count": len(ts_halluc),
        "judge_hallucination_count": len(jg_halluc),
        "ts_hallucination_rate": (len(ts_halluc) / n_ts_clauses) if n_ts_clauses else 0.0,
        "judge_hallucination_rate": (len(jg_halluc) / n_judge_clauses) if n_judge_clauses else 0.0,
        "ts_valid_extra_count": len(ts_valid_extra),
        "judge_valid_extra_count": len(jg_valid_extra),
        "ts_quality_score": ts_quality,
        "judge_quality_score": jg_quality,
    }
