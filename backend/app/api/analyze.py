"""Analysis API endpoints — submit, stream, and retrieve analyses."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.auth.dependencies import get_current_user_optional
from app.config import get_settings
from app.db import get_db
from app.models.analysis import Analysis
from app.models.user import User
from app.pipeline.graph import compile_graph, get_checkpointer
from app.pipeline.state import AnalysisState
from app.schemas.input import AnalysisRequest, InputType
from app.services.cache import (
    compute_content_hash,
    get_cached_result,
    get_cached_url_hash,
    set_cached_result,
    set_url_hash_mapping,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["Analysis"])

# In-memory store for SSE streaming (analysis_id → events queue)
_analysis_streams: dict[str, asyncio.Queue] = {}


@router.post("")
async def create_analysis(
    request: AnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Submit a new ToS analysis.

    Accepts URL or text input. Returns the analysis ID for streaming results.
    """
    settings = get_settings()

    # Determine content for cache check
    content_for_hash = None
    if request.input_type == InputType.URL:
        url_str = str(request.url)
        # Check URL → hash cache first
        cached_hash = await get_cached_url_hash(url_str)
        if cached_hash:
            cached = await get_cached_result(cached_hash)
            if cached:
                analysis_id = str(uuid.uuid4())
                # Save to DB
                analysis = Analysis(
                    id=uuid.UUID(analysis_id),
                    user_id=current_user.id if current_user else None,
                    input_type=request.input_type.value,
                    input_url=url_str,
                    content_hash=cached_hash,
                    status="complete",
                    result=cached,
                )
                db.add(analysis)
                return {
                    "analysis_id": analysis_id,
                    "status": "complete",
                    "cached": True,
                    "result": cached,
                }

    elif request.input_type == InputType.TEXT:
        content_for_hash = request.text
        if content_for_hash:
            content_hash = compute_content_hash(content_for_hash)
            cached = await get_cached_result(content_hash)
            if cached:
                analysis_id = str(uuid.uuid4())
                analysis = Analysis(
                    id=uuid.UUID(analysis_id),
                    user_id=current_user.id if current_user else None,
                    input_type=request.input_type.value,
                    content_hash=content_hash,
                    status="complete",
                    result=cached,
                )
                db.add(analysis)
                return {
                    "analysis_id": analysis_id,
                    "status": "complete",
                    "cached": True,
                    "result": cached,
                }

    # No cache hit — create analysis and start pipeline
    analysis_id = str(uuid.uuid4())
    llm_provider = request.llm_provider or settings.default_llm_provider
    llm_model = request.llm_model or settings.default_llm_model

    analysis = Analysis(
        id=uuid.UUID(analysis_id),
        user_id=current_user.id if current_user else None,
        input_type=request.input_type.value,
        input_url=str(request.url) if request.url else None,
        content_hash="pending",
        status="acquiring",
        llm_provider=llm_provider,
        llm_model=llm_model,
    )
    db.add(analysis)
    await db.flush()  # Get the ID assigned

    # Create SSE stream queue for this analysis
    _analysis_streams[analysis_id] = asyncio.Queue()

    # Start the pipeline in the background
    asyncio.create_task(
        _run_pipeline(
            analysis_id=analysis_id,
            input_type=request.input_type.value,
            raw_input=str(request.url) if request.input_type == InputType.URL else (request.text or ""),
            llm_provider=llm_provider,
            llm_model=llm_model,
            user_id=str(current_user.id) if current_user else None,
        )
    )

    return {
        "analysis_id": analysis_id,
        "status": "acquiring",
        "cached": False,
    }


@router.post("/file")
async def create_analysis_from_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Submit a PDF file for analysis."""
    settings = get_settings()

    # Validate file
    if not file.filename:
        raise HTTPException(400, "No file provided.")

    if not file.filename.lower().endswith((".pdf", ".txt")):
        raise HTTPException(400, "Only PDF and TXT files are supported.")

    file_bytes = await file.read()
    if len(file_bytes) > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(400, f"File too large. Maximum size is {settings.max_file_size_mb}MB.")

    analysis_id = str(uuid.uuid4())
    llm_provider = settings.default_llm_provider
    llm_model = settings.default_llm_model

    analysis = Analysis(
        id=uuid.UUID(analysis_id),
        user_id=current_user.id if current_user else None,
        input_type="file",
        content_hash="pending",
        status="acquiring",
        llm_provider=llm_provider,
        llm_model=llm_model,
    )
    db.add(analysis)
    await db.flush()

    _analysis_streams[analysis_id] = asyncio.Queue()

    asyncio.create_task(
        _run_pipeline(
            analysis_id=analysis_id,
            input_type="file",
            raw_input=file.filename or "upload.pdf",
            llm_provider=llm_provider,
            llm_model=llm_model,
            user_id=str(current_user.id) if current_user else None,
            file_bytes=file_bytes,
        )
    )

    return {
        "analysis_id": analysis_id,
        "status": "acquiring",
        "cached": False,
    }


@router.get("/{analysis_id}/stream")
async def stream_analysis(analysis_id: str):
    """SSE endpoint that streams analysis progress and partial results."""

    async def  event_generator():
        queue = _analysis_streams.get(analysis_id)
        if not queue:
            yield {
                "event": "error",
                "data": json.dumps({"error": "Analysis not found or already completed."}),
            }
            return

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=120.0)
            except asyncio.TimeoutError:
                yield {"event": "keepalive", "data": "{}"}
                continue

            yield {"event": event["event"], "data": json.dumps(event["data"])}

            if event["event"] in ("complete", "error"):
                # Clean up
                _analysis_streams.pop(analysis_id, None)
                break

    return EventSourceResponse(event_generator())


@router.get("/{analysis_id}")
async def get_analysis(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a completed analysis result by ID."""
    try:
        uid = uuid.UUID(analysis_id)
    except ValueError:
        raise HTTPException(400, "Invalid analysis ID.")

    result = await db.execute(select(Analysis).where(Analysis.id == uid))
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(404, "Analysis not found.")

    return {
        "analysis_id": str(analysis.id),
        "status": analysis.status,
        "input_type": analysis.input_type,
        "input_url": analysis.input_url,
        "document_title": analysis.document_title,
        "result": analysis.result,
        "error": analysis.error_message,
        "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
    }


