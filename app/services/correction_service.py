from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message_correction import MessageCorrection
from app.models.practice_message import PracticeMessage
from app.models.practice_session import PracticeSession
from app.schemas.correction import CorrectionAnalysis, get_correction_json_schema
from app.services.ai_provider import (
    AIConversationTurn,
    AIProviderConfigurationError,
    AIProviderParseError,
    AIProviderResponseError,
    generate_structured_json,
)
from app.services.personalization_service import try_update_personalization_after_correction
from app.services.practice_session_service import get_user_practice_session
from app.services.prompt_service import build_correction_prompt


async def generate_message_correction(
    session: AsyncSession,
    *,
    practice_session: PracticeSession,
    user_message: PracticeMessage,
) -> MessageCorrection:
    system_prompt = build_correction_prompt(
        user=practice_session.user,
        learning_profile=practice_session.user.learning_profile,
    )
    provider_result = await generate_structured_json(
        system_prompt=system_prompt,
        conversation=[
            AIConversationTurn(
                role="user",
                content=f"Analyze this learner message and return JSON only:\n{user_message.content}",
            )
        ],
        schema_name="message_correction",
        json_schema=get_correction_json_schema(),
    )
    parsed_correction = CorrectionAnalysis.model_validate(provider_result.data)

    correction = MessageCorrection(
        message_id=user_message.id,
        original_text=user_message.content,
        corrected_text=parsed_correction.corrected,
        explanation=parsed_correction.explanation,
        natural_version=parsed_correction.natural_version,
        retry_prompt=parsed_correction.retry_prompt,
        tags=parsed_correction.tags,
        severity=parsed_correction.severity,
    )
    session.add(correction)
    await session.commit()
    await session.refresh(correction)
    await try_update_personalization_after_correction(
        session=session,
        user_id=practice_session.user_id,
        user_message=user_message,
        correction=correction,
    )
    return correction


async def try_generate_message_correction(
    session: AsyncSession,
    *,
    practice_session: PracticeSession,
    user_message: PracticeMessage,
) -> MessageCorrection | None:
    try:
        return await generate_message_correction(
            session=session,
            practice_session=practice_session,
            user_message=user_message,
        )
    except (
        AIProviderConfigurationError,
        AIProviderResponseError,
        AIProviderParseError,
        ValidationError,
    ):
        return None


async def get_message_correction_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    message_id: uuid.UUID,
) -> MessageCorrection:
    await get_user_practice_session(session, user_id, session_id)

    result = await session.execute(
        select(MessageCorrection)
        .join(PracticeMessage, PracticeMessage.id == MessageCorrection.message_id)
        .where(
            MessageCorrection.message_id == message_id,
            PracticeMessage.session_id == session_id,
        )
    )
    correction = result.scalar_one_or_none()
    if correction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message correction not found",
        )
    return correction
