from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.personalization import (
    MistakePatternResponse,
    PersonalizationRecommendationResponse,
    PersonalizationSummaryResponse,
)
from app.services.personalization_service import (
    get_personalization_recommendation,
    get_personalization_summary,
    list_user_mistake_patterns,
)

router = APIRouter(prefix="/personalization", tags=["personalization"])


@router.get("/summary", response_model=PersonalizationSummaryResponse)
async def get_summary(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PersonalizationSummaryResponse:
    summary = await get_personalization_summary(session, user_id=current_user.id)
    if summary is None:
        return PersonalizationSummaryResponse(
            top_weak_areas=[],
            total_corrections_count=0,
            average_message_length=None,
            last_recommended_focus=None,
            detected_translation_level=None,
            total_translation_items_completed=0,
            average_translation_attempts=None,
            translation_first_try_rate=None,
        )
    return PersonalizationSummaryResponse(
        top_weak_areas=summary.top_weak_areas,
        total_corrections_count=summary.total_corrections_count,
        average_message_length=summary.average_message_length,
        last_recommended_focus=summary.last_recommended_focus,
        detected_translation_level=summary.detected_translation_level,
        total_translation_items_completed=summary.total_translation_items_completed,
        average_translation_attempts=summary.average_translation_attempts,
        translation_first_try_rate=(
            round(
                summary.translation_first_try_success_count / summary.total_translation_items_completed,
                2,
            )
            if summary.total_translation_items_completed
            else None
        ),
    )


@router.get("/recommendation", response_model=PersonalizationRecommendationResponse)
async def get_recommendation(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PersonalizationRecommendationResponse:
    recommendation = await get_personalization_recommendation(session, user_id=current_user.id)
    return PersonalizationRecommendationResponse(
        focus_title=recommendation.focus_title,
        short_reason=recommendation.short_reason,
        suggested_action=recommendation.suggested_action,
    )


@router.get("/mistakes", response_model=list[MistakePatternResponse])
async def get_mistakes(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[MistakePatternResponse]:
    patterns = await list_user_mistake_patterns(
        session=session,
        user_id=current_user.id,
        limit=limit,
    )
    return [MistakePatternResponse.model_validate(pattern) for pattern in patterns]
