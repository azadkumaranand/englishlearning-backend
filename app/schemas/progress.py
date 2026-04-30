from __future__ import annotations

from pydantic import BaseModel

from app.schemas.learning_profile import LearningProfileAreaResponse


class ProgressRecommendedPracticeResponse(BaseModel):
    type: str
    title: str


class ProgressResponse(BaseModel):
    overall_score: int
    average_translation_score: int
    average_conversation_score: int
    total_practice_sessions: int
    total_questions_answered: int
    total_conversations: int
    streak_days: int
    top_weak_areas: list[LearningProfileAreaResponse]
    recent_improvements: list[str]
    recommended_next_practice: ProgressRecommendedPracticeResponse
