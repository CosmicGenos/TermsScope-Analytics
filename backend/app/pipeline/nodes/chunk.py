"""Chunking node — section-aware splitting with per-chunk category mapping."""

from __future__ import annotations

import logging
from typing import Optional

from app.pipeline.state import AnalysisState
from app.pipeline.tokenizer import get_tokenizer_for_model

logger = logging.getLogger(__name__)

_SKIP_CHUNKING_CHARS = 12_000   # ~3K tokens — short docs bypass chunking
_CHUNK_SIZE = 2048              # target tokens per chunk
_CHUNK_OVERLAP = 128            # overlap tokens between adjacent chunks
_FALLBACK_CHUNK_SIZE = 5120     # larger chunks when no section structure found

# Keywords used to map chunks to analysis categories
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "privacy": [
        "privacy", "personal data", "personal information", "cookie", "tracking",
        "gdpr", "ccpa", "consent", "data collection", "data retention", "biometric",
    ],
    "financial": [
        "payment", "billing", "subscription", "fee", "refund", "price", "charge",
        "invoice", "auto-renew", "auto renewal", "trial", "free trial", "currency",
    ],
    "data_rights": [
        "license", "user content", "intellectual property", "ownership", "copyright",
        "ip rights", "portability", "export", "content you post", "content license",
    ],
    "cancellation": [
        "terminat", "cancell", "account closure", "suspend", "deactivat",
        "inactive", "deletion of account", "close your account", "discontinue",
    ],
    "liability": [
        "liability", "indemnif", "arbitration", "dispute", "warranty",
        "limitation of liability", "class action", "governing law", "as-is",
    ],
}


def _build_category_map(chunks: list[str]) -> dict[int, list[str]]:
    """Return {chunk_index: [relevant_categories]} based on keyword scanning."""
    result: dict[int, list[str]] = {}
    all_cats = list(_CATEGORY_KEYWORDS.keys())
    for idx, chunk in enumerate(chunks):
        text_lower = chunk.lower()
        relevant = [
            cat for cat, keywords in _CATEGORY_KEYWORDS.items()
            if any(kw in text_lower for kw in keywords)
        ]
        # Fall back to all categories if no keywords matched
        result[idx] = relevant if relevant else all_cats
    return result


def _standard_chunk(content: str, tokenizer: str, chunk_size: int) -> list[str]:
    """Plain sentence-aware chunking — no section awareness."""
    from chonkie import SentenceChunker

    chunker = SentenceChunker(
        tokenizer=tokenizer,
        chunk_size=chunk_size,
        chunk_overlap=_CHUNK_OVERLAP,
        min_sentences_per_chunk=2,
    )
    chunk_objects = chunker.chunk(content)
    chunks = [c.text for c in chunk_objects if c.text.strip()]
    return chunks if chunks else [content]


def _section_aware_chunk(
    content: str,
    document_structure: dict,
    tokenizer: str,
) -> Optional[list[str]]:
    """Split document at LLM-identified section boundaries.

    Each chunk is prefixed with its section title so analyzers always know
    which section they are reading.  Returns None if section positions cannot
    be reliably located (caller should fall back to standard chunking).
    """
    sections_data = document_structure.get("sections", [])
    structure_type = document_structure.get("structure_type", "flat")

    if structure_type == "flat" or len(sections_data) < 3:
        return None

    # Locate each section in the actual text using start_hint
    section_positions: list[tuple[str, int]] = []
    for sec in sections_data:
        hint = (sec.get("start_hint") or "")[:40].strip()
        if not hint:
            continue
        pos = content.find(hint)
        if pos >= 0:
            section_positions.append((sec["title"], pos))

    if len(section_positions) < 3:
        return None  # Too few sections found — fallback

    section_positions.sort(key=lambda x: x[1])

    # Slice text into per-section strings
    section_texts: list[tuple[str, str]] = []
    for i, (title, start_pos) in enumerate(section_positions):
        end_pos = section_positions[i + 1][1] if i + 1 < len(section_positions) else len(content)
        section_text = content[start_pos:end_pos].strip()
        if section_text:
            section_texts.append((title, section_text))

    if not section_texts:
        return None

    chunks: list[str] = []
    for title, text in section_texts:
        prefix = f"[Section: {title}]\n\n"
        # Rough token estimate (4 chars ≈ 1 token)
        approx_tokens = len(text) // 4

        if approx_tokens <= _CHUNK_SIZE:
            chunks.append(prefix + text)
        else:
            # Sub-chunk oversized sections; each sub-chunk keeps the section prefix
            from chonkie import SentenceChunker

            chunker = SentenceChunker(
                tokenizer=tokenizer,
                chunk_size=_CHUNK_SIZE,
                chunk_overlap=_CHUNK_OVERLAP,
                min_sentences_per_chunk=2,
            )
            sub_chunks = chunker.chunk(text)
            for sub in sub_chunks:
                if sub.text.strip():
                    chunks.append(prefix + sub.text)

    return chunks if chunks else None


async def chunk_content(state: AnalysisState) -> dict:
    """Split the cleaned content into manageable chunks.

    Strategy (in order of preference):
    1. Section-aware: split at LLM-identified section boundaries, prefix each
       chunk with its section title.
    2. Standard: plain SentenceChunker with a larger chunk_size.
    3. Single chunk: for very short documents or on any exception.

    Also builds chunk_category_map to let each analyzer skip irrelevant chunks.
    """
    content = state.get("cleaned_content", "")
    tokenizer = get_tokenizer_for_model(state.get("llm_model", ""))

    if len(content) < _SKIP_CHUNKING_CHARS:
        logger.info("Content is short (%d chars), skipping chunking", len(content))
        chunks = [content]
        return {
            "chunks": chunks,
            "chunk_category_map": _build_category_map(chunks),
            "status": "analyzing",
        }

    try:
        document_structure = state.get("document_structure") or {}
        chunks = None

        # Attempt section-aware chunking first
        if document_structure:
            chunks = _section_aware_chunk(content, document_structure, tokenizer)
            if chunks:
                logger.info(
                    "Section-aware chunking: %d chunks (structure_type=%s)",
                    len(chunks),
                    document_structure.get("structure_type", "unknown"),
                )

        # Fallback: standard sentence chunking
        if not chunks:
            logger.info("Falling back to standard chunking (tokenizer=%s)", tokenizer)
            chunks = _standard_chunk(content, tokenizer, _FALLBACK_CHUNK_SIZE)
            logger.info("Standard chunking: %d chunks from %d chars", len(chunks), len(content))

    except Exception as exc:
        logger.warning("Chunking failed (%s), using full content as single chunk", exc)
        chunks = [content]

    chunk_category_map = _build_category_map(chunks)
    logger.info(
        "Chunk category map built: %d chunks, avg %.1f categories/chunk",
        len(chunks),
        sum(len(v) for v in chunk_category_map.values()) / max(len(chunks), 1),
    )

    return {
        "chunks": chunks,
        "chunk_category_map": chunk_category_map,
        "status": "analyzing",
    }
