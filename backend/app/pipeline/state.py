
from __future__ import annotations

from typing import Annotated, Optional

from typing_extensions import TypedDict


def _merge_list(existing: list, new: list) -> list:
    """Reducer that appends new items to existing list."""
    return existing + new


def _last_value(existing, new):
    return new


class AnalysisState(TypedDict, total=False):

    input_type: str                    # "url" | "text" | "file"
    raw_input: str                     # URL string, pasted text, or filename
    file_bytes: Optional[bytes]        # Raw file content (for uploads)
    pre_extracted_content: Optional[str]  # Pre-extracted text passed from API to skip re-extraction

    raw_content: str                   # Scraped / parsed text
    cleaned_content: str               # Cleaned legal text
    document_title: Optional[str]      # Set by enrich node
    token_count: int

    # Document intelligence — set by enrich node
    document_metadata: Optional[dict]
    document_structure: Optional[dict]
    content_quality: Optional[dict]

    chunks: list[str]

    privacy_results: Annotated[list[dict], _merge_list]
    financial_results: Annotated[list[dict], _merge_list]
    data_rights_results: Annotated[list[dict], _merge_list]
    cancellation_results: Annotated[list[dict], _merge_list]
    liability_results: Annotated[list[dict], _merge_list]

    final_result: Optional[dict]       # Serialised AnalysisResult
    overall_score: Optional[int]

    status: Annotated[str, _last_value]  # Pipeline stage
    error: Optional[str]
    content_hash: Optional[str]
    llm_provider: str
    llm_model: str
