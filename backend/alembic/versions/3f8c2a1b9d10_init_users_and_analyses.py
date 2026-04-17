"""init users and analyses

Revision ID: 3f8c2a1b9d10
Revises: 
Create Date: 2026-03-22

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "3f8c2a1b9d10"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("google_id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("avatar_url", sa.String(length=2048), nullable=True),
        sa.UniqueConstraint("google_id", name="uq_users_google_id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_google_id", "users", ["google_id"], unique=False)

    op.create_table(
        "analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("input_type", sa.String(length=20), nullable=False),
        sa.Column("input_url", sa.String(length=2048), nullable=True),
        sa.Column("document_title", sa.String(length=500), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("llm_provider", sa.String(length=50), nullable=True),
        sa.Column("llm_model", sa.String(length=100), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_analyses_user_id_users", ondelete="SET NULL"),
    )
    op.create_index("ix_analyses_user_id", "analyses", ["user_id"], unique=False)
    op.create_index("ix_analyses_content_hash", "analyses", ["content_hash"], unique=False)
    op.create_index(
        "ix_analyses_content_hash_status",
        "analyses",
        ["content_hash", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_analyses_content_hash_status", table_name="analyses")
    op.drop_index("ix_analyses_content_hash", table_name="analyses")
    op.drop_index("ix_analyses_user_id", table_name="analyses")
    op.drop_table("analyses")

    op.drop_index("ix_users_google_id", table_name="users")
    op.drop_table("users")
