from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.practice_message import PracticeMessageResponse
from app.schemas.progress import ProgressRecommendedPracticeResponse
from app.schemas.topic import TopicResponse

PracticeMode = Literal[
    "free_chat",
    "guided_topic",
    "roleplay",
    "speaking_practice",
    "translation_practice",
]
PracticeSessionStatus = Literal["active", "completed", "abandoned"]


class PracticeSessionCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    mode: PracticeMode
    topic_id: uuid.UUID | None = None
    title: str | None = Field(default=None, max_length=255)


class PracticeSessionListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    topic_id: uuid.UUID | None
    mode: str
    title: str | None
    status: str
    started_at: datetime
    ended_at: datetime | None
    created_at: datetime
    updated_at: datetime
    topic: TopicResponse | None = None


class PracticeSessionStarterResponse(BaseModel):
    assistant_message: PracticeMessageResponse
    quick_replies: list[str] = Field(default_factory=list)
    is_fresh: bool = True


class PracticeSessionCompletionSummaryResponse(BaseModel):
    title: str
    message: str
    completed_items: int = 0
    average_score: int | None = None
    strongest_area: str | None = None
    focus_area: str | None = None
    recommended_next_practice: ProgressRecommendedPracticeResponse
    auto_completed: bool = False


class PracticeSessionDetailResponse(PracticeSessionListItemResponse):
    messages: list[PracticeMessageResponse]
    starter: PracticeSessionStarterResponse | None = None
    completion_summary: PracticeSessionCompletionSummaryResponse | None = None
