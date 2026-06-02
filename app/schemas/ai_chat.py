from __future__ import annotations

from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.correction import MessageCorrectionResponse
from app.schemas.practice_message import PracticeMessageResponse
from app.schemas.practice_session import PracticeSessionCompletionSummaryResponse


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    content: str = Field(min_length=1)
    metadata_json: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    session_id: uuid.UUID
    user_message: PracticeMessageResponse
    assistant_message: PracticeMessageResponse
    correction: MessageCorrectionResponse | None = None
    completion_summary: PracticeSessionCompletionSummaryResponse | None = None


class VoiceTranscriptionMetadata(BaseModel):
    provider: str
    model: str
    mime_type: str | None = None
    duration_ms: int | None = None
    source: str | None = None
    language: str | None = None
    file_name: str | None = None


class VoiceChatResponse(BaseModel):
    session_id: uuid.UUID
    transcript: str
    user_message: PracticeMessageResponse
    assistant_message: PracticeMessageResponse
    correction: MessageCorrectionResponse | None = None
    transcription: VoiceTranscriptionMetadata


class FreeChatReplyAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reply: str = Field(min_length=1)
    reply_language: str = Field(min_length=1)
    reply_language_code: str | None = None
    detected_user_language: str = Field(min_length=1)
    detected_user_language_code: str | None = None
    tone: str = Field(min_length=1)
    should_correct_english: bool


def get_free_chat_reply_json_schema() -> dict[str, Any]:
    nullable_string = {"anyOf": [{"type": "string"}, {"type": "null"}]}
    return {
        "type": "object",
        "properties": {
            "reply": {"type": "string"},
            "reply_language": {"type": "string"},
            "reply_language_code": nullable_string,
            "detected_user_language": {"type": "string"},
            "detected_user_language_code": nullable_string,
            "tone": {"type": "string"},
            "should_correct_english": {"type": "boolean"},
        },
        "required": [
            "reply",
            "reply_language",
            "reply_language_code",
            "detected_user_language",
            "detected_user_language_code",
            "tone",
            "should_correct_english",
        ],
        "additionalProperties": False,
    }
