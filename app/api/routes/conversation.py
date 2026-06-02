from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.conversation import (
    ConversationReplyRequest,
    ConversationReplyResponse,
    ConversationSessionStateResponse,
    ConversationStartRequest,
    ConversationStartResponse,
    ConversationVoiceReplyResponse,
)
from app.services.conversation_roleplay_service import (
    exit_conversation_session,
    reply_in_conversation_session,
    start_conversation_session,
)
from app.services.conversation_voice_service import handle_conversation_voice_reply

router = APIRouter(prefix="/conversation", tags=["conversation"])


@router.post("/start", response_model=ConversationStartResponse)
async def start_conversation(
    payload: ConversationStartRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ConversationStartResponse:
    return await start_conversation_session(
        session,
        user=current_user,
        scenario=payload.scenario,
    )


@router.post("/reply", response_model=ConversationReplyResponse)
async def reply_conversation(
    payload: ConversationReplyRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ConversationReplyResponse:
    return await reply_in_conversation_session(
        session,
        user=current_user,
        payload=payload,
    )


@router.patch("/{session_id}/exit", response_model=ConversationSessionStateResponse)
async def exit_conversation(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ConversationSessionStateResponse:
    return await exit_conversation_session(
        session,
        user=current_user,
        session_id=session_id,
    )


async def _reply_conversation_voice(
    *,
    session_id: uuid.UUID,
    audio: UploadFile = File(...),
    duration_ms: int | None = Form(default=None),
    source: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ConversationVoiceReplyResponse:
    return await handle_conversation_voice_reply(
        session=session,
        user=current_user,
        session_id=session_id,
        audio_file=audio,
        duration_ms=duration_ms,
        source=source,
    )


@router.post("/{session_id}/reply/voice", response_model=ConversationVoiceReplyResponse)
async def reply_conversation_voice_by_session(
    session_id: uuid.UUID,
    audio: UploadFile = File(...),
    duration_ms: int | None = Form(default=None),
    source: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ConversationVoiceReplyResponse:
    return await _reply_conversation_voice(
        session_id=session_id,
        audio=audio,
        duration_ms=duration_ms,
        source=source,
        current_user=current_user,
        session=session,
    )


@router.post("/reply/voice", response_model=ConversationVoiceReplyResponse)
async def reply_conversation_voice(
    session_id: uuid.UUID = Form(...),
    audio: UploadFile = File(...),
    duration_ms: int | None = Form(default=None),
    source: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ConversationVoiceReplyResponse:
    return await _reply_conversation_voice(
        session_id=session_id,
        audio=audio,
        duration_ms=duration_ms,
        source=source,
        current_user=current_user,
        session=session,
    )
