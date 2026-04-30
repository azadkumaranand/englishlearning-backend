"""add translation progress to learning summary

Revision ID: 20260427_0007
Revises: 20260420_0006
Create Date: 2026-04-27 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260427_0007"
down_revision = "20260420_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_learning_summaries",
        sa.Column(
            "completed_translation_sources",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "user_learning_summaries",
        sa.Column(
            "total_translation_items_completed",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("user_learning_summaries", "total_translation_items_completed")
    op.drop_column("user_learning_summaries", "completed_translation_sources")
