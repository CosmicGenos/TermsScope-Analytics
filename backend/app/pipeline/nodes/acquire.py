"""Content acquisition node — scrape, parse, or receive text."""

from __future__ import annotations

import logging

from app.llm.factory import LLMFactory
from app.pipeline.state import AnalysisState
from app.services.pdf_parser import extract_text_from_pdf
from app.services.scraper import scrape_url

logger = logging.getLogger(__name__)

_CLEANING_SYSTEM_PROMPT = """\
You are a legal document extractor. You will receive raw text that was scraped \
from a webpage. Your job is to extract ONLY the Terms of Service, Privacy Policy, \
or legal agreement text. Remove all navigation elements, advertisements, cookie \
notices, and unrelated content. Return the cleaned legal text as-is without \
summarising or modifying the legal language. If the text does not appear to \
contain any legal document, return the text as-is."""


def _strip_noise(text: str) -> str:
    """Drop lines that are clearly UI chrome rather than document content."""
    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append(line)
            continue
        # Skip very short lines that are all-caps or purely numeric (nav items, page numbers)
        if len(stripped) < 30 and (stripped.isupper() or stripped.isdigit()):
            continue
        # Skip common web chrome patterns
        if stripped.lower() in (
            "accept", "accept all", "reject all", "cookie settings",
            "skip to content", "skip to main content", "back to top",
            "close", "menu", "search", "sign in", "log in", "sign up",
        ):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


async def acquire_content(state: AnalysisState) -> dict:
    """Acquire and clean the legal document text.

    Handles three input types: URL scraping, direct text, and PDF upload.
    If pre_extracted_content is set in state (file uploads that already ran
    PDF extraction for cache checking), that content is used directly.
    """
    input_type = state["input_type"]
    raw_input = state["raw_input"]

    logger.info("Acquiring content: type=%s", input_type)

    content = None
    error = None

    # Fast path: API layer already extracted PDF content for cache checking
    pre_extracted = state.get("pre_extracted_content")
    if pre_extracted:
        logger.info("Using pre-extracted content (%d chars)", len(pre_extracted))
        content = pre_extracted

    elif input_type == "url":
        result = await scrape_url(raw_input)
        if result["success"]:
            content = result["content"]
        else:
            error = result["error"]

    elif input_type == "text":
        content = raw_input

    elif input_type == "file":
        file_bytes = state.get("file_bytes")
        if file_bytes:
            result = await extract_text_from_pdf(file_bytes, raw_input)
            if result["success"]:
                content = result["content"]
            else:
                error = result["error"]
        else:
            error = "No file content provided."

    if error or not content:
        return {
            "status": "error",
            "error": error or "No content could be extracted.",
            "raw_content": "",
            "cleaned_content": "",
        }

    content = _strip_noise(content)

    # LLM cleaning pass for URL content (removes residual web noise)
    cleaned = content
    if input_type == "url" and len(content) > 500:
        try:
            llm = LLMFactory.create(
                provider=state.get("llm_provider"),
                model=state.get("llm_model"),
            )
            _MAX_CLEAN_CHARS = 50_000
            if len(content) > _MAX_CLEAN_CHARS:
                truncated = content[:_MAX_CLEAN_CHARS]
                last_break = max(truncated.rfind(". "), truncated.rfind(".\n"))
                if last_break > _MAX_CLEAN_CHARS * 0.8:
                    truncated = truncated[:last_break + 1]
            else:
                truncated = content

            cleaned = await llm.generate_text(
                prompt=f"Extract and return only the legal document text from the following:\n\n{truncated}",
                system_prompt=_CLEANING_SYSTEM_PROMPT,
            )
            if len(cleaned) < len(content) * 0.1:
                cleaned = content
        except Exception as exc:
            logger.warning("LLM cleaning failed, using raw content: %s", exc)
            cleaned = content

    return {
        "raw_content": content,
        "cleaned_content": cleaned,
        "status": "enriching",
    }
