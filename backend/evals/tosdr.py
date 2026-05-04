"""ToSDR integration — fetch, cache, and format human-validated clause examples.

Fetches data from the public ToSDR API (no auth required) and caches responses
locally so repeated runs don't hit rate limits. The formatted output is injected
into the Pass 1 prompt as few-shot calibration examples.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import TypedDict

import httpx

from evals.config import TOSDR_CACHE_DIR

logger = logging.getLogger(__name__)

TOSDR_BASE = "https://api.tosdr.org"

# Maps ToSDR classification values to human-readable labels for the prompt
CLASSIFICATION_LABEL: dict[str, str] = {
    "good":    "POSITIVE — benefits the user",
    "neutral": "NEUTRAL  — industry-standard, no meaningful impact",
    "bad":     "NEGATIVE — limits or harms user rights",
    "alert":   "ALERT    — serious concern, read carefully",
    "blocker": "BLOCKER  — critical, consider avoiding this service",
}


class ToSDRPoint(TypedDict):
    title: str
    description: str
    classification: str   # good / neutral / bad / alert / blocker
    weight: int           # 0-100, higher = more important


class ToSDRData(TypedDict):
    slug: str
    name: str
    grade: str            # A / B / C / D / E
    service_id: int
    points: list[ToSDRPoint]


# ---------------------------------------------------------------------------
# Fetch + cache
# ---------------------------------------------------------------------------

def _cache_path(slug: str) -> Path:
    return TOSDR_CACHE_DIR / f"{slug}.json"


def _load_cache(slug: str) -> dict | None:
    p = _cache_path(slug)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def _save_cache(slug: str, data: dict) -> None:
    TOSDR_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(slug).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _search(query: str) -> list[dict]:
    resp = httpx.get(f"{TOSDR_BASE}/search/v4/", params={"query": query}, timeout=15)
    resp.raise_for_status()
    return resp.json().get("parameters", {}).get("services", [])


def _fetch_service(service_id: int) -> dict:
    resp = httpx.get(f"{TOSDR_BASE}/service/v3/", params={"id": service_id}, timeout=15)
    resp.raise_for_status()
    return resp.json()   # root IS the service object


def fetch_tosdr(slug: str, *, refresh: bool = False) -> ToSDRData | None:
    """Fetch ToSDR data for a platform slug.  Returns None if not found on ToSDR.

    Results are cached under evals/fixtures/tosdr_cache/{slug}.json.
    Pass refresh=True to force a fresh API call.
    """
    if not refresh:
        cached = _load_cache(slug)
        if cached:
            logger.info("tosdr: loaded %s from cache", slug)
            return cached  # type: ignore[return-value]

    logger.info("tosdr: searching API for '%s'", slug)
    try:
        hits = _search(slug)
    except httpx.HTTPStatusError as e:
        logger.warning("tosdr: search failed for %s (%s) — skipping", slug, e.response.status_code)
        return None

    if not hits:
        logger.warning("tosdr: no entry found for '%s'", slug)
        return None

    top = hits[0]
    service_id = top["id"]
    logger.info("tosdr: fetching service id=%s name=%s", service_id, top["name"])

    time.sleep(1.0)   # stay under rate limit between search and detail call

    try:
        raw = _fetch_service(service_id)
    except httpx.HTTPStatusError as e:
        logger.warning("tosdr: service fetch failed for %s (%s)", slug, e.response.status_code)
        return None

    data = _parse_service(slug, raw)
    _save_cache(slug, data)
    return data


def _parse_service(slug: str, raw: dict) -> ToSDRData:
    """Convert raw API response to our clean ToSDRData shape."""
    points: list[ToSDRPoint] = []
    for p in raw.get("points", []):
        case = p.get("case") or {}
        if not isinstance(case, dict):
            continue

        classification = case.get("classification", "").strip().lower()
        if not classification:
            continue   # skip points with no classification

        description = (case.get("description") or "").strip()
        title = (p.get("title") or case.get("title") or "").strip()
        weight = int(case.get("weight") or 0)

        if not title:
            continue

        points.append(ToSDRPoint(
            title=title,
            description=description,
            classification=classification,
            weight=weight,
        ))

    # Sort: most severe + highest weight first
    severity_order = {"blocker": 0, "alert": 1, "bad": 2, "neutral": 3, "good": 4}
    points.sort(key=lambda p: (severity_order.get(p["classification"], 5), -p["weight"]))

    return ToSDRData(
        slug=slug,
        name=raw.get("name", slug),
        grade=str(raw.get("rating") or "?"),
        service_id=int(raw.get("id", 0)),
        points=points,
    )


# ---------------------------------------------------------------------------
# Format for prompt injection
# ---------------------------------------------------------------------------

def format_examples_block(data: ToSDRData) -> str:
    """Return a prompt-ready string listing all human-validated examples.

    This is injected into the Pass 1 user prompt so the judge understands
    what classifications mean with real, service-specific examples.
    """
    if not data["points"]:
        return ""

    lines: list[str] = [
        f"Human reviewers graded this service: {data['grade']}",
        f"The following {len(data['points'])} clauses were validated by human reviewers for {data['name']}.",
        "Use them to calibrate your risk levels. Find ALL of these AND discover additional issues not listed here.",
        "",
    ]

    for p in data["points"]:
        label = CLASSIFICATION_LABEL.get(p["classification"], p["classification"].upper())
        lines.append(f"[{label}]")
        lines.append(f'  Title: "{p["title"]}"')
        if p["description"]:
            lines.append(f"  Why: {p['description']}")
        if p["weight"]:
            lines.append(f"  Severity weight: {p['weight']}/100")
        lines.append("")

    return "\n".join(lines)
