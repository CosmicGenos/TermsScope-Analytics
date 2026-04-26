"""Document enrichment node — 3 parallel LLM calls for metadata, structure, and quality."""

from __future__ import annotations

import asyncio
import logging

from app.llm.factory import LLMFactory
from app.pipeline.prompts.enrich import (
    METADATA_SYSTEM_PROMPT,
    QUALITY_SYSTEM_PROMPT,
    STRUCTURE_SYSTEM_PROMPT,
    build_metadata_prompt,
    build_quality_prompt,
    build_structure_prompt,
)
from app.pipeline.state import AnalysisState
from app.schemas.output import ContentQuality, DocumentMetadata, DocumentStructure

logger = logging.getLogger(__name__)


async def _extract_metadata(llm, content: str) -> DocumentMetadata:
    try:
        result: DocumentMetadata = await llm.generate(
            prompt=build_metadata_prompt(content),
            output_schema=DocumentMetadata,
            system_prompt=METADATA_SYSTEM_PROMPT,
            temperature=0.1,
        )
        return result
    except Exception as exc:
        logger.warning("Metadata extraction failed: %s", exc)
        return DocumentMetadata()


async def _extract_structure(llm, content: str) -> DocumentStructure:
    try:
        result: DocumentStructure = await llm.generate(
            prompt=build_structure_prompt(content),
            output_schema=DocumentStructure,
            system_prompt=STRUCTURE_SYSTEM_PROMPT,
            temperature=0.1,
        )
        return result
    except Exception as exc:
        logger.warning("Structure extraction failed: %s", exc)
        return DocumentStructure()


async def _assess_quality(llm, content: str) -> ContentQuality:
    try:
        result: ContentQuality = await llm.generate(
            prompt=build_quality_prompt(content),
            output_schema=ContentQuality,
            system_prompt=QUALITY_SYSTEM_PROMPT,
            temperature=0.1,
        )
        return result
    except Exception as exc:
        logger.warning("Quality assessment failed: %s", exc)
        return ContentQuality()


async def enrich_document(state: AnalysisState) -> dict:
    """Run three parallel LLM calls to extract document intelligence.

    Outputs:
    - document_metadata: company, doc type, dates, jurisdiction, language
    - document_structure: section list + structure type
    - content_quality: is_legal_document flag, completeness, quality notes
    - document_title: "{company_name} — {document_type}"
    """
    content = state.get("cleaned_content", "")
    llm = LLMFactory.create(
        provider=state.get("llm_provider"),
        model=state.get("llm_model"),
    )

    logger.info("Enriching document (%d chars)", len(content))

    metadata, structure, quality = await asyncio.gather(
        _extract_metadata(llm, content),
        _extract_structure(llm, content),
        _assess_quality(llm, content),
    )

    logger.info(
        "Enrich complete: type=%s company=%s structure=%s sections=%d quality=%d is_legal=%s",
        metadata.document_type,
        metadata.company_name,
        structure.structure_type,
        len(structure.sections),
        quality.completeness_score,
        quality.is_legal_document,
    )

    # Early exit if content is not a legal document
    if not quality.is_legal_document:
        return {
            "status": "error",
            "error": (
                "The provided content does not appear to be a legal document "
                "(Terms of Service, Privacy Policy, EULA, etc.). "
                "Please provide a valid legal agreement."
            ),
            "document_metadata": metadata.model_dump(),
            "document_structure": structure.model_dump(),
            "content_quality": quality.model_dump(),
        }

    # Build a human-readable document title from extracted metadata
    title_parts = [p for p in [metadata.company_name, metadata.document_type] if p and p != "Unknown"]
    document_title = " — ".join(title_parts) if title_parts else None

    return {
        "document_metadata": metadata.model_dump(),
        "document_structure": structure.model_dump(),
        "content_quality": quality.model_dump(),
        "document_title": document_title,
        "status": "validating",
    }
