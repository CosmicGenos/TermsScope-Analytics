"""Aggregation node — merge per-chunk results, deduplicate, score, and build final output."""

from __future__ import annotations

import logging

from app.pipeline.state import AnalysisState
from app.schemas.output import (
    AnalysisResult,
    CategoryName,
    CategoryResult,
    ClauseClassification,
    RiskLevel,
)

logger = logging.getLogger(__name__)

# Category → (CategoryName enum, state key)
_CATEGORY_MAP = {
    "privacy":      ("privacy",      "privacy_results"),
    "financial":    ("financial",    "financial_results"),
    "data_rights":  ("data_rights",  "data_rights_results"),
    "cancellation": ("cancellation", "cancellation_results"),
    "liability":    ("liability",    "liability_results"),
}

# Risk level weights for scoring
_RISK_WEIGHTS = {
    RiskLevel.CRITICAL: 30,
    RiskLevel.MODERATE: 15,
    RiskLevel.POSITIVE: -10,  # Positive clauses improve the score
    RiskLevel.NEUTRAL: 0,
}


def _merge_category_results(chunk_results: list[dict]) -> CategoryResult:
    """Merge multiple chunk results for a single category.

    Deduplicates clauses by comparing full normalised clause text,
    then calculates a risk score calibrated to the actual clause mix.
    """
    all_clauses: list[ClauseClassification] = []
    summaries: list[str] = []
    seen_texts: set[str] = set()

    for chunk_result in chunk_results:
        for clause_dict in chunk_result.get("clauses", []):
            try:
                clause = ClauseClassification.model_validate(clause_dict)
            except Exception:
                continue

            normalised = " ".join(clause.clause_text.lower().split())
            if normalised not in seen_texts:
                seen_texts.add(normalised)
                all_clauses.append(clause)

        summary = chunk_result.get("chunk_summary", "")
        if summary:
            summaries.append(summary)

    # Calculate risk score (0 = safe, 100 = risky)
    if not all_clauses:
        risk_score = 50  # Neutral default
    else:
        raw_score = sum(_RISK_WEIGHTS.get(c.risk_level, 0) for c in all_clauses)
        # Normalise against the actual achievable range:
        # max_positive = all CRITICAL (+30 each), min_possible = all POSITIVE (-10 each)
        max_positive = len(all_clauses) * 30
        min_possible = len(all_clauses) * -10
        actual_range = max_positive - min_possible  # always 40 * n
        risk_score = max(0, min(100, int(((raw_score - min_possible) / max(actual_range, 1)) * 100)))

    key_concerns = []
    for clause in sorted(
        all_clauses,
        key=lambda c: (
            0 if c.risk_level == RiskLevel.CRITICAL else
            1 if c.risk_level == RiskLevel.MODERATE else 2
        ),
    ):
        if clause.risk_level in (RiskLevel.CRITICAL, RiskLevel.MODERATE):
            key_concerns.append(clause.summary)
        if len(key_concerns) >= 3:
            break

    category_summary = " ".join(summaries[:3]) if summaries else "No significant findings."

    return CategoryResult(
        category=CategoryName(chunk_results[0]["category"]) if chunk_results else CategoryName.PRIVACY,
        risk_score=risk_score,
        clauses=all_clauses,
        summary=category_summary,
        key_concerns=key_concerns,
    )


async def aggregate_results(state: AnalysisState) -> dict:
    """Aggregate per-chunk, per-category results into the final AnalysisResult."""

    category_results: list[CategoryResult] = []

    for cat_name, (_, state_key) in _CATEGORY_MAP.items():
        chunk_results = state.get(state_key, [])
        if chunk_results:
            merged = _merge_category_results(chunk_results)
            merged.category = CategoryName(cat_name)
            category_results.append(merged)
        else:
            category_results.append(
                CategoryResult(
                    category=CategoryName(cat_name),
                    risk_score=50,
                    clauses=[],
                    summary="No relevant clauses found in this category.",
                    key_concerns=[],
                )
            )

    # Overall trust score: 100 minus average risk (higher = more trustworthy)
    if category_results:
        avg_risk = sum(c.risk_score for c in category_results) / len(category_results)
        overall_score = max(0, min(100, 100 - int(avg_risk)))
    else:
        overall_score = 50

    total_clauses = sum(len(c.clauses) for c in category_results)
    critical_count = sum(1 for cat in category_results for c in cat.clauses if c.risk_level == RiskLevel.CRITICAL)
    moderate_count = sum(1 for cat in category_results for c in cat.clauses if c.risk_level == RiskLevel.MODERATE)
    positive_count = sum(1 for cat in category_results for c in cat.clauses if c.risk_level == RiskLevel.POSITIVE)

    # Pull enriched metadata for the summary and output
    doc_metadata: dict = state.get("document_metadata") or {}
    doc_quality: dict = state.get("content_quality") or {}

    company = doc_metadata.get("company_name")
    doc_type = doc_metadata.get("document_type")

    doc_label = " ".join(p for p in [company, doc_type] if p and p != "Unknown") or "This document"

    overall_summary = (
        f"Analysed {total_clauses} clauses across 5 categories in {doc_label}. "
        f"Found {critical_count} critical risk{'s' if critical_count != 1 else ''}, "
        f"{moderate_count} moderate concern{'s' if moderate_count != 1 else ''}, "
        f"and {positive_count} positive clause{'s' if positive_count != 1 else ''}. "
    )

    if overall_score >= 70:
        overall_summary += "Overall, this document appears relatively user-friendly."
    elif overall_score >= 40:
        overall_summary += "This document has some areas of concern worth reviewing."
    else:
        overall_summary += "This document contains significant risks that deserve careful attention."

    analysis_result = AnalysisResult(
        overall_score=overall_score,
        overall_summary=overall_summary,
        categories=category_results,
        document_title=state.get("document_title"),
        company_name=doc_metadata.get("company_name"),
        document_type=doc_metadata.get("document_type"),
        effective_date=doc_metadata.get("effective_date"),
        jurisdiction=doc_metadata.get("jurisdiction"),
        completeness_score=doc_quality.get("completeness_score"),
        total_clauses_analyzed=total_clauses,
    )

    return {
        "final_result": analysis_result.model_dump(),
        "overall_score": overall_score,
        "status": "complete",
    }
