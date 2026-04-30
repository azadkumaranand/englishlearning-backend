from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.mistake_review import (
    MistakeReviewListResponse,
    MistakeRetryRequest,
    MistakeRetryResponse,
    MistakeRetryVoiceResponse,
)
from app.services.mistake_review_service import (
    get_mistake_review_payload,
    submit_mistake_retry,
    submit_voice_mistake_retry,
)

router = APIRouter(prefix="/mistakes", tags=["mistakes"])


@router.get("/review", response_model=MistakeReviewListResponse)
async def get_review_mistakes(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> MistakeReviewListResponse:
    return await get_mistake_review_payload(session, user=current_user)


@router.post("/retry", response_model=MistakeRetryResponse)
async def retry_mistake(
    payload: MistakeRetryRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> MistakeRetryResponse:
    return await submit_mistake_retry(session, user=current_user, payload=payload)


@router.post("/retry/voice", response_model=MistakeRetryVoiceResponse)
async def retry_mistake_with_voice(
    mistake_id: str = Form(...),
    audio: UploadFile = File(...),
    duration_ms: int | None = Form(default=None),
    source: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> MistakeRetryVoiceResponse:
    return await submit_voice_mistake_retry(
        session,
        user=current_user,
        mistake_id=mistake_id,
        audio_file=audio,
        duration_ms=duration_ms,
        source=source,
    )
