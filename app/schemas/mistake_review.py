from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typing import Literal

from app.schemas.ai_chat import VoiceTranscriptionMetadata

MistakeType = Literal[
    "tense",
    "grammar",
    "vocabulary",
    "sentence_structure",
    "word_order",
    "meaning",
    "word_by_word_translation",
    "spelling",
]
MistakeStatus = Literal["needs_practice", "improved", "resolved"]
MistakeInputMode = Literal["text", "speech"]


class MistakeReviewItemResponse(BaseModel):
    id: str
    type: MistakeType
    wrong_sentence: str
    correct_sentence: str
    explanation: str
    retry_question: str
    focus_area: MistakeType
    seen_count: int
    status: MistakeStatus


class MistakeReviewListResponse(BaseModel):
    mistakes: list[MistakeReviewItemResponse]


class MistakeRetryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    mistake_id: str
    retry_answer: str
    input_mode: MistakeInputMode


class MistakeRetryResponse(BaseModel):
    is_improved: bool
    score: int
    correct_answer: str
    natural_answer: str
    feedback: str
    remaining_issue: str | None
    status: Literal["improved", "needs_more_practice"]


class MistakeRetryVoiceResponse(BaseModel):
    transcript: str
    result: MistakeRetryResponse
    transcription: VoiceTranscriptionMetadata
