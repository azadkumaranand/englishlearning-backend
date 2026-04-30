from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TopicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title: str
    description: str | None
    category: str | None
    difficulty_level: str | None
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

