from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

MessageRole = Literal["user", "assistant"]


class PracticeMessageCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    role: MessageRole
    content: str = Field(min_length=1)


class PracticeMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    message_order: int
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

