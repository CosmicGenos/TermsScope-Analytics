from __future__ import annotations

import logging
from typing import Optional

from langgraph.graph import END, StateGraph

from app.pipeline.nodes.acquire import acquire_content
from app.pipeline.nodes.aggregate import aggregate_results
from app.pipeline.nodes.analyze import run_analyzers
from app.pipeline.nodes.chunk import chunk_content
from app.pipeline.nodes.validate import validate_content
from app.pipeline.state import AnalysisState

logger = logging.getLogger(__name__)


def _should_continue_after_acquire(state: AnalysisState) -> str:
    """Route after content acquisition."""
    if state.get("status") == "error":
        return END
    return "validate"


def _should_continue_after_validate(state: AnalysisState) -> str:
    """Route after validation."""
    if state.get("status") == "error":
        return END
    return "chunk"


def build_analysis_graph() -> StateGraph:
    graph = StateGraph(AnalysisState)

    
    graph.add_node("acquire", acquire_content)
    graph.add_node("validate", validate_content)
    graph.add_node("chunk", chunk_content)
    graph.add_node("analyze", run_analyzers)
    graph.add_node("aggregate", aggregate_results)

    
    graph.set_entry_point("acquire")

    
    graph.add_conditional_edges("acquire", _should_continue_after_acquire)
    graph.add_conditional_edges("validate", _should_continue_after_validate)
    graph.add_edge("chunk", "analyze")
    graph.add_edge("analyze", "aggregate")
    graph.add_edge("aggregate", END)

    return graph


def compile_graph(checkpointer=None):

    graph = build_analysis_graph()

    compile_kwargs = {}
    if checkpointer:
        compile_kwargs["checkpointer"] = checkpointer

    compiled = graph.compile(**compile_kwargs)
    logger.info("Analysis graph compiled (checkpointer=%s)", type(checkpointer).__name__ if checkpointer else "None")
    return compiled
