from __future__ import annotations

from collections.abc import AsyncIterator
import uuid
from typing import Any

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message_correction import MessageCorrection
from app.models.practice_message import PracticeMessage
from app.schemas.ai_chat import FreeChatReplyAnalysis, get_free_chat_reply_json_schema
from app.services.ai_provider import (
    AIConversationTurn,
    AIProviderConfigurationError,
    AIProviderParseError,
    AIProviderResponseError,
    generate_ai_reply,
    stream_ai_reply,
    generate_structured_json,
)
from app.services.correction_service import try_generate_message_correction
from app.services.personalization_service import get_personalization_summary
from app.services.prompt_service import build_conversation_prompt
from app.services.practice_session_service import (
    create_practice_message,
    get_user_practice_session,
    list_recent_practice_messages,
)
from app.services.translation_practice_service import handle_translation_practice_turn


def _serialize_history(messages: list[PracticeMessage], limit: int = 12) -> list[AIConversationTurn]:
    trimmed = messages[-limit:] if len(messages) > limit else messages
    return [AIConversationTurn(role=message.role, content=message.content) for message in trimmed]


async def _generate_free_chat_reply(
    *,
    system_prompt: str,
    conversation: list[AIConversationTurn],
) -> tuple[FreeChatReplyAnalysis, dict[str, str | bool | None]]:
    provider_result = await generate_structured_json(
        system_prompt=system_prompt,
        conversation=conversation,
        schema_name="free_chat_reply",
        json_schema=get_free_chat_reply_json_schema(),
    )
    analysis = FreeChatReplyAnalysis.model_validate(provider_result.data)
    metadata: dict[str, str | bool | None] = {
        "provider": provider_result.provider,
        "model": provider_result.model,
        "response_id": provider_result.response_id,
        "response_language": analysis.reply_language,
        "response_language_code": analysis.reply_language_code,
        "detected_user_language": analysis.detected_user_language,
        "detected_user_language_code": analysis.detected_user_language_code,
        "mirrored_tone": analysis.tone,
    }
    return analysis, metadata


async def chat_in_practice_session(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    content: str,
    user_message_metadata: dict | None = None,
) -> tuple[PracticeMessage, PracticeMessage, MessageCorrection | None, Any | None]:
    practice_session = await get_user_practice_session(
        session=session,
        user_id=user_id,
        session_id=session_id,
        include_messages=True,
        include_user_context=True,
    )
    if practice_session.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Practice session is not active",
        )

    if practice_session.mode == "translation_practice":
        return await handle_translation_practice_turn(
            session=session,
            practice_session=practice_session,
            content=content,
            user_message_metadata=user_message_metadata,
        )

    user_message = await create_practice_message(
        session=session,
        practice_session=practice_session,
        role="user",
        content=content,
        metadata_json=user_message_metadata,
    )
    recent_messages = await list_recent_practice_messages(session, session_id=session_id)
    serialized_history = _serialize_history(recent_messages)
    learning_summary = await get_personalization_summary(session, user_id=user_id)

    system_prompt = build_conversation_prompt(
        user=practice_session.user,
        learning_profile=practice_session.user.learning_profile,
        practice_session=practice_session,
        history=recent_messages,
        learning_summary=learning_summary,
    )

    try:
        assistant_metadata: dict | None
        should_generate_correction = True
        if practice_session.mode == "free_chat":
            free_chat_reply, assistant_metadata = await _generate_free_chat_reply(
                system_prompt=system_prompt,
                conversation=serialized_history,
            )
            assistant_content = free_chat_reply.reply
            should_generate_correction = free_chat_reply.should_correct_english
        else:
            provider_result = await generate_ai_reply(
                system_prompt=system_prompt,
                conversation=serialized_history,
            )
            assistant_content = provider_result.content
            assistant_metadata = {
                "provider": provider_result.provider,
                "model": provider_result.model,
                "response_id": provider_result.response_id,
            }
    except (AIProviderConfigurationError, AIProviderResponseError, AIProviderParseError, ValidationError) as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_502_BAD_GATEWAY
                if isinstance(exc, (AIProviderResponseError, AIProviderParseError, ValidationError))
                else status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=str(exc),
        ) from exc

    assistant_message = await create_practice_message(
        session=session,
        practice_session=practice_session,
        role="assistant",
        content=assistant_content,
        metadata_json=assistant_metadata,
    )
    correction = (
        await try_generate_message_correction(
            session=session,
            practice_session=practice_session,
            user_message=user_message,
        )
        if should_generate_correction
        else None
    )

    return user_message, assistant_message, correction, None


