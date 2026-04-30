"""create user learning profiles

Revision ID: 20260429_0010
Revises: 20260429_0009
Create Date: 2026-04-29 00:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260429_0010"
down_revision = "20260429_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_learning_profiles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("average_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_practice_sessions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_correct_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "weak_areas_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "strong_areas_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "repeated_mistakes_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "recent_mistakes_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("recommended_focus_area", sa.String(length=100), nullable=True),
        sa.Column(
            "current_difficulty",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'beginner'"),
        ),
        sa.Column("last_practiced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_learning_profiles_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_learning_profiles")),
        sa.UniqueConstraint("user_id", name=op.f("uq_user_learning_profiles_user_id")),
    )


def downgrade() -> None:
    op.drop_table("user_learning_profiles")
