"""Analysis model for storing ToS analysis results."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Analysis(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single ToS/Privacy Policy analysis run."""

    __tablename__ = "analyses"

    # Owner (nullable for anonymous users)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Input metadata
    input_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "url" | "text" | "file"
    input_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    document_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Denormalized from result JSONB for easy querying / sorting
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    document_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    overall_score: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Content hash for caching / dedup
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Pipeline status
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending"
    )  # pending | acquiring | validating | chunking | analyzing | aggregating | complete | error

    # Error message if pipeline failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Full analysis result (stored as JSONB)
    result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # LLM metadata
    llm_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    llm_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    token_count: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Relationships
    user = relationship("User", back_populates="analyses")

    __table_args__ = (
        Index("ix_analyses_content_hash_status", "content_hash", "status"),
    )

    def __repr__(self) -> str:
        return f"<Analysis {self.id} status={self.status}>"
