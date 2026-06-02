from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.practice_message import PracticeMessage
from app.models.practice_session import PracticeSession
from app.models.practice_translation_item import PracticeTranslationItem
from app.models.topic import Topic
from app.models.user import User
from app.schemas.practice_message import PracticeMessageCreateRequest
from app.schemas.practice_session import (
    PracticeSessionCompletionSummaryResponse,
    PracticeSessionCreateRequest,
)
from app.schemas.progress import ProgressRecommendedPracticeResponse
from app.services.personalization_service import get_personalization_summary
from app.services.session_starter_service import generate_session_starter
from app.services.user_learning_profile_service import (
    get_or_create_user_learning_profile,
    learning_area_label,
    normalize_learning_area,
)


def _session_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practice session not found")


def _top_area_label(area_counts: dict | None) -> str | None:
    if not area_counts:
        return None
    sorted_items = sorted(
        ((normalize_learning_area(str(key)), int(value or 0)) for key, value in area_counts.items()),
        key=lambda item: item[1],
        reverse=True,
    )
    for area, count in sorted_items:
        if area and count > 0:
            return learning_area_label(area)
    return None


def _recommended_next_practice(
    *,
    recommended_focus_area: str | None,
    repeated_mistakes_count: int,
    average_translation_score: int,
    average_conversation_score: int,
    practice_preference: str | None,
) -> ProgressRecommendedPracticeResponse:
    focus_area = normalize_learning_area(recommended_focus_area)
    focus_label = learning_area_label(focus_area).lower() if focus_area else ""

    if repeated_mistakes_count > 0 and focus_area:
        return ProgressRecommendedPracticeResponse(
            type="mistake_review",
            title=f"Review {focus_label} mistakes",
        )

    if practice_preference == "speaking" or (
        average_conversation_score > 0 and average_conversation_score < max(average_translation_score, 70)
    ):
        return ProgressRecommendedPracticeResponse(
            type="roleplay_speaking",
            title="Start a roleplay speaking session",
        )

    return ProgressRecommendedPracticeResponse(
        type="translation_practice",
        title=f"Practice {focus_label}" if focus_area else "Start translation practice",
    )


async def create_practice_session(
    session: AsyncSession,
    user: User,
    payload: PracticeSessionCreateRequest,
    topic: Topic | None = None,
) -> PracticeSession:
    practice_session = PracticeSession(
        user_id=user.id,
        topic_id=topic.id if topic else None,
        mode=payload.mode,
        title=payload.title,
        status="active",
        started_at=datetime.now(timezone.utc),
    )
    session.add(practice_session)
    await session.commit()
    await session.refresh(practice_session)
    if topic is not None:
        practice_session.topic = topic
    return practice_session


async def list_user_practice_sessions(
    session: AsyncSession,
    user_id: uuid.UUID,
    status_value: str | None = None,
    mode: str | None = None,
) -> list[PracticeSession]:
    query = (
        select(PracticeSession)
        .options(selectinload(PracticeSession.topic))
        .where(PracticeSession.user_id == user_id)
    )
    if status_value is not None:
        query = query.where(PracticeSession.status == status_value)
    if mode is not None:
        query = query.where(PracticeSession.mode == mode)
    query = query.order_by(PracticeSession.created_at.desc())
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_user_practice_session(
    session: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    include_messages: bool = False,
    include_user_context: bool = False,
) -> PracticeSession:
    options = [selectinload(PracticeSession.topic)]
    if include_messages:
        options.append(selectinload(PracticeSession.messages))
    if include_user_context:
        options.append(selectinload(PracticeSession.user).selectinload(User.learning_profile))
        options.append(
            selectinload(PracticeSession.user).selectinload(User.user_learning_profile)
        )

    result = await session.execute(
        select(PracticeSession)
        .options(*options)
        .where(PracticeSession.id == session_id, PracticeSession.user_id == user_id)
    )
    practice_session = result.scalar_one_or_none()
    if practice_session is None:
        raise _session_not_found()
    return practice_session


