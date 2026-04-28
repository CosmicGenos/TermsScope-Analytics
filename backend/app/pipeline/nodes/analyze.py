"""Analysis nodes — one node per category, all running in parallel via LangGraph Send."""

from __future__ import annotations

import asyncio
import logging

from app.llm.factory import LLMFactory
from app.pipeline.prompts.categories import CATEGORY_INSTRUCTIONS
from app.pipeline.prompts.system import BASE_SYSTEM_PROMPT, build_analyzer_prompt
from app.pipeline.state import AnalysisState
from app.schemas.output import AnalyzerOutput

logger = logging.getLogger(__name__)


async def _analyse_chunk(
    llm, category: str, chunk: str, chunk_idx: int, total_chunks: int
) -> dict:
    """Run a single LLM call: one category × one chunk."""
    instruction = CATEGORY_INSTRUCTIONS[category]
    prompt = build_analyzer_prompt(instruction, chunk, chunk_idx, total_chunks)

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


def _make_category_node(category: str, result_key: str):
    """Factory that returns a node function for a single category."""

    async def node(state: AnalysisState) -> dict:
        chunks = state.get("chunks", [])
        if not chunks:
            return {result_key: [], "status": "aggregating"}

        relevant = list(enumerate(chunks))

        if not relevant:
            logger.info("%s: no relevant chunks found, skipping", category)
            return {result_key: [], "status": "aggregating"}

        llm = LLMFactory.create(
            provider=state.get("llm_provider"),
            model=state.get("llm_model"),
        )

        total = len(chunks)
        logger.info(
            "Starting %s analysis: %d/%d chunks relevant",
            category, len(relevant), total,
        )

        tasks = [
            _analyse_chunk(llm, category, chunk, idx, total)
            for idx, chunk in relevant
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        category_results = []
        for r in results:
            if isinstance(r, Exception):
                logger.error("%s task exception: %s", category, r)
                continue
            if isinstance(r, dict):
                category_results.append(r)

        logger.info("%s analysis complete: %d chunk results", category, len(category_results))
        return {result_key: category_results, "status": "aggregating"}

    node.__name__ = f"analyze_{category}"
    return node


analyze_privacy      = _make_category_node("privacy",      "privacy_results")
analyze_financial    = _make_category_node("financial",    "financial_results")
analyze_data_rights  = _make_category_node("data_rights",  "data_rights_results")
analyze_cancellation = _make_category_node("cancellation", "cancellation_results")
analyze_liability    = _make_category_node("liability",    "liability_results")
