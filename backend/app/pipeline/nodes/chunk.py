"""Chunking node — split cleaned content into 20k-token chunks."""

from __future__ import annotations

import logging

from chonkie import SentenceChunker

from app.pipeline.state import AnalysisState
from app.pipeline.tokenizer import get_tokenizer_for_model

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 20_000
_SKIP_CHUNKING_CHARS = 12_000  # ~3k tokens — short docs skip chunking entirely


async def chunk_content(state: AnalysisState) -> dict:
    """Split cleaned content into 20k-token sentence-aware chunks.

    Short documents (under ~3k tokens) are returned as a single chunk without
    going through the chunker.  All chunks are passed to every category analyzer
    node — no keyword routing.
    """
    content = state.get("cleaned_content", "")
    tokenizer = get_tokenizer_for_model(state.get("llm_model", ""))

    if len(content) < _SKIP_CHUNKING_CHARS:
        logger.info("Content is short (%d chars), using as single chunk", len(content))
        return {"chunks": [content], "status": "analyzing"}

    try:
        chunker = SentenceChunker(
            tokenizer=tokenizer,
            chunk_size=_CHUNK_SIZE,
            chunk_overlap=0,
            min_sentences_per_chunk=1,
        )
        chunk_objects = chunker.chunk(content)
        chunks = [c.text for c in chunk_objects if c.text.strip()]
        if not chunks:
            chunks = [content]
        logger.info("Chunked into %d x 20k-token chunks (tokenizer=%s)", len(chunks), tokenizer)
    except Exception as exc:
        logger.warning("Chunking failed (%s), using full content as single chunk", exc)
        chunks = [content]

    return {"chunks": chunks, "status": "analyzing"}
