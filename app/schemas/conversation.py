from __future__ import annotations

from datetime import datetime
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ConversationScenario = Literal[
    "job_interview",
    "client_meeting",
    "daily_conversation",
    "ordering_food",
    "travel_airport",
    "introduce_yourself",
    "confidence_practice",
]

ConversationFeedbackLevel = Literal["good", "needs_improvement", "excellent"]
ConversationMistakeType = Literal["grammar", "vocabulary", "sentence_structure", "spelling", "tense"]


class ConversationStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    scenario: ConversationScenario


class ConversationStartResponse(BaseModel):
    session_id: uuid.UUID
    scenario: ConversationScenario
    level: str
    title: str
    ai_message: str
    goal: str
    max_turns: int


class ConversationSessionStateResponse(BaseModel):
    session_id: uuid.UUID
    status: str
    completed_at: datetime | None = None


class ConversationMistakeResponse(BaseModel):
    type: ConversationMistakeType
    issue: str
    fix: str
    reason: str


class ConversationSummaryResponse(BaseModel):
    average_score: int
    best_area: str
    weak_area: str
    tip: str


class ConversationReplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    session_id: uuid.UUID
    user_message: str = Field(min_length=1)


class ConversationReplyResponse(BaseModel):
    turn_number: int
    score: int
    feedback_level: ConversationFeedbackLevel
    corrected_sentence: str
    natural_sentence: str
    mistakes: list[ConversationMistakeResponse]
    encouragement: str
    ai_reply: str
    session_completed: bool
    remaining_turns: int
    summary: ConversationSummaryResponse | None = None


class ConversationVoiceTranscriptionMetadata(BaseModel):
    provider: str
    model: str
    mime_type: str | None = None
    duration_ms: int | None = None
    source: str | None = None
    language: str | None = None
    file_name: str | None = None


class ConversationVoiceReplyResponse(BaseModel):
    transcript: str
    result: ConversationReplyResponse
    transcription: ConversationVoiceTranscriptionMetadata


class ConversationMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    message: str
    score: int | None
    corrected_sentence: str | None
    natural_sentence: str | None
    feedback_json: dict | None
    created_at: datetime
