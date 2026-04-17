from __future__ import annotations

import hashlib
import json
import logging
from typing import Optional

from app.config import get_settings
from app.db.redis import get_redis

logger = logging.getLogger(__name__)


def compute_content_hash(content: str) -> str:
    normalised = " ".join(content.lower().split())
    return hashlib.sha256(normalised.encode()).hexdigest()


async def get_cached_result(content_hash: str) -> Optional[dict]:
    try:
        redis = await get_redis()
        key = f"analysis:{content_hash}"
        raw = await redis.get(key)
        if raw:
            logger.info("Cache HIT for hash %s…", content_hash[:12])
            return json.loads(raw)
        logger.debug("Cache MISS for hash %s…", content_hash[:12])
        return None
    except Exception as exc:
        logger.warning("Cache read error: %s", exc)
        return None


async def set_cached_result(content_hash: str, result: dict) -> None:
    """Store an analysis result in the cache."""
    try:
        settings = get_settings()
        redis = await get_redis()
        key = f"analysis:{content_hash}"
        await redis.set(key, json.dumps(result), ex=settings.cache_ttl_seconds)
        logger.info("Cached result for hash %s… (TTL=%ds)", content_hash[:12], settings.cache_ttl_seconds)
    except Exception as exc:
        logger.warning("Cache write error: %s", exc)


async def get_cached_url_hash(url: str) -> Optional[str]:
    """Look up a URL → content-hash mapping (short TTL)."""
    try:
        redis = await get_redis()
        key = f"url_hash:{hashlib.sha256(url.encode()).hexdigest()}"
        return await redis.get(key)
    except Exception:
        return None


async def set_url_hash_mapping(url: str, content_hash: str) -> None:
    """Store a URL → content-hash mapping with 1 hour TTL."""
    try:
        redis = await get_redis()
        key = f"url_hash:{hashlib.sha256(url.encode()).hexdigest()}"
        await redis.set(key, content_hash, ex=3600)
    except Exception as exc:
        logger.warning("URL hash mapping error: %s", exc)
