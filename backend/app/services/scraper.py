from __future__ import annotations

import logging
import re
from typing import Optional

from scrapling.fetchers import Fetcher, StealthyFetcher

logger = logging.getLogger(__name__)

_MIN_CONTENT_LENGTH = 200


async def scrape_url(url: str, timeout: float = 30.0) -> dict:
    result = await _fast_fetch(url, timeout)
    if result["success"] and result["content"] and len(result["content"]) > _MIN_CONTENT_LENGTH:
        return result

    logger.info("Fast fetch insufficient for %s, trying StealthyFetcher...", url)
    result = await _stealth_fetch(url, timeout)
    if result["success"] and result["content"] and len(result["content"]) > _MIN_CONTENT_LENGTH:
        return result

    return {
        "success": False,
        "content": None,
        "title": None,
        "error": (
            "Could not extract content from this URL. "
            "Please copy-paste the text directly or upload the document."
        ),
    }


async def _fast_fetch(url: str, timeout: float) -> dict:
    """TLS-spoofing HTTP fetch — no browser, fast, handles most static pages."""
    try:
        page = Fetcher.get(url, timeout=int(timeout), stealthy_headers=True)
        title = _extract_title(page)
        content = _extract_legal_text(page)
        return {"success": True, "content": content, "title": title, "error": None}
    except Exception as exc:
        logger.warning("Fast fetch failed for %s: %s", url, exc)
        return {"success": False, "content": None, "title": None, "error": str(exc)}


async def _stealth_fetch(url: str, timeout: float) -> dict:
    """Full browser fetch with fingerprint spoofing — handles JS + anti-bot pages."""
    try:
        with StealthyFetcher(headless=True) as fetcher:
            page = fetcher.fetch(url, timeout=int(timeout * 1000))
        title = _extract_title(page)
        content = _extract_legal_text(page)
        return {"success": True, "content": content, "title": title, "error": None}
    except Exception as exc:
        logger.warning("Stealth fetch failed for %s: %s", url, exc)
        return {"success": False, "content": None, "title": None, "error": str(exc)}


def _extract_title(page) -> Optional[str]:
    title_el = page.css("title::text").get()
    if title_el:
        return title_el.strip()
    h1 = page.css("h1::text").get()
    if h1:
        return h1.strip()
    return None


def _extract_legal_text(page) -> str:
    # get_all_text strips script/style/nav/footer automatically
    text = page.get_all_text(
        ignore_tags=("script", "style", "noscript", "iframe", "nav", "header", "footer", "aside"),
        separator="\n",
    )
    return _clean_text(text)


def _clean_text(text: str) -> str:
    lines = text.split("\n")
    cleaned = [line.strip() for line in lines if len(line.strip()) > 2]
    text = "\n".join(cleaned)
    text = re.sub(r"\n{3,}", "\n\n", text)
    logger.info("Cleaned text  %s",  text[0:500])
    return text.strip()