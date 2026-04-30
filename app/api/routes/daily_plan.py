from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.daily_plan import DailyPlanResponse
from app.services.daily_plan_service import build_daily_plan_for_user

router = APIRouter(prefix="/daily-plan", tags=["daily_plan"])


@router.get("/me", response_model=DailyPlanResponse)
async def get_my_daily_plan(
    current_user: User = Depends(get_current_user),
) -> DailyPlanResponse:
    return await build_daily_plan_for_user(current_user)
