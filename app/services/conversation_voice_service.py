from __future__ import annotations

import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.schemas.conversation import (
    ConversationReplyRequest,
    ConversationReplyResponse,
    ConversationVoiceReplyResponse,
    ConversationVoiceTranscriptionMetadata,
)
from app.services.conversation_roleplay_service import reply_in_conversation_session
from app.services.stt_provider import (
    STTProviderConfigurationError,
    STTProviderResponseError,
    transcribe_audio,
)
from app.services.voice_chat_service import ALLOWED_AUDIO_CONTENT_TYPES


async def handle_conversation_voice_reply(
    session: AsyncSession,
    *,
    user,
    session_id: uuid.UUID,
    audio_file: UploadFile,
    duration_ms: int | None = None,
    source: str | None = None,
) -> ConversationVoiceReplyResponse:
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
            use_default_language_hint=False,
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

    result: ConversationReplyResponse = await reply_in_conversation_session(
        session=session,
        user=user,
        payload=ConversationReplyRequest(
            session_id=session_id,
            user_message=transcription.text,
        ),
    )

    return ConversationVoiceReplyResponse(
        transcript=transcription.text,
        result=result,
        transcription=ConversationVoiceTranscriptionMetadata(
            provider=transcription.provider,
            model=transcription.model,
            mime_type=transcription.mime_type,
            duration_ms=transcription.duration_ms,
            source=transcription.source,
            language=transcription.language,
            file_name=transcription.file_name,
        ),
    )
