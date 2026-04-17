"""Analysis node — fan-out to 5 category analysers across all chunks."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.llm.factory import LLMFactory
from app.pipeline.prompts.categories import CATEGORY_INSTRUCTIONS
from app.pipeline.prompts.system import BASE_SYSTEM_PROMPT, build_analyzer_prompt
from app.pipeline.state import AnalysisState
from app.schemas.output import AnalyzerOutput

logger = logging.getLogger(__name__)

# Category → state key mapping
_RESULT_KEYS = {
    "privacy": "privacy_results",
    "financial": "financial_results",
    "data_rights": "data_rights_results",
    "cancellation": "cancellation_results",
    "liability": "liability_results",
}


async def _analyse_chunk(
    llm, category: str, chunk: str, chunk_idx: int
) -> dict:
    """Run a single LLM call: one category × one chunk."""
    instruction = CATEGORY_INSTRUCTIONS[category]
    prompt = build_analyzer_prompt(instruction, chunk)

    try:
        result: AnalyzerOutput = await llm.generate(
            prompt=prompt,
            output_schema=AnalyzerOutput,
            system_prompt=BASE_SYSTEM_PROMPT,
            temperature=0.1,
        )
        return {
            "category": category,
            "chunk_idx": chunk_idx,
            "clauses": [c.model_dump() for c in result.clauses],
            "chunk_summary": result.chunk_summary,
        }
    except Exception as exc:
        logger.error(
            "Analysis failed: category=%s chunk=%d error=%s",
            category, chunk_idx, exc,
        )
        return {
            "category": category,
            "chunk_idx": chunk_idx,
            "clauses": [],
            "chunk_summary": f"Analysis failed: {str(exc)}",
        }


async def run_analyzers(state: AnalysisState) -> dict:
    """Run all 5 analysers across all chunks in parallel.

    For N chunks × 5 categories = 5N concurrent LLM calls.
    Results are accumulated into per-category lists.
    """
    chunks = state.get("chunks", [])
    if not chunks:
        return {
            "status": "error",
            "error": "No content chunks to analyse.",
        }

    llm = LLMFactory.create(
        provider=state.get("llm_provider"),
        model=state.get("llm_model"),
    )

    categories = list(CATEGORY_INSTRUCTIONS.keys())

    logger.info(
        "Starting analysis: %d chunks × %d categories = %d LLM calls",
        len(chunks), len(categories), len(chunks) * len(categories),
    )

    # Build all tasks
    tasks: list[asyncio.Task] = []
    for chunk_idx, chunk in enumerate(chunks):
        for category in categories:
            task = asyncio.create_task(
                _analyse_chunk(llm, category, chunk, chunk_idx)
            )
            tasks.append(task)

    # Run all in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Bucket results by category
    updates: dict[str, list[dict]] = {key: [] for key in _RESULT_KEYS.values()}

    for r in results:
        if isinstance(r, Exception):
            logger.error("Task exception: %s", r)
            continue
        if isinstance(r, dict):
            cat = r.get("category", "")
            state_key = _RESULT_KEYS.get(cat)
            if state_key:
                updates[state_key].append(r)

    logger.info(
        "Analysis complete. Results per category: %s",
        {k: len(v) for k, v in updates.items()},
    )

    return {
        **updates,
        "status": "aggregating",
    }
