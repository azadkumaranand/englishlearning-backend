"""create conversation tables

Revision ID: 20260429_0012
Revises: 20260429_0011
Create Date: 2026-04-29 00:12:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260429_0012"
down_revision = "20260429_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_learning_profiles", sa.Column("average_conversation_score", sa.Float(), nullable=False, server_default="0"))
    op.add_column("user_learning_profiles", sa.Column("speaking_confidence_score", sa.Float(), nullable=False, server_default="0"))
    op.add_column("user_learning_profiles", sa.Column("total_conversation_turns", sa.Integer(), nullable=False, server_default="0"))

    op.create_table(
        "conversation_sessions",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scenario", sa.String(length=100), nullable=False),
        sa.Column("level", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'active'")),
        sa.Column("max_turns", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("current_turn", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_conversation_sessions_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversation_sessions")),
    )
    op.create_index(op.f("ix_conversation_sessions_user_id"), "conversation_sessions", ["user_id"], unique=False)

    op.create_table(
        "conversation_messages",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("corrected_sentence", sa.Text(), nullable=True),
        sa.Column("natural_sentence", sa.Text(), nullable=True),
        sa.Column("feedback_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["session_id"], ["conversation_sessions.id"], name=op.f("fk_conversation_messages_session_id_conversation_sessions"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversation_messages")),
    )
    op.create_index(op.f("ix_conversation_messages_session_id"), "conversation_messages", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_conversation_messages_session_id"), table_name="conversation_messages")
    op.drop_table("conversation_messages")
    op.drop_index(op.f("ix_conversation_sessions_user_id"), table_name="conversation_sessions")
    op.drop_table("conversation_sessions")
    op.drop_column("user_learning_profiles", "total_conversation_turns")
    op.drop_column("user_learning_profiles", "speaking_confidence_score")
    op.drop_column("user_learning_profiles", "average_conversation_score")