async def _run_pipeline(
    analysis_id: str,
    input_type: str,
    raw_input: str,
    llm_provider: str,
    llm_model: str,
    user_id: Optional[str] = None,
    file_bytes: Optional[bytes] = None,
) -> None:
    """Run the LangGraph pipeline in the background and stream events."""
    queue = _analysis_streams.get(analysis_id)
    if not queue:
        return

    try:
        # Emit start event
        await queue.put({
            "event": "status",
            "data": {"status": "acquiring", "message": "Fetching document...", "progress": 5},
        })

        # Build initial state
        initial_state: dict = {
            "input_type": input_type,
            "raw_input": raw_input,
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "status": "acquiring",
            "privacy_results": [],
            "financial_results": [],
            "data_rights_results": [],
            "cancellation_results": [],
            "liability_results": [],
        }

        logger.info("Initial state for analysis %s: %s", analysis_id, initial_state)
        
        if file_bytes:
            initial_state["file_bytes"] = file_bytes

        checkpointer = await get_checkpointer()
        graph = compile_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": analysis_id}}

        # Stream through graph nodes
        final_state = None
        async for event in graph.astream(initial_state, config, stream_mode="updates"):
            for node_name, node_output in event.items():
                current_status = node_output.get("status", "")
                error = node_output.get("error")

                if error:
                    await queue.put({
                        "event": "error",
                        "data": {"status": "error", "error": error},
                    })
                    # Update DB
                    await _update_analysis_db(analysis_id, "error", error_message=error)
                    return

                progress_map = {
                    "validating": 15,
                    "chunking": 25,
                    "aggregating": 85,
                    "complete": 100,
                }
                category_progress = {
                    "analyze_privacy":      35,
                    "analyze_financial":    45,
                    "analyze_data_rights":  55,
                    "analyze_cancellation": 65,
                    "analyze_liability":    75,
                }
                progress = progress_map.get(
                    current_status,
                    category_progress.get(node_name, 50),
                )

                message_map = {
                    "validating": "Validating document...",
                    "chunking": "Splitting into sections...",
                    "aggregating": "Compiling results...",
                    "complete": "Analysis complete!",
                }
                category_messages = {
                    "analyze_privacy":      "Analysing privacy clauses...",
                    "analyze_financial":    "Analysing financial clauses...",
                    "analyze_data_rights":  "Analysing data rights clauses...",
                    "analyze_cancellation": "Analysing cancellation clauses...",
                    "analyze_liability":    "Analysing liability clauses...",
                }
                message = message_map.get(
                    current_status,
                    category_messages.get(node_name, f"Processing ({node_name})..."),
                )

                await queue.put({
                    "event": "status",
                    "data": {"status": current_status, "message": message, "progress": progress},
                })

                final_state = node_output

        # If we reach here, pipeline completed
        if final_state and final_state.get("status") == "complete":
            result = final_state.get("final_result", {})
            content_hash = final_state.get("content_hash", "unknown")

            # Cache the result
            await set_cached_result(content_hash, result)

            # If URL input, also cache the URL → hash mapping
            if input_type == "url":
                await set_url_hash_mapping(raw_input, content_hash)

            # Update DB
            await _update_analysis_db(
                analysis_id,
                "complete",
                result=result,
                content_hash=content_hash,
                document_title=result.get("document_title"),
                token_count=final_state.get("token_count"),
            )

            await queue.put({
                "event": "complete",
                "data": {"status": "complete", "analysis_id": analysis_id, "result": result},
            })
        else:
            error_msg = "Pipeline ended without completion."
            await queue.put({
                "event": "error",
                "data": {"status": "error", "error": error_msg},
            })
            await _update_analysis_db(analysis_id, "error", error_message=error_msg)

    except Exception as exc:
        logger.exception("Pipeline error for analysis %s", analysis_id)
        error_msg = f"An unexpected error occurred: {str(exc)}"
        await queue.put({
            "event": "error",
            "data": {"status": "error", "error": error_msg},
        })
        await _update_analysis_db(analysis_id, "error", error_message=error_msg)


async def _update_analysis_db(
    analysis_id: str,
    status: str,
    result: Optional[dict] = None,
    error_message: Optional[str] = None,
    content_hash: Optional[str] = None,
    document_title: Optional[str] = None,
    token_count: Optional[int] = None,
) -> None:
    """Update the analysis record in the database."""
    from app.db import async_session_factory

    try:
        async with async_session_factory() as session:
            uid = uuid.UUID(analysis_id)
            stmt = select(Analysis).where(Analysis.id == uid)
            db_result = await session.execute(stmt)
            analysis = db_result.scalar_one_or_none()
            if analysis:
                analysis.status = status
                if result is not None:
                    analysis.result = result
                if error_message is not None:
                    analysis.error_message = error_message
                if content_hash is not None:
                    analysis.content_hash = content_hash
                if document_title is not None:
                    analysis.document_title = document_title
                if token_count is not None:
                    analysis.token_count = token_count
                await session.commit()
    except Exception as exc:
        logger.error("Failed to update analysis %s in DB: %s", analysis_id, exc)
