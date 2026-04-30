"""create translation practice items

Revision ID: 20260420_0006
Revises: 20260420_0005
Create Date: 2026-04-20 19:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260420_0006"
down_revision = "20260420_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "practice_translation_items",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("source_sentence", sa.Text(), nullable=False),
        sa.Column("reference_translation", sa.Text(), nullable=False),
        sa.Column("assistant_prompt", sa.Text(), nullable=False),
        sa.Column("focus_tag", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'active'"), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_learner_answer", sa.Text(), nullable=True),
        sa.Column("generator_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["practice_sessions.id"],
            name=op.f("fk_practice_translation_items_session_id_practice_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_practice_translation_items")),
        sa.UniqueConstraint("session_id", "order_index", name="uq_practice_translation_items_session_order"),
    )
    op.create_index(
        op.f("ix_practice_translation_items_session_id"),
        "practice_translation_items",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_practice_translation_items_active_session",
        "practice_translation_items",
        ["session_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index("ix_practice_translation_items_active_session", table_name="practice_translation_items")
    op.drop_index(op.f("ix_practice_translation_items_session_id"), table_name="practice_translation_items")
    op.drop_table("practice_translation_items")
