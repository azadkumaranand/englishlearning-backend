from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MistakePatternResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tag: str
    frequency: int
    first_seen_at: datetime
    last_seen_at: datetime
    last_example_original: str | None
    last_example_corrected: str | None
    severity_score: float | None
    created_at: datetime
    updated_at: datetime


class PersonalizationSummaryResponse(BaseModel):
    top_weak_areas: list[str]
    total_corrections_count: int
    average_message_length: float | None
    last_recommended_focus: str | None
    detected_translation_level: str | None = None
    total_translation_items_completed: int = 0
    average_translation_attempts: float | None = None
    translation_first_try_rate: float | None = None


class PersonalizationRecommendationResponse(BaseModel):
    focus_title: str
    short_reason: str
    suggested_action: str
