from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

DailyPlanTaskType = Literal["translation", "review", "speaking", "conversation"]
DailyPlanTaskStatus = Literal["pending", "completed"]


class DailyPlanTaskResponse(BaseModel):
    id: str
    type: DailyPlanTaskType
    title: str
    description: str
    estimated_minutes: int = Field(ge=1)
    status: DailyPlanTaskStatus = "pending"


class DailyPlanResponse(BaseModel):
    date: date
    title: str
    estimated_minutes: int = Field(ge=1)
    tasks: list[DailyPlanTaskResponse]
