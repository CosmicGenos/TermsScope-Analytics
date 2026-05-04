"""Corpus fetcher — downloads and cleans ToS texts to fixtures/raw/.

Each platform has multiple legal document URLs (ToS + Privacy Policy + billing
terms). This fetcher:
  1. Scrapes every URL using StealthyFetcher (full headless browser, fingerprint
     spoofed) — no fast-path fallback, since this is a one-time operation.
  2. Concatenates the pages with clear source separators.
  3. Runs each section through OpenAI gpt-4o-mini to strip scraping noise while
     preserving all legal clause text verbatim.
  4. Saves {slug}_raw.txt (pre-clean) and {slug}.txt (cleaned, used by eval).
"""

from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import logging
import re
import time
from pathlib import Path

import yaml
from openai import AsyncOpenAI
from scrapling.fetchers import StealthyFetcher

from app.config import get_settings
from evals.config import CORPUS, RAW_DIR, SOURCES_FILE, PlatformSpec

logger = logging.getLogger(__name__)

_CLEAN_SYSTEM = """\
You are a precise legal-document cleaner. You will receive raw text scraped from
a single legal web page (Terms of Service, Privacy Policy, or similar).

Your job:
- REMOVE: cookie consent banners, navigation menus, breadcrumbs, footer links,
  "last updated" date lines at the very top, social-share buttons, repetitive
  page-title headers, and any obvious scraping artefacts (e.g. repeated blank
  lines, stray punctuation lines, single-word orphan lines from nav elements).
- KEEP: every sentence and clause that is part of the legal document itself,
  exactly as written. Do NOT paraphrase, summarise, or reorder anything.
- Fix broken line wrapping where a sentence is split across multiple short lines
  due to HTML rendering — join those into proper paragraphs.
- Output ONLY the cleaned legal text. No commentary, no preamble, no markdown.
"""


def _extract_text(page) -> str:
    """Extract and minimally clean visible text from a Scrapling page object."""
    text = page.get_all_text(
        ignore_tags=("script", "style", "noscript", "iframe", "nav", "header", "footer", "aside"),
        separator="\n",
    )
    lines = [line.strip() for line in text.split("\n") if len(line.strip()) > 2]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _scrape_one_url(url: str, timeout: float = 90.0) -> str:
    """Synchronous StealthyFetcher scrape of a single URL. Returns extracted text."""
    with StealthyFetcher(headless=True) as fetcher:
        page = fetcher.fetch(url, timeout=int(timeout * 1000))
    return _extract_text(page)


async def _clean_section(client: AsyncOpenAI, url: str, raw_text: str) -> str:
    """Send one page's raw text to OpenAI for noise removal. Returns cleaned text."""
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _CLEAN_SYSTEM},
                {"role": "user", "content": raw_text},
            ],
            temperature=0.0,
            max_tokens=16000,
        )
        cleaned = response.choices[0].message.content or raw_text
        logger.info("  cleaned %s: %d → %d chars", url, len(raw_text), len(cleaned))
        return cleaned
    except Exception as exc:
        logger.warning("OpenAI cleaning failed for %s (%s) — using raw text", url, exc)
        return raw_text


async def fetch_one(spec: PlatformSpec, *, refresh: bool) -> dict:
    out_path = RAW_DIR / f"{spec.slug}.txt"
    if out_path.exists() and not refresh:
        text = out_path.read_text(encoding="utf-8")
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return {
            "slug": spec.slug,
            "urls": spec.urls,
            "sha256": sha,
            "length": len(text),
            "fetched_at": _stat_iso(out_path),
            "skipped": True,
        }

    settings = get_settings()
    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

    raw_sections: list[tuple[str, str]] = []   # (url, raw_text)
    for i, url in enumerate(spec.urls):
        logger.info("[%s] fetching %d/%d — %s", spec.slug, i + 1, len(spec.urls), url)
        try:
            raw = _scrape_one_url(url)
            raw_sections.append((url, raw))
            logger.info("  fetched %d chars", len(raw))
        except Exception as exc:
            logger.warning("  failed to fetch %s: %s", url, exc)
            raw_sections.append((url, f"[FETCH FAILED: {exc}]"))
        if i < len(spec.urls) - 1:
            time.sleep(3.0)   # polite pause between pages

    # save raw (pre-clean) for debugging
    raw_blob = "\n\n".join(
        f"===== SOURCE: {url} =====\n\n{text}" for url, text in raw_sections
    )
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / f"{spec.slug}_raw.txt").write_text(raw_blob, encoding="utf-8")

    # clean each section separately (keeps each well within gpt-4o-mini output limit)
    logger.info("[%s] cleaning %d sections with OpenAI...", spec.slug, len(raw_sections))
    cleaned_sections: list[str] = []
    for url, raw in raw_sections:
        cleaned = await _clean_section(openai_client, url, raw)
        cleaned_sections.append(f"===== SOURCE: {url} =====\n\n{cleaned}")

    final_text = "\n\n".join(cleaned_sections)
    out_path.write_text(final_text, encoding="utf-8")
    sha = hashlib.sha256(final_text.encode("utf-8")).hexdigest()

    return {
        "slug": spec.slug,
        "urls": spec.urls,
        "sha256": sha,
        "length": len(final_text),
        "raw_length": len(raw_blob),
        "fetched_at": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "skipped": False,
    }


def _stat_iso(p: Path) -> str:
    return dt.datetime.utcfromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds") + "Z"


async def fetch_corpus(specs: list[PlatformSpec] | None = None, *, refresh: bool = False) -> list[dict]:
    specs = specs or list(CORPUS)
    results: list[dict] = []
    for spec in specs:
        try:
            results.append(await fetch_one(spec, refresh=refresh))
        except Exception as exc:
            logger.error("Failed to fetch %s: %s", spec.slug, exc)
            results.append({"slug": spec.slug, "urls": spec.urls, "error": str(exc)})
    _write_sources_yaml(results)
    return results


def _write_sources_yaml(rows: list[dict]) -> None:
    SOURCES_FILE.parent.mkdir(parents=True, exist_ok=True)
    SOURCES_FILE.write_text(yaml.safe_dump(rows, sort_keys=False), encoding="utf-8")


def load_text(slug: str) -> str:
    path = RAW_DIR / f"{slug}.txt"
    if not path.exists():
        raise FileNotFoundError(
            f"Fixture missing for {slug}. Run `python -m evals.cli fetch-corpus` first."
        )
    return path.read_text(encoding="utf-8")


def doc_sha256(slug: str) -> str:
    return hashlib.sha256(load_text(slug).encode("utf-8")).hexdigest()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    asyncio.run(fetch_corpus())
