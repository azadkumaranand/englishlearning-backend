from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.onboarding import (
    OnboardingCompleteRequest,
    OnboardingCompleteResponse,
    OnboardingResponse,
)
from app.services.user_service import complete_onboarding, get_user_with_learning_profile

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def _build_onboarding_response(user: User) -> OnboardingResponse:
    return OnboardingResponse(
        user_id=user.id,
        native_language=user.native_language,
        english_level=user.english_level,
        learning_goal=user.learning_goal,
        practice_preference=user.practice_preference,
        onboarding_completed=user.onboarding_completed,
    )


@router.get("", response_model=OnboardingResponse)
async def get_onboarding(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> OnboardingResponse:
    user = await get_user_with_learning_profile(session, current_user.id)
    if user is None:
        user = current_user
    return _build_onboarding_response(user)


@router.post("/complete", response_model=OnboardingCompleteResponse)
async def save_onboarding(
    payload: OnboardingCompleteRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> OnboardingCompleteResponse:
    user, profile, first_plan = await complete_onboarding(session, current_user, payload)
    user.learning_profile = profile
    return OnboardingCompleteResponse(
        success=True,
        onboarding=_build_onboarding_response(user),
        first_plan=first_plan,
    )
