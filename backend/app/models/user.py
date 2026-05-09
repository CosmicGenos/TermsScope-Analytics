"""User models — core identity + per-auth-type detail tables."""

from __future__ import annotations

import enum
import uuid
from typing import Optional

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


class AuthType(str, enum.Enum):
    google = "google"
    email = "email"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Core identity record — one row per person regardless of auth method."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="userrole"), nullable=False, default=UserRole.user
    )
    auth_type: Mapped[AuthType] = mapped_column(
        Enum(AuthType, name="authtype"), nullable=False
    )

    google_auth: Mapped[Optional[GoogleAuthUser]] = relationship(
        "GoogleAuthUser", back_populates="user", uselist=False
    )
    email_auth: Mapped[Optional[EmailAuthUser]] = relationship(
        "EmailAuthUser", back_populates="user", uselist=False
    )
    analyses = relationship("Analysis", back_populates="user", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.auth_type})>"


class GoogleAuthUser(Base):
    """Google OAuth credentials linked to a User."""

    __tablename__ = "google_auth_users"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    google_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="google_auth")

    def __repr__(self) -> str:
        return f"<GoogleAuthUser google_id={self.google_id}>"


class EmailAuthUser(Base):
    """Email + bcrypt password hash linked to a User."""

    __tablename__ = "email_auth_users"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    user: Mapped[User] = relationship("User", back_populates="email_auth")

    def __repr__(self) -> str:
        return f"<EmailAuthUser user_id={self.user_id}>"
