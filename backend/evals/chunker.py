"""Document chunking for eval pass 1.

Uses chonkie's SentenceChunker with the same tiktoken encoding the judge model
uses, so chunk_size=20_000 means 20k *model tokens*, not characters.
No overlap — each chunk is independent input to the judge.
"""

from __future__ import annotations

import logging

from chonkie import SentenceChunker

from app.pipeline.tokenizer import get_tokenizer_for_model

logger = logging.getLogger(__name__)


def chunk_document(text: str, model: str, chunk_size: int = 20_000) -> list[str]:
    """Split *text* into chunks of at most *chunk_size* tokens.

    Returns a list of chunk strings. If the whole document fits in one chunk,
    returns a single-element list so callers don't need a special case.
    """
    encoding_name = get_tokenizer_for_model(model)
    chunker = SentenceChunker(
        tokenizer=encoding_name,
        chunk_size=chunk_size,
        chunk_overlap=0,
        min_sentences_per_chunk=1,
    )
    chunks = chunker.chunk(text)
    texts = [c.text for c in chunks if c.text.strip()]
    logger.info(
        "chunker: model=%s encoding=%s doc=%d chars → %d chunk(s)",
        model, encoding_name, len(text), len(texts),
    )
    return texts
