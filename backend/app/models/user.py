"""User model for Google OAuth users."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A user authenticated via Google OAuth."""

    __tablename__ = "users"

    google_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)

    # Relationship to analyses
    analyses = relationship("Analysis", back_populates="user", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User {self.email}>"
