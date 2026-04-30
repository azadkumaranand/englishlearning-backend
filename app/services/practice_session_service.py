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
from app.models.topic import Topic
from app.models.user import User
from app.schemas.practice_message import PracticeMessageCreateRequest
from app.schemas.practice_session import PracticeSessionCreateRequest
from app.services.personalization_service import get_personalization_summary
from app.services.session_starter_service import generate_session_starter


def _session_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practice session not found")


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
