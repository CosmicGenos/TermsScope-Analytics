"""add denormalized analysis columns

Revision ID: a1c4e7f2b835
Revises: 3f8c2a1b9d10
Create Date: 2026-04-27

Adds three columns to the analyses table that mirror data already stored
inside the JSONB result column.  Keeping them as real columns lets the
application sort, filter, and display history rows without parsing JSON.

  company_name   — pulled from result.company_name    (set by enrich node)
  document_type  — pulled from result.document_type   (set by enrich node)
  overall_score  — pulled from result.overall_score   (0-100, set by aggregate node)

Existing rows are back-filled from the JSONB result column where possible.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "a1c4e7f2b835"
down_revision = "3f8c2a1b9d10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Add new columns (all nullable so existing rows are not broken) ------
    op.add_column("analyses", sa.Column("company_name",  sa.String(255), nullable=True))
    op.add_column("analyses", sa.Column("document_type", sa.String(100), nullable=True))
    op.add_column("analyses", sa.Column("overall_score", sa.Integer(),   nullable=True))

    # --- Back-fill from existing JSONB result rows ---------------------------
    op.execute("""
        UPDATE analyses
        SET
            company_name  = result->>'company_name',
            document_type = result->>'document_type',
            overall_score = (result->>'overall_score')::int
        WHERE
            result IS NOT NULL
            AND status = 'complete'
    """)

    # --- Indexes for the two most useful query patterns ----------------------
    # Sort history by score (highest/lowest risk first)
    op.create_index("ix_analyses_overall_score", "analyses", ["overall_score"])

    # Filter history by company ("show me all Spotify analyses")
    op.create_index("ix_analyses_company_name",  "analyses", ["company_name"])


def downgrade() -> None:
    op.drop_index("ix_analyses_company_name",  table_name="analyses")
    op.drop_index("ix_analyses_overall_score", table_name="analyses")

    op.drop_column("analyses", "overall_score")
    op.drop_column("analyses", "document_type")
    op.drop_column("analyses", "company_name")
