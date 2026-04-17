"""Web scraping service for extracting ToS / legal text from URLs."""

from __future__ import annotations

import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Tags likely to contain the main legal content
_CONTENT_TAGS = ["article", "main", "section", "div"]
_LEGAL_KEYWORDS = [
    "terms", "privacy", "policy", "agreement", "license",
    "conditions", "service", "legal", "cookie",
]

# Noise elements to strip before extraction
_NOISE_SELECTORS = [
    "nav", "header", "footer", "aside",
    "script", "style", "noscript", "iframe",
    ".navbar", ".footer", ".sidebar", ".cookie-banner",
    "#cookie-banner", "#nav", "#header", "#footer",
]


async def scrape_url(url: str, timeout: float = 30.0) -> dict:
    """Scrape legal text from a URL.

    Returns
    -------
    dict
        {"success": bool, "content": str | None, "title": str | None, "error": str | None}
    """
    # Step 1: Try static fetch via httpx
    result = await _static_fetch(url, timeout)
    if result["success"] and result["content"] and len(result["content"]) > 200:
        return result

    # Step 2: Fallback to Playwright for JS-rendered pages
    logger.info("Static fetch insufficient for %s, trying Playwright...", url)
    result = await _playwright_fetch(url, timeout)
    if result["success"] and result["content"] and len(result["content"]) > 200:
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


async def _static_fetch(url: str, timeout: float) -> dict:
    """Fetch and parse a page using httpx + BeautifulSoup (no JS)."""
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": "TermsScope-Analyzer/1.0"},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        title = _extract_title(soup)
        content = _extract_legal_text(soup)

        return {
            "success": True,
            "content": content,
            "title": title,
            "error": None,
        }
    except Exception as exc:
        logger.warning("Static fetch failed for %s: %s", url, exc)
        return {"success": False, "content": None, "title": None, "error": str(exc)}


async def _playwright_fetch(url: str, timeout: float) -> dict:
    """Fetch a JS-rendered page using Playwright."""
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle", timeout=int(timeout * 1000))
            html = await page.content()
            await browser.close()

        soup = BeautifulSoup(html, "lxml")
        title = _extract_title(soup)
        content = _extract_legal_text(soup)

        return {
            "success": True,
            "content": content,
            "title": title,
            "error": None,
        }
    except Exception as exc:
        logger.warning("Playwright fetch failed for %s: %s", url, exc)
        return {"success": False, "content": None, "title": None, "error": str(exc)}


def _extract_title(soup: BeautifulSoup) -> Optional[str]:
    """Try to extract the document title."""
    # Check <title> tag
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    # Check first <h1>
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return None


def _extract_legal_text(soup: BeautifulSoup) -> str:
    """Extract the main legal/ToS text from parsed HTML.

    Strategy:
    1. Remove noise elements (nav, footer, scripts, etc.)
    2. Try to find a container with legal keywords in id/class
    3. Fall back to largest text block
    """
    # Remove noise
    for selector in _NOISE_SELECTORS:
        for tag in soup.select(selector):
            tag.decompose()

    # Strategy 1: Find a container with legal keywords in id or class
    for tag in _CONTENT_TAGS:
        for el in soup.find_all(tag):
            attrs_text = " ".join(
                str(v) for v in (el.get("id", ""), " ".join(el.get("class", [])))
            ).lower()
            if any(kw in attrs_text for kw in _LEGAL_KEYWORDS):
                text = el.get_text(separator="\n", strip=True)
                if len(text) > 500:
                    return _clean_text(text)

    # Strategy 2: Get the largest text block from body
    body = soup.find("body")
    if body:
        text = body.get_text(separator="\n", strip=True)
        return _clean_text(text)

    # Fallback
    return _clean_text(soup.get_text(separator="\n", strip=True))


def _clean_text(text: str) -> str:
    """Normalize whitespace and remove very short lines."""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        line = line.strip()
        if len(line) > 2:  # Skip empty / tiny lines
            cleaned.append(line)
    text = "\n".join(cleaned)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
