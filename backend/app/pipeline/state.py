
from __future__ import annotations

from typing import Annotated, Any, Optional

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


def _merge_list(existing: list, new: list) -> list:
    """Reducer that appends new items to existing list."""
    return existing + new


class AnalysisState(TypedDict, total=False):
 

    input_type: str                    # "url" | "text" | "file"
    raw_input: str                     # URL string, pasted text, or filename
    file_bytes: Optional[bytes]        # Raw file content (for uploads)

    raw_content: str                   # Scraped / parsed text
    cleaned_content: str               # Cleaned legal text
    document_title: Optional[str]
    token_count: int

    chunks: list[str]

    privacy_results: Annotated[list[dict], _merge_list]
    financial_results: Annotated[list[dict], _merge_list]
    data_rights_results: Annotated[list[dict], _merge_list]
    cancellation_results: Annotated[list[dict], _merge_list]
    liability_results: Annotated[list[dict], _merge_list]

    final_result: Optional[dict]       # Serialised AnalysisResult
    overall_score: Optional[int]

    status: str                        # Pipeline stage
    error: Optional[str]
    content_hash: Optional[str]
    llm_provider: str
    llm_model: str
