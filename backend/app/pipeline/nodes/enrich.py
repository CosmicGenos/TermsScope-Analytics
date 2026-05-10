"""Document enrichment node — single LLM call for metadata and quality."""

from __future__ import annotations

import logging

from app.llm.factory import LLMFactory
from app.pipeline.prompts.enrich import ENRICH_SYSTEM_PROMPT, build_enrich_prompt
from app.pipeline.state import AnalysisState
from app.schemas.output import ContentQuality, DocumentMetadata, EnrichResult

logger = logging.getLogger(__name__)


async def enrich_document(state: AnalysisState) -> dict:
    """Single LLM call to extract document metadata and assess quality."""
    content = state.get("cleaned_content", "")
    llm = LLMFactory.create(
        provider=state.get("llm_provider"),
        model=state.get("llm_model"),
    )

    logger.info("Enriching document (%d chars)", len(content))

    try:
        result: EnrichResult = await llm.generate(
            prompt=build_enrich_prompt(content),
            output_schema=EnrichResult,
            system_prompt=ENRICH_SYSTEM_PROMPT,
            temperature=0.1,
        )
        metadata = result.metadata
        quality = result.quality
    except Exception as exc:
        logger.warning("Enrich failed: %s", exc)
        metadata = DocumentMetadata()
        quality = ContentQuality()

    logger.info(
        "Enrich complete: type=%s company=%s quality=%d is_legal=%s",
        metadata.document_type,
        metadata.company_name,
        quality.completeness_score,
        quality.is_legal_document,
    )

    if not quality.is_legal_document:
        return {
            "status": "error",
            "error": (
                "The provided content does not appear to be a legal document "
                "(Terms of Service, Privacy Policy, EULA, etc.). "
                "Please provide a valid legal agreement."
            ),
            "document_metadata": metadata.model_dump(),
            "content_quality": quality.model_dump(),
        }

    title_parts = [p for p in [metadata.company_name, metadata.document_type] if p and p != "Unknown"]
    document_title = " — ".join(title_parts) if title_parts else None

    return {
        "document_metadata": metadata.model_dump(),
        "content_quality": quality.model_dump(),
        "document_title": document_title,
        "status": "validating",
    }
