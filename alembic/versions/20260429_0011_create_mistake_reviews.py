"""create mistake reviews

Revision ID: 20260429_0011
Revises: 20260429_0010
Create Date: 2026-04-29 00:11:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260429_0011"
down_revision = "20260429_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mistake_reviews",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mistake_id", sa.String(length=255), nullable=False),
        sa.Column("retry_answer", sa.Text(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("is_improved", sa.Boolean(), nullable=False),
        sa.Column(
            "feedback_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_mistake_reviews_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mistake_reviews")),
    )
    op.create_index(op.f("ix_mistake_reviews_user_id"), "mistake_reviews", ["user_id"], unique=False)
    op.create_index(op.f("ix_mistake_reviews_mistake_id"), "mistake_reviews", ["mistake_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_mistake_reviews_mistake_id"), table_name="mistake_reviews")
    op.drop_index(op.f("ix_mistake_reviews_user_id"), table_name="mistake_reviews")
    op.drop_table("mistake_reviews")
