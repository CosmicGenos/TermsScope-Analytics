"""Pass 1: independent analysis by the judge, optionally guided by ToSDR examples.

Without ToSDR data the judge analyses each chunk blind (original behaviour).
When ToSDR data is supplied the prompt is extended with human-validated examples
so the judge is calibrated to known concerns for that specific service — it must
cover all of them AND discover anything extra.

Large documents are split into 20 k-token chunks (no overlap) with
`judge_pass1_chunked`. Each chunk is analysed independently then the per-category
clauses are merged and risk scores recomputed from the merged clause mix.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from app.schemas.output import (
    AnalysisResult, CategoryName, CategoryResult, RiskLevel,
)
from evals.judge.client import JudgeClient
from evals.judge.prompts import PASS1_EXAMPLES_BLOCK, PASS1_SYSTEM, PASS1_USER
from evals.tosdr import ToSDRData, format_examples_block

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Single-chunk pass
# ---------------------------------------------------------------------------

async def judge_pass1(
    text: str,
    client: JudgeClient,
    tosdr_data: ToSDRData | None = None,
) -> AnalysisResult:
    """Run Pass-1 analysis on a single text chunk. Raises if the judge violates
    the schema.

    Parameters
    ----------
    text:
        Raw ToS document text (or one chunk of it).
    client:
        Configured JudgeClient.
    tosdr_data:
        Optional human-validated ToSDR points for this service. When provided,
        examples are injected into the prompt to calibrate the judge.
    """
    system = PASS1_SYSTEM
    user = PASS1_USER.format(document_text=text)

    if tosdr_data and tosdr_data.get("points"):
        examples_body = format_examples_block(tosdr_data)
        user = user + PASS1_EXAMPLES_BLOCK.format(examples_body=examples_body)
        logger.info(
            "Pass 1: guided by %d ToSDR examples (grade=%s)",
            len(tosdr_data["points"]),
            tosdr_data["grade"],
        )
    else:
        logger.info("Pass 1: no ToSDR data — running blind")

    logger.info("Pass 1: judge=%s, chunk_len=%d chars", client.cfg.judge_model, len(text))
    result = await client.structured(system, user, AnalysisResult, max_tokens=16000)

    # Backfill any missing categories so downstream metrics always see all five.
    present = {c.category.value for c in result.categories}
    for cat in CategoryName:
        if cat.value not in present:
            logger.warning("Judge omitted category %s; backfilling empty.", cat.value)
            result.categories.append(
                CategoryResult(
                    category=cat,
                    risk_score=0,
                    clauses=[],
                    summary="(judge did not return clauses for this category)",
                    key_concerns=[],
                )
            )
    return result


# ---------------------------------------------------------------------------
# Merge helpers
# ---------------------------------------------------------------------------

def _recompute_risk_score(clauses: list) -> int:
    """Recompute category risk_score from its clause mix.

    Uses the same calibration anchors stated in PASS1_SYSTEM:
      critical  → +25
      moderate  → +12
      positive  → -8
      neutral   →  0
    Capped to [0, 100].
    """
    score = 0
    for clause in clauses:
        if clause.risk_level == RiskLevel.CRITICAL:
            score += 25
        elif clause.risk_level == RiskLevel.MODERATE:
            score += 12
        elif clause.risk_level == RiskLevel.POSITIVE:
            score -= 8
    return max(0, min(100, score))


def _merge_results(results: list[AnalysisResult]) -> AnalysisResult:
    """Merge per-chunk AnalysisResult objects into one consolidated result.

    Strategy:
    - Clauses: concatenated across all chunks per category.
    - risk_score: recomputed from merged clause mix.
    - overall_score: 100 minus mean of merged category risk scores.
    - Summaries: joined from all chunks (one sentence per chunk).
    - key_concerns: union of all chunks, capped at 5.
    - Metadata (title, company, etc.): taken from the first chunk's result.
    """
    cat_clauses: dict[str, list] = defaultdict(list)
    cat_summaries: dict[str, list[str]] = defaultdict(list)
    cat_concerns: dict[str, list[str]] = defaultdict(list)

    for r in results:
        for cat in r.categories:
            cat_clauses[cat.category.value].extend(cat.clauses)
            if cat.summary:
                cat_summaries[cat.category.value].append(cat.summary)
            cat_concerns[cat.category.value].extend(cat.key_concerns)

    merged_categories: list[CategoryResult] = []
    for cat in CategoryName:
        clauses = cat_clauses.get(cat.value, [])
        risk = _recompute_risk_score(clauses)
        summary = " ".join(cat_summaries.get(cat.value, [])) or "(no findings)"
        concerns = list(dict.fromkeys(cat_concerns.get(cat.value, [])))[:5]  # deduplicate, cap 5
        merged_categories.append(CategoryResult(
            category=cat,
            risk_score=risk,
            clauses=clauses,
            summary=summary,
            key_concerns=concerns,
        ))

    total_clauses = sum(len(c.clauses) for c in merged_categories)
    avg_risk = sum(c.risk_score for c in merged_categories) / len(merged_categories)
    overall_score = max(0, min(100, round(100 - avg_risk)))

    first = results[0]
    overall_summary = " ".join(r.overall_summary for r in results if r.overall_summary)

    return AnalysisResult(
        overall_score=overall_score,
        overall_summary=overall_summary,
        categories=merged_categories,
        document_title=first.document_title,
        company_name=first.company_name,
        document_type=first.document_type,
        effective_date=first.effective_date,
        jurisdiction=first.jurisdiction,
        completeness_score=first.completeness_score,
        total_clauses_analyzed=total_clauses,
    )


# ---------------------------------------------------------------------------
# Chunked entry point (used by runner)
# ---------------------------------------------------------------------------

async def judge_pass1_chunked(
    text: str,
    client: JudgeClient,
    tosdr_data: ToSDRData | None = None,
    chunk_size: int = 20_000,
) -> AnalysisResult:
    """Chunk *text* into 20 k-token slices, run Pass-1 on each, then merge.

    If the document fits in a single chunk the merge step is skipped and the
    raw result is returned directly (no degradation for short docs).
    """
    from evals.chunker import chunk_document

    chunks = chunk_document(text, client.cfg.judge_model, chunk_size=chunk_size)
    logger.info(
        "Pass 1 chunked: %d chunk(s) from %d chars (chunk_size=%d tokens)",
        len(chunks), len(text), chunk_size,
    )

    if len(chunks) == 1:
        return await judge_pass1(chunks[0], client, tosdr_data)

    results: list[AnalysisResult] = []
    for i, chunk in enumerate(chunks, 1):
        logger.info("Pass 1: chunk %d/%d (%d chars)", i, len(chunks), len(chunk))
        result = await judge_pass1(chunk, client, tosdr_data)
        results.append(result)

    merged = _merge_results(results)
    logger.info(
        "Pass 1 merged: %d total clauses, overall_score=%d",
        merged.total_clauses_analyzed, merged.overall_score,
    )
    return merged
