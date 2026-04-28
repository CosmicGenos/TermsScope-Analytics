"""System prompts and user-prompt builders for the document enrichment node."""

from __future__ import annotations

# Only the first portion of the document is needed for metadata / structure.
_ENRICH_EXCERPT_CHARS = 50000 # ~10k tokens, should cover all metadata and section headings in most docs

METADATA_SYSTEM_PROMPT = """\
You are a legal document metadata extractor.
Extract structured metadata from the provided legal document text.
Focus on factual extraction only — do not analyse or summarise the content.
If a field cannot be determined from the text, return null for that field."""

STRUCTURE_SYSTEM_PROMPT = """\
You are a document structure analyst.
Identify the top-level section headings of the provided legal document in document order.
Focus on main sections only — do not include sub-sections.
Return at most 30 sections."""

QUALITY_SYSTEM_PROMPT = """\
You are a document quality assessor.
Evaluate whether the provided text is a legitimate legal agreement and how complete it appears.
Be strict: a random webpage, blog post, marketing copy, or partial snippet is NOT a legal document."""


def build_metadata_prompt(content: str) -> str:
    excerpt = content[:_ENRICH_EXCERPT_CHARS]
    return f"""Extract metadata from this legal document.

---
{excerpt}
---

Extract the following from the text above:
- company_name: the company or organisation name (e.g. "Meta Platforms, Inc.") — null if not clearly stated
- document_type: one of "Terms of Service", "Privacy Policy", "EULA", "Data Processing Agreement", "Cookie Policy", "Acceptable Use Policy", "Other"
- effective_date: the date the document takes effect (e.g. "January 1, 2025") — null if not found
- last_updated: the last-updated date — null if not found
- version: document version string (e.g. "v2.3") — null if not found
- jurisdiction: the governing-law location (e.g. "California, USA") — null if not found
- document_language: ISO 639-1 language code (e.g. "en")"""


def build_structure_prompt(content: str) -> str:
    excerpt = content[:_ENRICH_EXCERPT_CHARS]
    return f"""Identify the section structure of this legal document.

---
{excerpt}
---

List every major section heading you can identify, in document order.
For each section provide:
- title: the section heading exactly as it appears
- start_hint: the first 60 characters of content that appears directly under that heading (used to locate the section in the full text)

Also determine:
- has_subsections: true if the document uses sub-sections (e.g. 1.1, 1.2, Article I.A)
- structure_type: one of:
  "numbered"  — sections are numbered (1., 2., 3. …)
  "titled"    — sections use distinct heading text (ALL CAPS, bold headers, etc.)
  "article"   — sections use "Article I", "Article II" style
  "flat"      — no discernible section structure (wall of text)"""


def build_quality_prompt(content: str) -> str:
    excerpt = content[:_ENRICH_EXCERPT_CHARS]
    return f"""Assess the quality of this text as a legal document.

---
{excerpt}
---

Determine:
- is_legal_document: true ONLY if this is clearly a Terms of Service, Privacy Policy, EULA, or similar legal agreement — false for blog posts, articles, or random web pages
- completeness_score: integer 0-100 (100 = all standard sections present and readable, 0 = near-empty or garbage text)
- estimated_reading_time_minutes: estimated minutes to read the full document at 200 words per minute
- contains_amendments: true if the document explicitly references amendments or modifications
- quality_notes: a single sentence describing document quality or any notable issues (e.g. "Complete privacy policy with GDPR section", "Document appears truncated after section 4")"""
