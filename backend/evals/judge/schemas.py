"""Pydantic schemas for Pass-2 judge verdicts."""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field

from app.schemas.output import RiskLevel


class MatchedPair(BaseModel):
    a_clause_idx: int = Field(..., description="Zero-based flat index into Output A clauses.")
    b_clause_idx: int = Field(..., description="Zero-based flat index into Output B clauses.")
    same_risk_level: bool = Field(..., description="Do A and B agree on the risk_level for this clause?")
    judge_risk_level: RiskLevel = Field(..., description="The judge's preferred risk_level for this clause.")
    rationale: str = Field(..., description="One-sentence justification.")


class UnmatchedClause(BaseModel):
    output: Literal["A", "B"] = Field(..., description="Which output the clause belongs to.")
    clause_idx: int = Field(..., description="Zero-based flat index in that output.")
    is_valid_finding: bool = Field(
        ...,
        description="True if the clause is genuinely present in the document and correctly interpreted; False if hallucinated or materially misread.",
    )
    rationale: str = Field(..., description="One-sentence justification.")


class Pass2Verdict(BaseModel):
    matched: List[MatchedPair] = Field(default_factory=list)
    unmatched: List[UnmatchedClause] = Field(default_factory=list)
    quality_a: int = Field(..., ge=0, le=100, description="Overall analytical quality of Output A (0-100).")
    quality_b: int = Field(..., ge=0, le=100, description="Overall analytical quality of Output B (0-100).")
    overall_reasoning: str = Field(..., description="Free-form summary of the comparison.")
