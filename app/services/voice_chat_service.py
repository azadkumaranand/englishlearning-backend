from __future__ import annotations

import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.message_correction import MessageCorrection
from app.models.practice_message import PracticeMessage
from app.services.conversation_service import chat_in_practice_session
from app.services.practice_session_service import get_user_practice_session
from app.services.stt_provider import (
    STTProviderConfigurationError,
    STTProviderResponseError,
    STTTranscriptionResult,
    transcribe_audio,
)


ALLOWED_AUDIO_CONTENT_TYPES = {
    "audio/m4a",
    "audio/mp4",
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
    "audio/ogg",
    "audio/aac",
    "audio/x-m4a",
}


async def handle_voice_chat(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    audio_file: UploadFile,
    duration_ms: int | None = None,
    source: str | None = None,
) -> tuple[STTTranscriptionResult, PracticeMessage, PracticeMessage, MessageCorrection | None]:
    practice_session = await get_user_practice_session(
        session=session,
        user_id=user_id,
        session_id=session_id,
    )
    use_default_language_hint = practice_session.mode != "free_chat"

    if not audio_file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file is required",
        )

    content_type = audio_file.content_type
    if content_type and content_type not in ALLOWED_AUDIO_CONTENT_TYPES and not content_type.startswith("audio/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported audio format",
        )

    file_bytes = await audio_file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file is empty",
        )
    if len(file_bytes) > get_settings().voice_max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Audio file is too large",
        )

    try:
        transcription = await transcribe_audio(
            file_bytes=file_bytes,
            file_name=audio_file.filename,
            mime_type=content_type,
            duration_ms=duration_ms,
            source=source,
            use_default_language_hint=use_default_language_hint,
        )
    except STTProviderConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except STTProviderResponseError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    user_message, assistant_message, correction = await chat_in_practice_session(
        session=session,
        user_id=user_id,
        session_id=session_id,
        content=transcription.text,
        user_message_metadata={
            "input_mode": "voice",
            "transcript_provider": transcription.provider,
            "transcript_model": transcription.model,
            "mime_type": transcription.mime_type,
            "duration_ms": transcription.duration_ms,
            "language": transcription.language,
            "source": transcription.source,
            "file_name": transcription.file_name,
        },
    )
    return transcription, user_message, assistant_message, correction
