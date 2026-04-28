"""Content acquisition node — scrape, parse, or receive text."""

from __future__ import annotations

import asyncio
import logging

from chonkie import SentenceChunker

from app.llm.factory import LLMFactory
from app.pipeline.state import AnalysisState
from app.pipeline.tokenizer import get_tokenizer_for_model
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

_ADAPTIVE_PROMPT_PREFIX = (
    "The previous attempt returned too little content. "
    "Please extract ALL legal text present, preserving every clause and sentence. "
    "Do not omit any legal language:\n\n"
)

_MAX_CLEAN_TOKENS = 50_000
_MAX_RETRIES = 3
_MIN_CONTENT_RATIO = 0.1


def _strip_noise(text: str) -> str:
    """Drop lines that are clearly UI chrome rather than document content."""
    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append(line)
            continue
        if len(stripped) < 30 and (stripped.isupper() or stripped.isdigit()):
            continue
        if stripped.lower() in (
            "accept", "accept all", "reject all", "cookie settings",
            "skip to content", "skip to main content", "back to top",
            "close", "menu", "search", "sign in", "log in", "sign up",
        ):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


async def _clean_chunk(llm, text: str, index: int) -> str:
    """Clean one chunk with up to _MAX_RETRIES attempts.

    On the first attempt uses a base prompt. If the output is too short
    (<10% of input) or the API call raises, subsequent attempts switch to
    an adaptive prompt that explicitly asks the model not to omit content.
    After all retries are exhausted the raw chunk is returned unchanged.
    """
    base_prompt = (
        f"Extract and return only the legal document text from the following:\n\n{text}"
    )
    adaptive_prompt = f"{_ADAPTIVE_PROMPT_PREFIX}{text}"

    use_adaptive = False
    for attempt in range(_MAX_RETRIES):
        prompt = adaptive_prompt if use_adaptive else base_prompt
        try:
            result = await llm.generate_text(
                prompt=prompt,
                system_prompt=_CLEANING_SYSTEM_PROMPT,
            )
            if len(result) >= len(text) * _MIN_CONTENT_RATIO:
                return result
            logger.warning(
                "Chunk %d attempt %d: output too short (%d chars vs %d expected), retrying",
                index, attempt + 1, len(result), int(len(text) * _MIN_CONTENT_RATIO),
            )
            use_adaptive = True
        except Exception as exc:
            logger.warning("Chunk %d attempt %d failed: %s", index, attempt + 1, exc)
            # use_adaptive stays False — model never responded, base prompt on retry

    logger.warning("Chunk %d: all retries exhausted, using raw chunk", index)
    return text


async def _clean_content_chunked(llm, content: str, model: str) -> str:
    """Chunk the full document and clean all chunks in parallel."""
    tokenizer_name = get_tokenizer_for_model(model)
    chunker = SentenceChunker(
        tokenizer=tokenizer_name,
        chunk_size=_MAX_CLEAN_TOKENS,
        chunk_overlap=0,
        min_sentences_per_chunk=1,
    )
    chunks = chunker.chunk(content)

    if not chunks:
        return content

    logger.info(
        "Cleaning %d chunk(s) in parallel (tokenizer=%s)", len(chunks), tokenizer_name
    )

    tasks = [_clean_chunk(llm, chunk.text, i) for i, chunk in enumerate(chunks)]
    cleaned_parts = await asyncio.gather(*tasks)
    return "\n\n".join(cleaned_parts)


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
            cleaned = await _clean_content_chunked(
                llm, content, model=state.get("llm_model") or ""
            )
        except Exception as exc:
            logger.warning("LLM cleaning failed, using raw content: %s", exc)
            cleaned = content

    return {
        "raw_content": content,
        "cleaned_content": cleaned,
        "status": "enriching",
    }
