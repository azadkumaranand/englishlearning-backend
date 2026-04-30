"""create personalization tables

Revision ID: 20260420_0005
Revises: 20260417_0004
Create Date: 2026-04-20 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260420_0005"
down_revision = "20260417_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_learning_summaries",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "top_weak_areas",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("last_recommended_focus", sa.String(), nullable=True),
        sa.Column("average_message_length", sa.Float(), nullable=True),
        sa.Column("total_corrections_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_user_learning_summaries_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_learning_summaries")),
        sa.UniqueConstraint("user_id", name=op.f("uq_user_learning_summaries_user_id")),
    )
    op.create_table(
        "user_mistake_patterns",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag", sa.String(length=100), nullable=False),
        sa.Column("frequency", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_example_original", sa.Text(), nullable=True),
        sa.Column("last_example_corrected", sa.Text(), nullable=True),
        sa.Column("severity_score", sa.Float(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_user_mistake_patterns_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_mistake_patterns")),
        sa.UniqueConstraint("user_id", "tag", name="uq_user_mistake_patterns_user_tag"),
    )
    op.create_index(op.f("ix_user_mistake_patterns_tag"), "user_mistake_patterns", ["tag"], unique=False)
    op.create_index(op.f("ix_user_mistake_patterns_user_id"), "user_mistake_patterns", ["user_id"], unique=False)

def downgrade() -> None:
    op.drop_index(op.f("ix_user_mistake_patterns_user_id"), table_name="user_mistake_patterns")
    op.drop_index(op.f("ix_user_mistake_patterns_tag"), table_name="user_mistake_patterns")
    op.drop_table("user_mistake_patterns")
    op.drop_table("user_learning_summaries")
