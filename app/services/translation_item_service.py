from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect as sa_inspect

from app.models.practice_session import PracticeSession
from app.models.practice_translation_item import PracticeTranslationItem


async def get_active_translation_item(
    session: AsyncSession,
    *,
    session_id: uuid.UUID,
) -> PracticeTranslationItem | None:
    result = await session.execute(
        select(PracticeTranslationItem)
        .where(
            PracticeTranslationItem.session_id == session_id,
            PracticeTranslationItem.status == "active",
        )
        .order_by(PracticeTranslationItem.order_index.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_completed_translation_source_sentences(
    session: AsyncSession,
    *,
    session_id: uuid.UUID,
) -> list[str]:
    result = await session.execute(
        select(PracticeTranslationItem.source_sentence)
        .where(
            PracticeTranslationItem.session_id == session_id,
            PracticeTranslationItem.status == "completed",
        )
        .order_by(PracticeTranslationItem.order_index.asc())
    )
    return list(result.scalars().all())


async def create_translation_item(
    session: AsyncSession,
    *,
    practice_session: PracticeSession,
    source_sentence: str,
    reference_translation: str,
    assistant_prompt: str,
    focus_tag: str | None = None,
    generator_metadata: dict[str, Any] | None = None,
) -> PracticeTranslationItem:
    result = await session.execute(
        select(func.max(PracticeTranslationItem.order_index)).where(
            PracticeTranslationItem.session_id == practice_session.id
        )
    )
    max_order = result.scalar_one()
    next_order = (max_order or 0) + 1

    translation_item = PracticeTranslationItem(
        session_id=practice_session.id,
        order_index=next_order,
        source_sentence=source_sentence,
        reference_translation=reference_translation,
        assistant_prompt=assistant_prompt,
        focus_tag=focus_tag,
        status="active",
        generator_metadata=generator_metadata,
    )
    session.add(translation_item)
    await session.commit()
    await session.refresh(translation_item)
    return translation_item


async def record_translation_item_retry(
    session: AsyncSession,
    *,
    translation_item: PracticeTranslationItem,
    learner_answer: str,
) -> PracticeTranslationItem:
    translation_item_id = sa_inspect(translation_item).identity[0]
    await session.execute(
        update(PracticeTranslationItem)
        .where(PracticeTranslationItem.id == translation_item_id)
        .values(
            attempt_count=PracticeTranslationItem.attempt_count + 1,
            last_learner_answer=learner_answer,
        )
    )
    await session.commit()
    await session.refresh(translation_item)
    return translation_item


async def mark_translation_item_completed(
    session: AsyncSession,
    *,
    translation_item: PracticeTranslationItem,
    learner_answer: str,
) -> PracticeTranslationItem:
    translation_item_id = sa_inspect(translation_item).identity[0]
    await session.execute(
        update(PracticeTranslationItem)
        .where(PracticeTranslationItem.id == translation_item_id)
        .values(
            status="completed",
            attempt_count=PracticeTranslationItem.attempt_count + 1,
            last_learner_answer=learner_answer,
            completed_at=datetime.now(timezone.utc),
        )
    )
    await session.commit()
    await session.refresh(translation_item)
    return translation_item
