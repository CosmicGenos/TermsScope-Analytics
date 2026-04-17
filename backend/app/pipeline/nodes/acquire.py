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


async def acquire_content(state: AnalysisState) -> dict:
    """Acquire and clean the legal document text.

    Handles three input types: URL scraping, direct text, and PDF upload.
    Returns updated state keys.
    """
    input_type = state["input_type"]
    raw_input = state["raw_input"]

    logger.info("Acquiring content: type=%s", input_type)

    content = None
    title = None
    error = None

    if input_type == "url":
        result = await scrape_url(raw_input)
        if result["success"]:
            content = result["content"]
            title = result["title"]
        else:
            error = result["error"]

    elif input_type == "text":
        content = raw_input
        # Try to detect title from first line
        lines = raw_input.strip().split("\n")
        if lines and len(lines[0].strip()) < 200:
            title = lines[0].strip()

    elif input_type == "file":
        file_bytes = state.get("file_bytes")
        if file_bytes:
            result = await extract_text_from_pdf(file_bytes, raw_input)
            if result["success"]:
                content = result["content"]
                title = result["title"]
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

    # Clean content using LLM if it came from a URL (likely has noise)
    cleaned = content
    if input_type == "url" and len(content) > 500:
        try:
            llm = LLMFactory.create(
                provider=state.get("llm_provider"),
                model=state.get("llm_model"),
            )
            cleaned = await llm.generate_text(
                prompt=f"Extract and return only the legal document text from the following:\n\n{content[:50000]}",
                system_prompt=_CLEANING_SYSTEM_PROMPT,
            )
            if len(cleaned) < len(content) * 0.1:
                # LLM over-stripped; fall back to raw content
                cleaned = content
        except Exception as exc:
            logger.warning("LLM cleaning failed, using raw content: %s", exc)
            cleaned = content

    return {
        "raw_content": content,
        "cleaned_content": cleaned,
        "document_title": title,
        "status": "validating",
    }


# need fixes in filtering noise.