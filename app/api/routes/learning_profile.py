from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.learning_profile import LearningProfileResponse
from app.services.user_learning_profile_service import build_learning_profile_response

router = APIRouter(prefix="/learning-profile", tags=["learning_profile"])


@router.get("/me", response_model=LearningProfileResponse)
async def get_my_learning_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> LearningProfileResponse:
    return await build_learning_profile_response(session, user=current_user)
