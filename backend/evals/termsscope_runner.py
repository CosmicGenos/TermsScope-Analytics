"""Invokes the existing TermsScope pipeline graph end-to-end with text input.

We bypass the FastAPI / SSE / DB layer — this module talks directly to the
LangGraph compiled graph, which is faster and avoids the database dependency.
The graph's PostgreSQL checkpointer IS still required if the production graph
expects it; we run with no checkpointer (in-memory only) since we don't need
resumability for evals.
"""

from __future__ import annotations

import logging
from typing import Any

from app.config import get_settings
from app.pipeline.graph import compile_graph
from app.schemas.output import AnalysisResult

logger = logging.getLogger(__name__)


_compiled_graph = None


def _graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = compile_graph(checkpointer=None)
    return _compiled_graph


async def run_termsscope_on_text(
    text: str,
    *,
    llm_provider: str | None = None,
    llm_model: str | None = None,
) -> AnalysisResult:
    """Run the production pipeline on raw ToS text and return the AnalysisResult.

    Uses input_type='text' so the acquire node skips network scraping and
    LLM-cleaning, treating the text as already-extracted document content.
    """
    settings = get_settings()
    initial_state: dict[str, Any] = {
        "input_type": "text",
        "raw_input": text,
        "pre_extracted_content": text,  # also short-circuits LLM cleaning
        "llm_provider": llm_provider or settings.default_llm_provider,
        "llm_model": llm_model or settings.default_llm_model,
        "status": "acquiring",
        "privacy_results": [],
        "financial_results": [],
        "data_rights_results": [],
        "cancellation_results": [],
        "liability_results": [],
    }

    config = {"configurable": {"thread_id": f"eval-{abs(hash(text)) % 10**12}"}}
    final_state = await _graph().ainvoke(initial_state, config=config)

    if final_state.get("status") == "error":
        raise RuntimeError(
            f"TermsScope pipeline errored: {final_state.get('error')}"
        )

    final_result = final_state.get("final_result")
    if not final_result:
        raise RuntimeError("Pipeline finished without a final_result. State keys: "
                           + ", ".join(final_state.keys()))

    return AnalysisResult.model_validate(final_result)
