from __future__ import annotations

import logging

import tiktoken

from app.config import get_settings
from app.pipeline.state import AnalysisState
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

    try:
        enc = tiktoken.get_encoding("cl100k_base")
        token_count = len(enc.encode(content))
    except Exception:

        token_count = len(content) // 4

    logger.info("Content validated: %d tokens (%d characters)", token_count, len(content))

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
