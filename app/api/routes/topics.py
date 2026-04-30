from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.dependencies.auth import get_current_user
from app.schemas.topic import TopicResponse
from app.services.topic_service import get_active_topic_by_id, list_active_topics

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("", response_model=list[TopicResponse])
async def get_topics(
    category: str | None = Query(default=None),
    difficulty_level: str | None = Query(default=None),
    _: object = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[TopicResponse]:
    topics = await list_active_topics(
        session=session,
        category=category,
        difficulty_level=difficulty_level,
    )
    return [TopicResponse.model_validate(topic) for topic in topics]


@router.get("/{topic_id}", response_model=TopicResponse)
async def get_topic(
    topic_id: uuid.UUID,
    _: object = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> TopicResponse:
    topic = await get_active_topic_by_id(session, topic_id)
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
    return TopicResponse.model_validate(topic)

