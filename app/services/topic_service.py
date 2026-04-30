from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.topic import Topic

INITIAL_TOPICS: list[dict[str, str | int | bool | None]] = [
    {
        "slug": "introduce-yourself",
        "title": "Introduce Yourself",
        "description": "Practice basic self-introduction in English.",
        "category": "social",
        "difficulty_level": "beginner",
        "sort_order": 1,
    },
    {
        "slug": "daily-life",
        "title": "Daily Life",
        "description": "Talk about your daily routine and everyday habits.",
        "category": "daily_conversation",
        "difficulty_level": "beginner",
        "sort_order": 2,
    },
    {
        "slug": "travel",
        "title": "Travel",
        "description": "Discuss trips, planning, and travel situations.",
        "category": "travel",
        "difficulty_level": "intermediate",
        "sort_order": 3,
    },
    {
        "slug": "job-interview",
        "title": "Job Interview",
        "description": "Prepare for common interview questions and answers.",
        "category": "career",
        "difficulty_level": "intermediate",
        "sort_order": 4,
    },
    {
        "slug": "office-conversation",
        "title": "Office Conversation",
        "description": "Practice workplace discussions and collaboration language.",
        "category": "career",
        "difficulty_level": "intermediate",
        "sort_order": 5,
    },
    {
        "slug": "ordering-food",
        "title": "Ordering Food",
        "description": "Practice restaurant and cafe conversations.",
        "category": "daily_conversation",
        "difficulty_level": "beginner",
        "sort_order": 6,
    },
    {
        "slug": "storytelling",
        "title": "Storytelling",
        "description": "Build confidence telling stories and sharing experiences.",
        "category": "fluency",
        "difficulty_level": "intermediate",
        "sort_order": 7,
    },
    {
        "slug": "debate",
        "title": "Debate",
        "description": "Practice presenting opinions and responding to opposing views.",
        "category": "advanced_speaking",
        "difficulty_level": "advanced",
        "sort_order": 8,
    },
]


async def list_active_topics(
    session: AsyncSession,
    category: str | None = None,
    difficulty_level: str | None = None,
) -> list[Topic]:
    query = select(Topic).where(Topic.is_active.is_(True))
    if category is not None:
        query = query.where(Topic.category == category)
    if difficulty_level is not None:
        query = query.where(Topic.difficulty_level == difficulty_level)
    query = query.order_by(Topic.sort_order.asc(), Topic.title.asc())
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_active_topic_by_id(session: AsyncSession, topic_id: uuid.UUID) -> Topic | None:
    result = await session.execute(
        select(Topic).where(Topic.id == topic_id, Topic.is_active.is_(True))
    )
    return result.scalar_one_or_none()


async def seed_topics(session: AsyncSession) -> int:
    result = await session.execute(select(Topic))
    existing_topics = {topic.slug: topic for topic in result.scalars().all()}

    for topic_data in INITIAL_TOPICS:
        existing = existing_topics.get(topic_data["slug"])
        if existing is None:
            session.add(Topic(**topic_data))
            continue

        existing.title = str(topic_data["title"])
        existing.description = topic_data["description"]  # type: ignore[assignment]
        existing.category = topic_data["category"]  # type: ignore[assignment]
        existing.difficulty_level = topic_data["difficulty_level"]  # type: ignore[assignment]
        existing.is_active = bool(topic_data.get("is_active", True))
        existing.sort_order = int(topic_data.get("sort_order", 0))

    await session.commit()
    return len(INITIAL_TOPICS)

