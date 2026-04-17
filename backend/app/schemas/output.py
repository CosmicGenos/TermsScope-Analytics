"""Output schemas — the structured analysis results returned by the LLM pipeline.

These Pydantic models are used BOTH as the LLM structured-output schema
(via OpenAI's response_format / tool-use) AND as the API response shape.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ── Risk Level ────────────────────────────────────────────────────────

class RiskLevel(str, Enum):
    """Clause risk classification."""

    CRITICAL = "critical"      # 🔴 Requires user attention
    MODERATE = "moderate"      # 🟡 Common but worth knowing
    POSITIVE = "positive"      # 🟢 User-friendly clause
    NEUTRAL = "neutral"        # ⚪ Industry standard


# ── Per-Clause Result ─────────────────────────────────────────────────

class ClauseClassification(BaseModel):
    """A single classified clause from the document."""

    clause_text: str = Field(
        ...,
        description="The exact or closely paraphrased quote from the document.",
    )
    risk_level: RiskLevel = Field(
        ...,
        description="How risky this clause is for the user.",
    )
    summary: str = Field(
        ...,
        description="Plain-English, one-sentence explanation of what this clause means.",
    )
    implication: str = Field(
        ...,
        description=(
            "What this means for the user in practice. "
            "Format: 'If you accept this, they can ...' or similar warning."
        ),
    )
    section_reference: Optional[str] = Field(
        None,
        description="Section title or number where this clause appears, if identifiable.",
    )


# ── Per-Category Result ───────────────────────────────────────────────

class CategoryName(str, Enum):
    """The five analysis categories."""

    PRIVACY = "privacy"
    FINANCIAL = "financial"
    DATA_RIGHTS = "data_rights"
    CANCELLATION = "cancellation"
    LIABILITY = "liability"


class CategoryResult(BaseModel):
    """Aggregated result for one analysis category."""

    category: CategoryName
    risk_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Risk score for this category (0 = safe, 100 = very risky).",
    )
    clauses: List[ClauseClassification] = Field(
        default_factory=list,
        description="Individual clause findings in this category.",
    )
    summary: str = Field(
        ...,
        description="Two- to three-sentence summary of findings in this category.",
    )
    key_concerns: List[str] = Field(
        default_factory=list,
        description="Top 3 most important bullet-point concerns.",
        max_length=5,
    )


# ── Full Analysis Result ──────────────────────────────────────────────

class AnalysisResult(BaseModel):
    """Complete analysis output returned to the frontend."""

    overall_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Overall trust score (0 = avoid, 100 = very trustworthy).",
    )
    overall_summary: str = Field(
        ...,
        description="Two- to three-sentence executive summary in plain English.",
    )
    categories: List[CategoryResult] = Field(
        ...,
        description="Results for each of the five analysis categories.",
    )
    document_title: Optional[str] = Field(
        None,
        description="Detected title of the document, if any.",
    )
    total_clauses_analyzed: int = Field(
        0,
        description="Total number of clauses found and classified.",
    )
    disclaimer: str = Field(
        default=(
            "This analysis is for informational purposes only and does not constitute "
            "legal advice. Always consult a qualified legal professional for specific "
            "legal questions or concerns."
        ),
        description="Legal disclaimer included in every response.",
    )


# ── Analyzer-specific output (used as LLM structured output) ─────────

class AnalyzerOutput(BaseModel):
    """Output schema sent to each individual analyzer LLM call.

    Each analyzer returns this for a single chunk of text.
    """

    clauses: List[ClauseClassification] = Field(
        default_factory=list,
        description="Classified clauses found in this text chunk.",
    )
    chunk_summary: str = Field(
        ...,
        description="Brief summary of findings in this chunk for this category.",
    )
