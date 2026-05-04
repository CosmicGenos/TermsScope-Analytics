"""Round-trip tests for Pass2Verdict and AnalysisResult parsing."""

from __future__ import annotations

import pytest

from app.schemas.output import AnalysisResult
from evals.judge.pass2 import _flat_index_map, _slim_for_judge, assign_ab
from evals.judge.schemas import Pass2Verdict

pytestmark = pytest.mark.eval


_PASS2_JSON = {
    "matched": [
        {"a_clause_idx": 0, "b_clause_idx": 1, "same_risk_level": True,
         "judge_risk_level": "moderate", "rationale": "same content"},
    ],
    "unmatched": [
        {"output": "A", "clause_idx": 1, "is_valid_finding": False,
         "rationale": "not in document"},
        {"output": "B", "clause_idx": 0, "is_valid_finding": True,
         "rationale": "TS missed it"},
    ],
    "quality_a": 65, "quality_b": 80,
    "overall_reasoning": "B is more thorough.",
}


def test_pass2_verdict_roundtrip():
    v = Pass2Verdict.model_validate(_PASS2_JSON)
    assert len(v.matched) == 1
    assert v.matched[0].judge_risk_level.value == "moderate"
    assert v.quality_a == 65
    assert v.quality_b == 80


def test_pass2_verdict_quality_bounds():
    bad = dict(_PASS2_JSON)
    bad["quality_a"] = 150
    with pytest.raises(Exception):
        Pass2Verdict.model_validate(bad)


def test_assign_ab_deterministic():
    assert assign_ab(42, "discord") == assign_ab(42, "discord")
    assert assign_ab(7, "spotify") == assign_ab(7, "spotify")
    # Across many slugs the assignment must produce both labels
    slugs = [f"plat{i}" for i in range(40)]
    bools = {assign_ab(42, s) for s in slugs}
    assert bools == {True, False}


def test_flat_index_map_order():
    """Flat indices walk privacy → financial → data_rights → cancellation → liability."""
    sample_json = {
        "overall_score": 50, "overall_summary": "x",
        "categories": [
            {"category": "privacy", "risk_score": 50, "summary": "x", "key_concerns": [],
             "clauses": [{"clause_text": "a", "risk_level": "moderate",
                          "summary": "s", "implication": "i", "section_reference": None}]},
            {"category": "financial", "risk_score": 50, "summary": "x", "key_concerns": [],
             "clauses": [{"clause_text": "b", "risk_level": "moderate",
                          "summary": "s", "implication": "i", "section_reference": None}]},
            {"category": "data_rights", "risk_score": 50, "summary": "x",
             "key_concerns": [], "clauses": []},
            {"category": "cancellation", "risk_score": 50, "summary": "x",
             "key_concerns": [], "clauses": []},
            {"category": "liability", "risk_score": 50, "summary": "x", "key_concerns": [],
             "clauses": [{"clause_text": "c", "risk_level": "critical",
                          "summary": "s", "implication": "i", "section_reference": None}]},
        ],
        "total_clauses_analyzed": 3,
    }
    res = AnalysisResult.model_validate(sample_json)
    flat_map = _flat_index_map(res)
    assert flat_map[0] == "privacy[0]"
    assert flat_map[1] == "financial[0]"
    assert flat_map[2] == "liability[0]"  # data_rights and cancellation skipped (empty)


def test_slim_for_judge_strips_implications():
    sample_json = {
        "overall_score": 50, "overall_summary": "x",
        "categories": [
            {"category": "privacy", "risk_score": 50, "summary": "x", "key_concerns": [],
             "clauses": [{"clause_text": "very long " * 200,
                          "risk_level": "moderate", "summary": "s",
                          "implication": "i", "section_reference": "S1"}]},
            {"category": "financial", "risk_score": 50, "summary": "x",
             "key_concerns": [], "clauses": []},
            {"category": "data_rights", "risk_score": 50, "summary": "x",
             "key_concerns": [], "clauses": []},
            {"category": "cancellation", "risk_score": 50, "summary": "x",
             "key_concerns": [], "clauses": []},
            {"category": "liability", "risk_score": 50, "summary": "x",
             "key_concerns": [], "clauses": []},
        ],
        "total_clauses_analyzed": 1,
    }
    res = AnalysisResult.model_validate(sample_json)
    slim = _slim_for_judge(res)
    assert "implication" not in slim["categories"][0]["clauses"][0]
    assert len(slim["categories"][0]["clauses"][0]["clause_text"]) <= 600
    assert slim["categories"][0]["clauses"][0]["flat_idx"] == 0
