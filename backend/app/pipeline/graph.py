from __future__ import annotations

import logging

from langgraph.graph import END, StateGraph
from langgraph.types import Send

from app.pipeline.nodes.acquire import acquire_content
from app.pipeline.nodes.aggregate import aggregate_results
from app.pipeline.nodes.analyze import (
    analyze_cancellation,
    analyze_data_rights,
    analyze_financial,
    analyze_liability,
    analyze_privacy,
)
from app.pipeline.nodes.chunk import chunk_content
from app.pipeline.nodes.validate import validate_content
from app.pipeline.state import AnalysisState

logger = logging.getLogger(__name__)

_CATEGORY_NODES = [
    "analyze_privacy",
    "analyze_financial",
    "analyze_data_rights",
    "analyze_cancellation",
    "analyze_liability",
]


def _should_continue_after_acquire(state: AnalysisState) -> str:
    if state.get("status") == "error":
        return END
    return "validate"


def _should_continue_after_validate(state: AnalysisState) -> str:
    if state.get("status") == "error":
        return END
    return "chunk"


def _dispatch_analyzers(state: AnalysisState) -> list[Send]:
    """Fan-out: dispatch all 5 category nodes in parallel."""
    return [
        Send("analyze_privacy",      state),
        Send("analyze_financial",    state),
        Send("analyze_data_rights",  state),
        Send("analyze_cancellation", state),
        Send("analyze_liability",    state),
    ]


def build_analysis_graph() -> StateGraph:
    graph = StateGraph(AnalysisState)

    graph.add_node("acquire",             acquire_content)
    graph.add_node("validate",            validate_content)
    graph.add_node("chunk",               chunk_content)
    graph.add_node("analyze_privacy",     analyze_privacy)
    graph.add_node("analyze_financial",   analyze_financial)
    graph.add_node("analyze_data_rights", analyze_data_rights)
    graph.add_node("analyze_cancellation",analyze_cancellation)
    graph.add_node("analyze_liability",   analyze_liability)
    graph.add_node("aggregate",           aggregate_results)

    graph.set_entry_point("acquire")

    graph.add_conditional_edges("acquire",   _should_continue_after_acquire)
    graph.add_conditional_edges("validate",  _should_continue_after_validate)
    graph.add_conditional_edges("chunk",     _dispatch_analyzers, _CATEGORY_NODES)

    for node in _CATEGORY_NODES:
        graph.add_edge(node, "aggregate")

    graph.add_edge("aggregate", END)

    return graph


async def get_checkpointer():
    """Create and initialise a PostgreSQL-backed LangGraph checkpointer."""
    from app.config import get_settings
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    settings = get_settings()
    # AsyncPostgresSaver needs a raw psycopg3 connection string (no SQLAlchemy prefix)
    raw_url = settings.database_url_sync.replace("postgresql+psycopg://", "postgresql://")
    checkpointer = AsyncPostgresSaver.from_conn_string(raw_url)
    await checkpointer.setup()
    return checkpointer


def compile_graph(checkpointer=None):
    graph = build_analysis_graph()

    compile_kwargs = {}
    if checkpointer:
        compile_kwargs["checkpointer"] = checkpointer

    compiled = graph.compile(**compile_kwargs)
    logger.info(
        "Analysis graph compiled (checkpointer=%s)",
        type(checkpointer).__name__ if checkpointer else "None",
    )
    return compiled
