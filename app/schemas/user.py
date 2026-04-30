from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    native_language: str | None
    english_level: str | None
    learning_goal: str | None
    practice_preference: str | None
    onboarding_completed: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