async def stream_chat_in_practice_session(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    content: str,
    user_message_metadata: dict | None = None,
) -> AsyncIterator[dict[str, Any]]:
    practice_session = await get_user_practice_session(
        session=session,
        user_id=user_id,
        session_id=session_id,
        include_messages=True,
        include_user_context=True,
    )
    if practice_session.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Practice session is not active",
        )

    if practice_session.mode == "translation_practice":
        yield {
            "type": "status",
            "phase": "received",
            "message": "Checking your translation...",
        }
        yield {
            "type": "status",
            "phase": "evaluating",
            "message": "Reviewing grammar and meaning...",
        }
        user_message, assistant_message, correction, completion_summary = await handle_translation_practice_turn(
            session=session,
            practice_session=practice_session,
            content=content,
            user_message_metadata=user_message_metadata,
        )
        yield {
            "type": "final",
            "session_id": session_id,
            "user_message": user_message,
            "assistant_message": assistant_message,
            "correction": correction,
            "completion_summary": completion_summary,
        }
        return

    user_message = await create_practice_message(
        session=session,
        practice_session=practice_session,
        role="user",
        content=content,
        metadata_json=user_message_metadata,
    )
    recent_messages = await list_recent_practice_messages(session, session_id=session_id)
    serialized_history = _serialize_history(recent_messages)
    learning_summary = await get_personalization_summary(session, user_id=user_id)
    system_prompt = build_conversation_prompt(
        user=practice_session.user,
        learning_profile=practice_session.user.learning_profile,
        practice_session=practice_session,
        history=recent_messages,
        learning_summary=learning_summary,
    )

    try:
        assistant_metadata: dict | None
        should_generate_correction = True
        if practice_session.mode == "free_chat":
            yield {
                "type": "status",
                "phase": "replying",
                "message": "Preparing a reply in the same language...",
            }
            free_chat_reply, assistant_metadata = await _generate_free_chat_reply(
                system_prompt=system_prompt,
                conversation=serialized_history,
            )
            assistant_content = free_chat_reply.reply
            should_generate_correction = free_chat_reply.should_correct_english
        else:
            yield {
                "type": "status",
                "phase": "replying",
                "message": "Coach is typing...",
            }
            assistant_content = ""
            provider_name: str | None = None
            model_name: str | None = None
            response_id: str | None = None
            async for provider_event in stream_ai_reply(
                system_prompt=system_prompt,
                conversation=serialized_history,
            ):
                if hasattr(provider_event, "delta"):
                    assistant_content = provider_event.snapshot
                    yield {
                        "type": "assistant_delta",
                        "delta": provider_event.delta,
                        "snapshot": provider_event.snapshot,
                    }
                else:
                    assistant_content = provider_event.content
                    provider_name = provider_event.provider
                    model_name = provider_event.model
                    response_id = provider_event.response_id
            assistant_metadata = {
                "provider": provider_name,
                "model": model_name,
                "response_id": response_id,
            }
    except (AIProviderConfigurationError, AIProviderResponseError, AIProviderParseError, ValidationError) as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_502_BAD_GATEWAY
                if isinstance(exc, (AIProviderResponseError, AIProviderParseError, ValidationError))
                else status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=str(exc),
        ) from exc

    if should_generate_correction:
        yield {
            "type": "status",
            "phase": "feedback",
            "message": "Preparing your feedback...",
        }

    assistant_message = await create_practice_message(
        session=session,
        practice_session=practice_session,
        role="assistant",
        content=assistant_content,
        metadata_json=assistant_metadata,
    )
    correction = (
        await try_generate_message_correction(
            session=session,
            practice_session=practice_session,
            user_message=user_message,
        )
        if should_generate_correction
        else None
    )
    yield {
        "type": "final",
        "session_id": session_id,
        "user_message": user_message,
        "assistant_message": assistant_message,
        "correction": correction,
        "completion_summary": None,
    }
