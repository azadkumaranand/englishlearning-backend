from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    native_language: Mapped[str | None] = mapped_column(String(100), nullable=True)
    english_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    learning_goal: Mapped[str | None] = mapped_column(String(100), nullable=True)
    practice_preference: Mapped[str | None] = mapped_column(String(50), nullable=True)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    learning_profile: Mapped["LearningProfile | None"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    practice_sessions: Mapped[list["PracticeSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    conversation_sessions: Mapped[list["ConversationSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    mistake_patterns: Mapped[list["UserMistakePattern"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    learning_summary: Mapped["UserLearningSummary | None"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    user_learning_profile: Mapped["UserLearningProfile | None"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    mistake_reviews: Mapped[list["MistakeReview"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
