from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EnglishLevelValue = Literal["beginner", "intermediate", "advanced", "not_sure"]
LearningGoalValue = Literal[
    "daily_conversation",
    "job_interview",
    "business_english",
    "travel_english",
    "exam_preparation",
    "confidence_building",
]
PracticePreferenceValue = Literal["speaking", "writing", "both"]
FirstPlanTaskType = Literal["translation", "speaking", "conversation"]


class OnboardingCompleteRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    native_language: str = Field(min_length=1, max_length=100)
    english_level: EnglishLevelValue
    learning_goal: LearningGoalValue
    practice_preference: PracticePreferenceValue


class OnboardingResponse(BaseModel):
    user_id: uuid.UUID
    native_language: str | None = None
    english_level: EnglishLevelValue | None = None
    learning_goal: LearningGoalValue | None = None
    practice_preference: PracticePreferenceValue | None = None
    onboarding_completed: bool = False


class FirstPlanTaskResponse(BaseModel):
    type: FirstPlanTaskType
    title: str
    estimated_minutes: int = Field(ge=1)


class FirstPlanResponse(BaseModel):
    title: str
    description: str
    tasks: list[FirstPlanTaskResponse]


class OnboardingCompleteResponse(BaseModel):
    success: bool = True
    onboarding: OnboardingResponse
    first_plan: FirstPlanResponse
