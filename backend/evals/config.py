"""Configuration for the eval harness — judge model, corpus, paths."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

EVALS_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = EVALS_DIR / "fixtures"
RAW_DIR = FIXTURES_DIR / "raw"
SOURCES_FILE = FIXTURES_DIR / "sources.yaml"
TOSDR_CACHE_DIR = FIXTURES_DIR / "tosdr_cache"    # cached ToSDR API responses per platform
GROUND_TRUTH_DIR = FIXTURES_DIR / "ground_truth"  # human-validated AnalysisResult JSONs
CACHE_DIR = EVALS_DIR / "cache"
EMBEDDINGS_DB = CACHE_DIR / "embeddings.sqlite"
PASS_CACHE_DIR = CACHE_DIR / "passes"
REPORTS_DIR = EVALS_DIR.parent.parent / "reports" / "runs"


@dataclass(frozen=True)
class PlatformSpec:
    slug: str
    name: str
    urls: list[str]          # all relevant legal document URLs for this platform
    note: str = ""

    @property
    def url(self) -> str:    # backward-compat: primary URL
        return self.urls[0]


@dataclass(frozen=True)
class JudgeConfig:
    judge_provider: Literal["claude", "openai"] = "claude"
    judge_model: str = "claude-sonnet-4-5-20250929"
    embedding_model: str = "text-embedding-3-small"
    match_threshold: float = 0.75
    temperature: float = 0.0
    max_clauses_per_doc: int = 200
    seed: int = 42


CORPUS: list[PlatformSpec] = [
    PlatformSpec(
        slug="discord",
        name="Discord",
        urls=[
            "https://discord.com/terms",
            "https://discord.com/privacy",
            "https://discord.com/terms/paid-services-terms",
        ],
        note="Concise legal style",
    ),
    PlatformSpec(
        slug="spotify",
        name="Spotify",
        urls=[
            "https://www.spotify.com/us/legal/end-user-agreement/",
            "https://www.spotify.com/us/legal/privacy-policy/",
            "https://www.spotify.com/us/legal/paid-subscription-terms/",
        ],
        note="Subscription billing heavy",
    ),
    PlatformSpec(
        slug="openai",
        name="OpenAI",
        urls=[
            "https://openai.com/policies/terms-of-use/",
            "https://openai.com/policies/privacy-policy/",
        ],
        note="AI-specific clauses",
    ),
    PlatformSpec(
        slug="reddit",
        name="Reddit",
        urls=[
            "https://www.redditinc.com/policies/user-agreement",
            "https://www.reddit.com/policies/privacy-policy",
        ],
        note="UGC content licensing",
    ),
    PlatformSpec(
        slug="netflix",
        name="Netflix",
        urls=[
            "https://help.netflix.com/legal/termsofuse",
            "https://help.netflix.com/legal/privacy",
        ],
        note="Auto-renewal & cancellation",
    ),
    PlatformSpec(
        slug="github",
        name="GitHub",
        urls=[
            "https://docs.github.com/en/site-policy/github-terms/github-terms-of-service",
            "https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement",
        ],
        note="Developer-friendly tone",
    ),
    PlatformSpec(
        slug="notion",
        name="Notion",
        urls=[
            "https://www.notion.so/terms",
            "https://www.notion.com/trust/privacy-policy",
        ],
        note="SaaS data clauses",
    ),
    PlatformSpec(
        slug="substack",
        name="Substack",
        urls=[
            "https://substack.com/tos",
            "https://substack.com/privacy",
        ],
        note="Creator payouts",
    ),
]


def get_platform(slug: str) -> PlatformSpec:
    for p in CORPUS:
        if p.slug == slug:
            return p
    raise KeyError(f"Unknown platform slug: {slug}. Known: {[p.slug for p in CORPUS]}")


def select_platforms(slugs: list[str] | None) -> list[PlatformSpec]:
    if not slugs or slugs == ["all"]:
        return list(CORPUS)
    return [get_platform(s) for s in slugs]
