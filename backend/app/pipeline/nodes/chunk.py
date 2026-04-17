"""Chunking node — split long documents using Chonkie SentenceChunker."""

from __future__ import annotations

import logging

from app.pipeline.state import AnalysisState

logger = logging.getLogger(__name__)

# Threshold: skip chunking for short documents
_SKIP_CHUNKING_CHARS = 12_000  # ~3K tokens


async def chunk_content(state: AnalysisState) -> dict:
    """Split the cleaned content into manageable chunks.

    Uses Chonkie SentenceChunker for sentence-aware splitting.
    Short documents (< ~3K tokens) bypass chunking entirely.
    """
    content = state.get("cleaned_content", "")

    if len(content) < _SKIP_CHUNKING_CHARS:
        logger.info("Content is short (%d chars), skipping chunking", len(content))
        return {
            "chunks": [content],
            "status": "analyzing",
        }

    try:
        from chonkie import SentenceChunker

        chunker = SentenceChunker(
            tokenizer="gpt2",
            chunk_size=4096,
            chunk_overlap=256,
            min_sentences_per_chunk=2,
        )

        chunk_objects = chunker.chunk(content)
        chunks = [c.text for c in chunk_objects if c.text.strip()]

        logger.info("Content chunked into %d pieces (from %d chars)", len(chunks), len(content))

        if not chunks:
            chunks = [content]

    except Exception as exc:
        logger.warning("Chunking failed (%s), using full content as single chunk", exc)
        chunks = [content]

    return {
        "chunks": chunks,
        "status": "analyzing",
    }
