from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PracticeTranslationItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "practice_translation_items"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("practice_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    source_sentence: Mapped[str] = mapped_column(Text, nullable=False)
    reference_translation: Mapped[str] = mapped_column(Text, nullable=False)
    assistant_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    focus_tag: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default=text("'active'"),
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    last_learner_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    generator_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped["PracticeSession"] = relationship(back_populates="translation_items")
