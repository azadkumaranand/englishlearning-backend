"""add phase1 onboarding fields

Revision ID: 20260429_0009
Revises: 20260428_0008
Create Date: 2026-04-29 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260429_0009"
down_revision = "20260428_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("native_language", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("learning_goal", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("practice_preference", sa.String(length=50), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "onboarding_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "onboarding_completed")
    op.drop_column("users", "practice_preference")
    op.drop_column("users", "learning_goal")
    op.drop_column("users", "native_language")
