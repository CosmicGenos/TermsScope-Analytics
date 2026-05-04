"""Pass 2: A/B comparative verdict from the judge.

The judge sees both analyses (random A/B assignment) and the document, then
classifies matched pairs, unmatched clauses (valid finding vs hallucination),
and assigns quality scores.
"""

from __future__ import annotations

import json
import logging
import random
from typing import Iterable

from app.schemas.output import AnalysisResult, CategoryName
from evals.judge.client import JudgeClient
from evals.judge.prompts import PASS2_SYSTEM, PASS2_USER
from evals.judge.schemas import Pass2Verdict

logger = logging.getLogger(__name__)


def _flat_index_map(result: AnalysisResult) -> dict[int, str]:
    """{flat_idx: 'category[position]'} — for human-readable prompt indexing."""
    order = [
        CategoryName.PRIVACY,
        CategoryName.FINANCIAL,
        CategoryName.DATA_RIGHTS,
        CategoryName.CANCELLATION,
        CategoryName.LIABILITY,
    ]
    cats_by = {c.category: c for c in result.categories}
    out: dict[int, str] = {}
    flat = 0
    for name in order:
        cat = cats_by.get(name)
        if cat is None:
            continue
        for i, _clause in enumerate(cat.clauses):
            out[flat] = f"{name.value}[{i}]"
            flat += 1
    return out


def _slim_for_judge(result: AnalysisResult) -> dict:
    """Strip large/irrelevant fields and add flat indices for the judge."""
    order = [
        CategoryName.PRIVACY,
        CategoryName.FINANCIAL,
        CategoryName.DATA_RIGHTS,
        CategoryName.CANCELLATION,
        CategoryName.LIABILITY,
    ]
    cats_by = {c.category: c for c in result.categories}
    flat = 0
    cats_out = []
    for name in order:
        cat = cats_by.get(name)
        if cat is None:
            continue
        clauses_out = []
        for clause in cat.clauses:
            clauses_out.append({
                "flat_idx": flat,
                "clause_text": clause.clause_text[:600],
                "risk_level": clause.risk_level.value,
                "summary": clause.summary,
                "section_reference": clause.section_reference,
            })
            flat += 1
        cats_out.append({
            "category": name.value,
            "risk_score": cat.risk_score,
            "summary": cat.summary,
            "clauses": clauses_out,
        })
    return {
        "overall_score": result.overall_score,
        "overall_summary": result.overall_summary,
        "company_name": result.company_name,
        "total_clauses_analyzed": result.total_clauses_analyzed,
        "categories": cats_out,
    }


def assign_ab(seed: int, platform_slug: str) -> bool:
    """Returns True if TermsScope is Output A, False if it is Output B."""
    rng = random.Random(seed + abs(hash(platform_slug)))
    return rng.random() < 0.5


async def judge_pass2(
    document_text: str,
    ts_result: AnalysisResult,
    judge_result: AnalysisResult,
    *,
    a_is_termsscope: bool,
    client: JudgeClient,
) -> Pass2Verdict:
    """Run Pass 2 with a randomised A/B assignment."""
    a, b = (ts_result, judge_result) if a_is_termsscope else (judge_result, ts_result)
    a_index_map = _flat_index_map(a)
    b_index_map = _flat_index_map(b)

    user = PASS2_USER.format(
        document_text=document_text,
        a_index_map=json.dumps(a_index_map),
        b_index_map=json.dumps(b_index_map),
        output_a_json=json.dumps(_slim_for_judge(a), indent=2),
        output_b_json=json.dumps(_slim_for_judge(b), indent=2),
    )
    logger.info("Pass 2: A=%s clauses, B=%s clauses",
                len(a_index_map), len(b_index_map))
    return await client.structured(PASS2_SYSTEM, user, Pass2Verdict, max_tokens=8000)
