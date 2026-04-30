from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LearningProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learning_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    focus_areas: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    daily_target_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user: Mapped["User"] = relationship(back_populates="learning_profile")

