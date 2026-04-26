from __future__ import annotations

import logging

import tiktoken

from app.config import get_settings
from app.pipeline.state import AnalysisState
from app.pipeline.tokenizer import get_tokenizer_for_model
from app.services.cache import compute_content_hash

logger = logging.getLogger(__name__)


async def validate_content(state: AnalysisState) -> dict:
    """Validate the acquired content.

    Checks:
    - Content is not empty
    - Token count is within the allowed limit (100K)
    - Computes content hash for caching
    """
    settings = get_settings()
    content = state.get("cleaned_content", "")

    if not content or len(content.strip()) < 50:
        return {
            "status": "error",
            "error": "The extracted content is too short to analyse. Please provide a longer document.",
            "token_count": 0,
        }

    # Use the tokenizer that matches the active LLM model
    encoding_name = get_tokenizer_for_model(state.get("llm_model", ""))
    try:
        enc = tiktoken.get_encoding(encoding_name)
        token_count = len(enc.encode(content))
    except Exception:
        token_count = len(content) // 4

    logger.info(
        "Content validated: %d tokens (%d chars) using %s encoding",
        token_count, len(content), encoding_name,
    )

    if token_count > settings.max_token_limit:
        return {
            "status": "error",
            "error": (
                f"Document is too long ({token_count:,} tokens). "
                f"Maximum allowed is {settings.max_token_limit:,} tokens. "
                "Please provide a shorter document or extract the relevant sections."
            ),
            "token_count": token_count,
        }

    content_hash = compute_content_hash(content)

    return {
        "token_count": token_count,
        "content_hash": content_hash,
        "status": "chunking",
    }
