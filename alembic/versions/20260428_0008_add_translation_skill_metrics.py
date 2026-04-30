"""add translation skill metrics

Revision ID: 20260428_0008
Revises: 20260427_0007
Create Date: 2026-04-28 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260428_0008"
down_revision = "20260427_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_learning_summaries",
        sa.Column(
            "total_translation_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "user_learning_summaries",
        sa.Column(
            "translation_first_try_success_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "user_learning_summaries",
        sa.Column("average_translation_attempts", sa.Float(), nullable=True),
    )
    op.add_column(
        "user_learning_summaries",
        sa.Column("detected_translation_level", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_learning_summaries", "detected_translation_level")
    op.drop_column("user_learning_summaries", "average_translation_attempts")
    op.drop_column("user_learning_summaries", "translation_first_try_success_count")
    op.drop_column("user_learning_summaries", "total_translation_attempts")
