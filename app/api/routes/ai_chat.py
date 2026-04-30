from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.ai_chat import ChatRequest, ChatResponse, VoiceChatResponse, VoiceTranscriptionMetadata
from app.schemas.correction import build_message_correction_response
from app.schemas.practice_message import PracticeMessageResponse
from app.services.conversation_service import chat_in_practice_session
from app.services.voice_chat_service import handle_voice_chat

router = APIRouter(prefix="/practice/sessions", tags=["ai_chat"])


@router.post("/{session_id}/chat", response_model=ChatResponse)
async def chat_in_session(
    session_id: uuid.UUID,
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ChatResponse:
    user_message, assistant_message, correction = await chat_in_practice_session(
        session=session,
        user_id=current_user.id,
        session_id=session_id,
        content=payload.content,
        user_message_metadata=payload.metadata_json,
    )
    return ChatResponse(
        session_id=session_id,
        user_message=PracticeMessageResponse.model_validate(user_message),
        assistant_message=PracticeMessageResponse.model_validate(assistant_message),
        correction=build_message_correction_response(correction) if correction is not None else None,
    )


@router.post("/{session_id}/voice-chat", response_model=VoiceChatResponse)
async def voice_chat_in_session(
    session_id: uuid.UUID,
    audio: UploadFile = File(...),
    duration_ms: int | None = Form(default=None),
    source: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> VoiceChatResponse:
    transcription, user_message, assistant_message, correction = await handle_voice_chat(
        session=session,
        user_id=current_user.id,
        session_id=session_id,
        audio_file=audio,
        duration_ms=duration_ms,
        source=source,
    )
    return VoiceChatResponse(
        session_id=session_id,
        transcript=transcription.text,
        user_message=PracticeMessageResponse.model_validate(user_message),
        assistant_message=PracticeMessageResponse.model_validate(assistant_message),
        correction=build_message_correction_response(correction) if correction is not None else None,
        transcription=VoiceTranscriptionMetadata(
            provider=transcription.provider,
            model=transcription.model,
            mime_type=transcription.mime_type,
            duration_ms=transcription.duration_ms,
            source=transcription.source,
            language=transcription.language,
            file_name=transcription.file_name,
        ),
    )
