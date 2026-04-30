from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.correction import MessageCorrectionResponse, build_message_correction_response
from app.services.correction_service import get_message_correction_for_user

router = APIRouter(prefix="/practice/sessions", tags=["corrections"])


@router.get(
    "/{session_id}/messages/{message_id}/correction",
    response_model=MessageCorrectionResponse,
)
async def get_message_correction(
    session_id: uuid.UUID,
    message_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> MessageCorrectionResponse:
    try:
        parsed_message_id = uuid.UUID(message_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message correction not found",
        ) from exc

    correction = await get_message_correction_for_user(
        session=session,
        user_id=current_user.id,
        session_id=session_id,
        message_id=parsed_message_id,
    )
    return build_message_correction_response(correction)