async def create_practice_message(
    session: AsyncSession,
    practice_session: PracticeSession,
    *,
    role: str,
    content: str,
    metadata_json: dict[str, Any] | None = None,
) -> PracticeMessage:
    result = await session.execute(
        select(func.max(PracticeMessage.message_order)).where(
            PracticeMessage.session_id == practice_session.id
        )
    )
    max_order = result.scalar_one()
    next_order = (max_order or 0) + 1

    message = PracticeMessage(
        session_id=practice_session.id,
        role=role,
        content=content,
        message_order=next_order,
        metadata_json=metadata_json,
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


async def complete_practice_session(
    session: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> PracticeSession:
    practice_session = await get_user_practice_session(session, user_id, session_id)
    practice_session.status = "completed"
    if practice_session.ended_at is None:
        practice_session.ended_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(practice_session)
    return await get_user_practice_session(session, user_id, session_id, include_messages=True)


async def build_practice_session_completion_summary(
    session: AsyncSession,
    *,
    practice_session: PracticeSession,
    auto_completed: bool,
    completed_items: int | None = None,
) -> PracticeSessionCompletionSummaryResponse:
    profile = await get_or_create_user_learning_profile(
        session,
        user_id=practice_session.user_id,
        preferred_level=practice_session.user.english_level if practice_session.user else None,
    )

    if completed_items is None and practice_session.mode == "translation_practice":
        result = await session.execute(
            select(func.count(PracticeTranslationItem.id)).where(
                PracticeTranslationItem.session_id == practice_session.id,
                PracticeTranslationItem.status == "completed",
            )
        )
        completed_items = int(result.scalar_one() or 0)

    focus_area = normalize_learning_area(profile.recommended_focus_area)
    focus_label = learning_area_label(focus_area) if focus_area else None
    strongest_area = _top_area_label(profile.strong_areas_json)
    repeated_mistakes_count = len(
        [item for item in list(profile.repeated_mistakes_json or []) if int(item.get("count", 1) or 1) >= 2]
    )
    recommended_next_practice = _recommended_next_practice(
        recommended_focus_area=profile.recommended_focus_area,
        repeated_mistakes_count=repeated_mistakes_count,
        average_translation_score=int(round(profile.average_score or 0)),
        average_conversation_score=int(round(profile.average_conversation_score or 0)),
        practice_preference=practice_session.user.practice_preference if practice_session.user else None,
    )

    if practice_session.mode == "translation_practice":
        title = "Nice work"
        message = (
            f"You completed {completed_items or 0} translation items."
            + (f" Next, focus on {focus_label.lower()}." if focus_label else " Keep building clear English sentences.")
        )
    else:
        title = "Session complete"
        message = "You finished this practice session. Keep the momentum going with your next personalized activity."

    return PracticeSessionCompletionSummaryResponse(
        title=title,
        message=message,
        completed_items=completed_items or 0,
        average_score=int(round(profile.average_score or 0)) if (profile.total_attempts or 0) > 0 else None,
        strongest_area=strongest_area,
        focus_area=focus_label,
        recommended_next_practice=recommended_next_practice,
        auto_completed=auto_completed,
    )


async def add_practice_message(
    session: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    payload: PracticeMessageCreateRequest,
) -> PracticeMessage:
    practice_session = await get_user_practice_session(session, user_id, session_id)
    return await create_practice_message(
        session=session,
        practice_session=practice_session,
        role=payload.role,
        content=payload.content,
    )


async def list_practice_messages(
    session: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> list[PracticeMessage]:
    await get_user_practice_session(session, user_id, session_id)
    result = await session.execute(
        select(PracticeMessage)
        .where(PracticeMessage.session_id == session_id)
        .order_by(PracticeMessage.message_order.asc(), PracticeMessage.created_at.asc())
    )
    return list(result.scalars().all())


async def list_recent_practice_messages(
    session: AsyncSession,
    session_id: uuid.UUID,
    limit: int = 12,
) -> list[PracticeMessage]:
    result = await session.execute(
        select(PracticeMessage)
        .where(PracticeMessage.session_id == session_id)
        .order_by(PracticeMessage.message_order.desc())
        .limit(limit)
    )
    return list(reversed(result.scalars().all()))


async def ensure_practice_session_starter(
    session: AsyncSession,
    *,
    practice_session: PracticeSession,
) -> PracticeMessage | None:
    loaded_session = await get_user_practice_session(
        session=session,
        user_id=practice_session.user_id,
        session_id=practice_session.id,
        include_messages=True,
        include_user_context=True,
    )
    existing_messages = loaded_session.messages or []
    if existing_messages:
        return next(
            (
                message
                for message in existing_messages
                if message.role == "assistant"
                and isinstance(message.metadata_json, dict)
                and message.metadata_json.get("is_starter") is True
            ),
            None,
        )

    if loaded_session.mode == "translation_practice":
        from app.services.translation_practice_service import ensure_translation_session_starter

        return await ensure_translation_session_starter(
            session=session,
            practice_session=loaded_session,
        )

    learning_summary = await get_personalization_summary(
        session,
        user_id=loaded_session.user_id,
    )
    starter = await generate_session_starter(
        session=session,
        practice_session=loaded_session,
        learning_summary=learning_summary,
    )
    starter_metadata = {
        "is_starter": True,
        "starter_source": starter.source,
        "quick_replies": starter.quick_replies,
        "provider": starter.provider,
        "model": starter.model,
        "response_id": starter.response_id,
    }
    if starter.metadata_json:
        starter_metadata.update(starter.metadata_json)
    return await create_practice_message(
        session=session,
        practice_session=loaded_session,
        role="assistant",
        content=starter.opener,
        metadata_json=starter_metadata,
    )
