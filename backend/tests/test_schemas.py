"""Pure Pydantic unit tests — no DB, no network required."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.input import AnalysisRequest, InputType
from app.schemas.output import (
    AnalysisResult,
    CategoryName,
    CategoryResult,
    ClauseClassification,
    RiskLevel,
)


def _make_clause(text: str = "We collect your data.", level: RiskLevel = RiskLevel.MODERATE):
    return ClauseClassification(
        clause_text=text,
        risk_level=level,
        summary="Company collects user data.",
        implication="If you accept this, they can collect your personal information.",
        section_reference="Section 3.1",
    )


def _make_category(name: CategoryName, score: int = 50):
    return CategoryResult(
        category=name,
        risk_score=score,
        clauses=[_make_clause()],
        summary="This category has moderate risk.",
        key_concerns=["Data collection", "Third-party sharing"],
    )


def _make_full_result():
    return AnalysisResult(
        overall_score=42,
        overall_summary="This document has several concerning clauses related to data collection and liability.",
        categories=[_make_category(n) for n in CategoryName],
    )


# ── RiskLevel enum ────────────────────────────────────────────────────

def test_risk_level_has_critical():
    assert RiskLevel.CRITICAL == "critical"


def test_risk_level_has_moderate():
    assert RiskLevel.MODERATE == "moderate"


def test_risk_level_has_positive():
    assert RiskLevel.POSITIVE == "positive"


def test_risk_level_has_neutral():
    assert RiskLevel.NEUTRAL == "neutral"


# ── InputType enum ────────────────────────────────────────────────────

def test_input_type_has_url():
    assert InputType.URL == "url"


def test_input_type_has_text():
    assert InputType.TEXT == "text"


def test_input_type_has_file():
    assert InputType.FILE == "file"


# ── CategoryName enum ─────────────────────────────────────────────────

def test_five_categories_exist():
    names = {c.value for c in CategoryName}
    assert names == {"privacy", "financial", "data_rights", "cancellation", "liability"}


# ── ClauseClassification validation ──────────────────────────────────

def test_clause_classification_valid():
    clause = _make_clause("We may share your data with advertisers.", RiskLevel.CRITICAL)
    assert clause.risk_level == RiskLevel.CRITICAL
    assert clause.clause_text == "We may share your data with advertisers."


def test_clause_section_reference_optional():
    clause = ClauseClassification(
        clause_text="We collect cookies.",
        risk_level=RiskLevel.NEUTRAL,
        summary="Standard cookie use.",
        implication="If you accept this, cookies are stored on your device.",
        section_reference=None,
    )
    assert clause.section_reference is None


# ── AnalysisResult validation ─────────────────────────────────────────

def test_analysis_result_roundtrip():
    result = _make_full_result()
    serialised = result.model_dump_json()
    restored = AnalysisResult.model_validate_json(serialised)
    assert restored.overall_score == result.overall_score
    assert len(restored.categories) == 5


def test_overall_score_lower_bound():
    with pytest.raises(ValidationError):
        AnalysisResult(
            overall_score=-1,
            overall_summary="test",
            categories=[_make_category(CategoryName.PRIVACY)],
        )


def test_overall_score_upper_bound():
    with pytest.raises(ValidationError):
        AnalysisResult(
            overall_score=101,
            overall_summary="test",
            categories=[_make_category(CategoryName.PRIVACY)],
        )


def test_category_risk_score_upper_bound():
    with pytest.raises(ValidationError):
        CategoryResult(
            category=CategoryName.PRIVACY,
            risk_score=150,
            summary="test",
        )


def test_disclaimer_has_default():
    result = _make_full_result()
    assert len(result.disclaimer) > 0
    assert "legal advice" in result.disclaimer.lower()


# ── AnalysisRequest validation ────────────────────────────────────────

def test_analysis_request_url_requires_url_field():
    with pytest.raises(ValidationError):
        AnalysisRequest(input_type=InputType.URL)


def test_analysis_request_text_requires_text_field():
    with pytest.raises(ValidationError):
        AnalysisRequest(input_type=InputType.TEXT)


def test_analysis_request_url_valid():
    req = AnalysisRequest(input_type=InputType.URL, url="https://example.com/terms")
    assert str(req.url).startswith("https://example.com")


def test_analysis_request_text_valid():
    req = AnalysisRequest(input_type=InputType.TEXT, text="These are the terms of service.")
    assert req.text == "These are the terms of service."
