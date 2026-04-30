from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.practice_message import PracticeMessageCreateRequest, PracticeMessageResponse
from app.schemas.practice_session import (
    PracticeMode,
    PracticeSessionCreateRequest,
    PracticeSessionDetailResponse,
    PracticeSessionListItemResponse,
    PracticeSessionStarterResponse,
    PracticeSessionStatus,
)
from app.services.practice_session_service import (
    add_practice_message,
    complete_practice_session,
    create_practice_session,
    ensure_practice_session_starter,
    get_user_practice_session,
    list_practice_messages,
    list_user_practice_sessions,
)
from app.services.topic_service import get_active_topic_by_id

router = APIRouter(prefix="/practice/sessions", tags=["practice_sessions"])


def _serialize_session_list_item(practice_session) -> PracticeSessionListItemResponse:
    return PracticeSessionListItemResponse.model_validate(practice_session)


def _extract_session_starter(practice_session) -> PracticeSessionStarterResponse | None:
    messages = sorted(
        practice_session.messages or [],
        key=lambda message: (message.message_order, message.created_at),
    )
    if not messages or any(message.role == "user" for message in messages):
        return None

    for message in messages:
        metadata = message.metadata_json if isinstance(message.metadata_json, dict) else {}
        if message.role != "assistant" or metadata.get("is_starter") is not True:
            continue

        quick_replies = [
            str(value).strip()
            for value in metadata.get("quick_replies", [])
            if str(value).strip()
        ]
        return PracticeSessionStarterResponse(
            assistant_message=PracticeMessageResponse.model_validate(message),
            quick_replies=quick_replies,
            is_fresh=True,
        )
    return None


def _serialize_session_detail(practice_session) -> PracticeSessionDetailResponse:
    detail = PracticeSessionDetailResponse.model_validate(practice_session)
    return detail.model_copy(update={"starter": _extract_session_starter(practice_session)})


@router.post("", response_model=PracticeSessionDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: PracticeSessionCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PracticeSessionDetailResponse:
    topic = None
    if payload.topic_id is not None:
        topic = await get_active_topic_by_id(session, payload.topic_id)
        if topic is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")

    practice_session = await create_practice_session(
        session=session,
        user=current_user,
        payload=payload,
        topic=topic,
    )
    practice_session = await get_user_practice_session(
        session=session,
        user_id=current_user.id,
        session_id=practice_session.id,
        include_messages=True,
        include_user_context=True,
    )
    await ensure_practice_session_starter(session=session, practice_session=practice_session)
    practice_session = await get_user_practice_session(
        session=session,
        user_id=current_user.id,
        session_id=practice_session.id,
        include_messages=True,
        include_user_context=True,
    )
    return _serialize_session_detail(practice_session)


@router.get("", response_model=list[PracticeSessionListItemResponse])
async def list_sessions(
    status_value: PracticeSessionStatus | None = Query(default=None, alias="status"),
    mode: PracticeMode | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[PracticeSessionListItemResponse]:
    practice_sessions = await list_user_practice_sessions(
        session=session,
        user_id=current_user.id,
        status_value=status_value,
        mode=mode,
    )
    return [_serialize_session_list_item(item) for item in practice_sessions]


@router.get("/{session_id}", response_model=PracticeSessionDetailResponse)
async def get_session_detail(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PracticeSessionDetailResponse:
    practice_session = await get_user_practice_session(
        session=session,
        user_id=current_user.id,
        session_id=session_id,
        include_messages=True,
        include_user_context=True,
    )
    if practice_session.status == "active" and not practice_session.messages:
        await ensure_practice_session_starter(session=session, practice_session=practice_session)
        practice_session = await get_user_practice_session(
            session=session,
            user_id=current_user.id,
            session_id=session_id,
            include_messages=True,
            include_user_context=True,
        )
    return _serialize_session_detail(practice_session)


@router.patch("/{session_id}/complete", response_model=PracticeSessionDetailResponse)
async def complete_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PracticeSessionDetailResponse:
    practice_session = await complete_practice_session(session, current_user.id, session_id)
    return _serialize_session_detail(practice_session)


@router.post(
    "/{session_id}/messages",
    response_model=PracticeMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session_message(
    session_id: uuid.UUID,
    payload: PracticeMessageCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PracticeMessageResponse:
    message = await add_practice_message(
        session=session,
        user_id=current_user.id,
        session_id=session_id,
        payload=payload,
    )
    return PracticeMessageResponse.model_validate(message)


@router.get("/{session_id}/messages", response_model=list[PracticeMessageResponse])
async def get_session_messages(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[PracticeMessageResponse]:
    messages = await list_practice_messages(session, current_user.id, session_id)
    return [PracticeMessageResponse.model_validate(message) for message in messages]
