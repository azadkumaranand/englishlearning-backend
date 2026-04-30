from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LearningProfileAreaResponse(BaseModel):
    type: str
    count: int
    label: str


class LearningProfileMistakeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str
    label: str
    wrong: str
    correct: str
    count: int
    last_seen_at: datetime


class LearningProfileResponse(BaseModel):
    average_score: int
    average_conversation_score: int
    speaking_confidence_score: int
    total_conversation_turns: int
    total_practice_sessions: int
    total_attempts: int
    total_correct_attempts: int
    weak_areas: list[LearningProfileAreaResponse]
    strong_areas: list[LearningProfileAreaResponse]
    repeated_mistakes: list[LearningProfileMistakeResponse]
    recent_mistakes: list[LearningProfileMistakeResponse]
    recommended_focus_area: str | None
    current_difficulty: str
    summary: str
