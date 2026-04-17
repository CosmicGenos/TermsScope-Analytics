"""LangGraph state schema for the analysis pipeline."""

from __future__ import annotations

from typing import Annotated, Any, Optional

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


def _merge_list(existing: list, new: list) -> list:
    """Reducer that appends new items to existing list."""
    return existing + new


class AnalysisState(TypedDict, total=False):
    """Shared state flowing through the LangGraph pipeline.

    Keys annotated with a reducer (like `Annotated[..., _merge_list]`)
    accumulate values across parallel branches.
    """

    # ── Input ───────────────────────────────────────────
    input_type: str                    # "url" | "text" | "file"
    raw_input: str                     # URL string, pasted text, or filename
    file_bytes: Optional[bytes]        # Raw file content (for uploads)

    # ── After acquisition ─────────────────────────────────
    raw_content: str                   # Scraped / parsed text
    cleaned_content: str               # Cleaned legal text
    document_title: Optional[str]
    token_count: int

    # ── After chunking ────────────────────────────────────
    chunks: list[str]

    # ── Per-category analysis results (accumulated) ───────
    privacy_results: Annotated[list[dict], _merge_list]
    financial_results: Annotated[list[dict], _merge_list]
    data_rights_results: Annotated[list[dict], _merge_list]
    cancellation_results: Annotated[list[dict], _merge_list]
    liability_results: Annotated[list[dict], _merge_list]

    # ── After aggregation ─────────────────────────────────
    final_result: Optional[dict]       # Serialised AnalysisResult
    overall_score: Optional[int]

    # ── Metadata ──────────────────────────────────────────
    status: str                        # Pipeline stage
    error: Optional[str]
    content_hash: Optional[str]
    llm_provider: str
    llm_model: str
