from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.learning_profile import LearningProfile
from app.models.user import User
from app.schemas.onboarding import (
    FirstPlanResponse,
    FirstPlanTaskResponse,
    OnboardingCompleteRequest,
)


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_with_learning_profile(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await session.execute(
        select(User)
        .options(selectinload(User.learning_profile))
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    email: str,
    hashed_password: str,
    full_name: str | None = None,
) -> User:
    user = User(
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


def _build_first_plan(payload: OnboardingCompleteRequest) -> FirstPlanResponse:
    if payload.practice_preference == "speaking":
        return FirstPlanResponse(
            title="Your First English Practice Plan",
            description=(
                "We’ll start with short spoken prompts so you can answer naturally and build confidence fast."
            ),
            tasks=[
                FirstPlanTaskResponse(
                    type="speaking",
                    title="Answer 3 simple speaking prompts",
                    estimated_minutes=5,
                )
            ],
        )

    if payload.practice_preference == "writing":
        return FirstPlanResponse(
            title="Your First English Practice Plan",
            description=(
                "We’ll start with simple daily-life sentences to build your confidence step by step."
            ),
            tasks=[
                FirstPlanTaskResponse(
                    type="translation",
                    title="Translate 3 simple sentences",
                    estimated_minutes=5,
                )
            ],
        )

    return FirstPlanResponse(
        title="Your First English Practice Plan",
        description=(
            "We’ll begin with simple daily-life sentences, then move into short replies so you build both accuracy and confidence."
        ),
        tasks=[
            FirstPlanTaskResponse(
                type="translation",
                title="Translate 3 simple sentences",
                estimated_minutes=5,
            )
        ],
    )


def _default_focus_areas(practice_preference: str) -> list[str]:
    if practice_preference == "speaking":
        return ["speaking", "fluency", "confidence"]
    if practice_preference == "writing":
        return ["writing", "grammar", "vocabulary"]
    return ["speaking", "writing", "confidence"]


async def complete_onboarding(
    session: AsyncSession,
    user: User,
    payload: OnboardingCompleteRequest,
) -> tuple[User, LearningProfile, FirstPlanResponse]:
    db_user = await get_user_with_learning_profile(session, user.id)
    if db_user is None:
        raise ValueError("User not found")

    db_user.native_language = payload.native_language
    db_user.english_level = payload.english_level
    db_user.learning_goal = payload.learning_goal
    db_user.practice_preference = payload.practice_preference
    db_user.onboarding_completed = True

    profile = db_user.learning_profile
    if profile is None:
        profile = LearningProfile(user_id=db_user.id)
        session.add(profile)

    profile.goal = payload.learning_goal
    profile.focus_areas = _default_focus_areas(payload.practice_preference)
    if profile.daily_target_minutes is None:
        profile.daily_target_minutes = 15

    await session.commit()
    await session.refresh(db_user)
    await session.refresh(profile)
    return db_user, profile, _build_first_plan(payload)
