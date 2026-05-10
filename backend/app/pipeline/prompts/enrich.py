"""System prompts and user-prompt builders for the document enrichment node."""

from __future__ import annotations

_ENRICH_EXCERPT_CHARS = 10000

ENRICH_SYSTEM_PROMPT = """\
You are a legal document analyser.
Extract structured metadata and assess document quality from the provided legal document text.
Focus on factual extraction only — do not analyse or summarise the content beyond what is asked.
If a metadata field cannot be determined from the text, return null for that field.
Be strict on quality: a random webpage, blog post, marketing copy, or partial snippet is NOT a legal document."""


def build_enrich_prompt(content: str) -> str:
    excerpt = content[:_ENRICH_EXCERPT_CHARS]
    return f"""Analyse this legal document excerpt.

---
{excerpt}
---

Extract the following metadata:
- company_name: the company or organisation name (e.g. "Meta Platforms, Inc.") — null if not clearly stated
- document_type: one of "Terms of Service", "Privacy Policy", "EULA", "Data Processing Agreement", "Cookie Policy", "Acceptable Use Policy", "Other"
- effective_date: the date the document takes effect (e.g. "January 1, 2025") — null if not found
- last_updated: the last-updated date — null if not found
- version: document version string (e.g. "v2.3") — null if not found
- jurisdiction: the governing-law location (e.g. "California, USA") — null if not found
- document_language: ISO 639-1 language code (e.g. "en")

Also assess quality:
- is_legal_document: true ONLY if this is clearly a Terms of Service, Privacy Policy, EULA, or similar legal agreement — false for blog posts, articles, or random web pages
- completeness_score: integer 0-100 (100 = all standard sections present and readable, 0 = near-empty or garbage text)
- estimated_reading_time_minutes: estimated minutes to read the full document at 200 words per minute
- contains_amendments: true if the document explicitly references amendments or modifications
- quality_notes: a single sentence describing document quality or any notable issues"""
