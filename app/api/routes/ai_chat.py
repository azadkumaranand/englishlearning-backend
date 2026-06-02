from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.ai_chat import ChatRequest, ChatResponse, VoiceChatResponse, VoiceTranscriptionMetadata
from app.schemas.correction import build_message_correction_response
from app.schemas.practice_message import PracticeMessageResponse
from app.services.conversation_service import chat_in_practice_session, stream_chat_in_practice_session
from app.services.voice_chat_service import handle_voice_chat

router = APIRouter(prefix="/practice/sessions", tags=["ai_chat"])
logger = logging.getLogger(__name__)


def _build_chat_response(
    *,
    session_id: uuid.UUID,
    user_message,
    assistant_message,
    correction,
    completion_summary=None,
) -> ChatResponse:
    return ChatResponse(
        session_id=session_id,
        user_message=PracticeMessageResponse.model_validate(user_message),
        assistant_message=PracticeMessageResponse.model_validate(assistant_message),
        correction=build_message_correction_response(correction) if correction is not None else None,
        completion_summary=completion_summary,
    )


def _sse_event(payload: dict) -> bytes:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


@router.post("/{session_id}/chat", response_model=ChatResponse)
async def chat_in_session(
    session_id: uuid.UUID,
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ChatResponse:
    user_message, assistant_message, correction, completion_summary = await chat_in_practice_session(
        session=session,
        user_id=current_user.id,
        session_id=session_id,
        content=payload.content,
        user_message_metadata=payload.metadata_json,
    )
    return _build_chat_response(
        session_id=session_id,
        user_message=user_message,
        assistant_message=assistant_message,
        correction=correction,
        completion_summary=completion_summary,
    )


@router.post("/{session_id}/chat/stream")
async def chat_in_session_stream(
    session_id: uuid.UUID,
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    async def event_stream():
        try:
            async for event in stream_chat_in_practice_session(
                session=session,
                user_id=current_user.id,
                session_id=session_id,
                content=payload.content,
                user_message_metadata=payload.metadata_json,
            ):
                if event.get("type") == "final":
                    response = _build_chat_response(
                        session_id=session_id,
                        user_message=event["user_message"],
                        assistant_message=event["assistant_message"],
                        correction=event["correction"],
                        completion_summary=event.get("completion_summary"),
                    )
                    yield _sse_event(
                        {
                            "type": "final",
                            "data": response.model_dump(mode="json"),
                        }
                    )
                else:
                    yield _sse_event(event)
        except Exception as exc:
            logger.exception("Practice chat stream failed", extra={"session_id": str(session_id)})
            detail = getattr(exc, "detail", None)
            message = detail if isinstance(detail, str) else str(exc)
            yield _sse_event({"type": "error", "detail": message or "Chat stream failed"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
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
