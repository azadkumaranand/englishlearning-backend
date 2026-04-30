from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime, timezone
import re

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message_correction import MessageCorrection
from app.models.practice_message import PracticeMessage
from app.models.user_learning_summary import UserLearningSummary
from app.models.user_mistake_pattern import UserMistakePattern
from app.services.recommendation_service import FocusRecommendation, build_focus_recommendation

_MAX_COMPLETED_TRANSLATION_HISTORY = 75
_LEVEL_ORDER = ["beginner", "intermediate", "advanced"]


def _normalize_tags(tags: Sequence[str] | None) -> list[str]:
    if not tags:
        return []
    normalized: list[str] = []
    for tag in tags:
        value = tag.strip().lower()
        if value and value not in normalized:
            normalized.append(value)
    return normalized


def _severity_to_score(severity: str) -> float:
    return {
        "none": 0.0,
        "low": 1.0,
        "medium": 2.0,
        "high": 3.0,
    }.get(severity, 1.0)


def _estimate_message_length(content: str) -> int:
    words = [word for word in content.split() if word]
    return len(words)


def _normalize_completed_translation_sentence(value: str) -> str:
    return " ".join(value.split()).strip()


def _translation_sentence_key(value: str) -> str:
    lowered = _normalize_completed_translation_sentence(value).lower()
    lowered = re.sub(r"[^\w\s]", " ", lowered, flags=re.UNICODE)
    return " ".join(lowered.split()).strip()


def _normalize_level_value(level: str | None) -> str | None:
    if not level:
        return None
    normalized = level.strip().lower()
    return normalized if normalized in _LEVEL_ORDER else None


def _level_rank(level: str | None) -> int:
    normalized = _normalize_level_value(level)
    if normalized is None:
        return 0
    return _LEVEL_ORDER.index(normalized)


def _level_from_rank(rank: int) -> str:
    bounded_rank = min(max(rank, 0), len(_LEVEL_ORDER) - 1)
    return _LEVEL_ORDER[bounded_rank]


def _detect_translation_level(
    *,
    preferred_level: str | None,
    completed_count: int,
    total_attempts: int,
    first_try_success_count: int,
    top_weak_areas: Sequence[str] | None,
) -> str:
    base_rank = _level_rank(preferred_level)
    if completed_count <= 0:
        return _level_from_rank(base_rank)

    average_attempts = total_attempts / completed_count if completed_count else 0.0
    first_try_rate = first_try_success_count / completed_count if completed_count else 0.0
    weak_area_count = len([tag for tag in (top_weak_areas or []) if tag.strip()])

    adjusted_rank = base_rank
    if completed_count >= 12 and average_attempts <= 1.3 and first_try_rate >= 0.7:
        adjusted_rank = max(adjusted_rank, 2)
    elif completed_count >= 5 and average_attempts <= 1.55 and first_try_rate >= 0.55:
        adjusted_rank = max(adjusted_rank, 1)

    if completed_count >= 4 and average_attempts >= 2.4 and weak_area_count >= 2:
        adjusted_rank = min(adjusted_rank, 0)
    elif completed_count >= 4 and average_attempts >= 1.95 and adjusted_rank > 0:
        adjusted_rank -= 1

    return _level_from_rank(adjusted_rank)


async def _get_top_weak_areas(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int = 3,
) -> list[str]:
    result = await session.execute(
        select(UserMistakePattern.tag)
        .where(UserMistakePattern.user_id == user_id)
        .order_by(
            UserMistakePattern.frequency.desc(),
            UserMistakePattern.severity_score.desc().nullslast(),
            UserMistakePattern.last_seen_at.desc(),
        )
        .limit(limit)
    )
    return list(result.scalars().all())


async def _get_learning_summary_record(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> UserLearningSummary | None:
    result = await session.execute(
        select(UserLearningSummary).where(UserLearningSummary.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def _get_or_create_learning_summary_record(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> UserLearningSummary:
    summary = await _get_learning_summary_record(session, user_id=user_id)
    if summary is not None:
        return summary

    summary = UserLearningSummary(
        user_id=user_id,
        top_weak_areas=[],
        total_corrections_count=0,
        completed_translation_sources=[],
        total_translation_items_completed=0,
        total_translation_attempts=0,
        translation_first_try_success_count=0,
        average_translation_attempts=None,
        detected_translation_level=None,
    )
    session.add(summary)
    await session.flush()
    return summary


async def update_personalization_after_correction(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    user_message: PracticeMessage,
    correction: MessageCorrection,
) -> None:
    now = datetime.now(timezone.utc)
    normalized_tags = _normalize_tags(correction.tags)
    severity_score = _severity_to_score(correction.severity)
    existing_patterns: dict[str, UserMistakePattern] = {}
    if normalized_tags:
        existing_patterns_result = await session.execute(
            select(UserMistakePattern).where(
                UserMistakePattern.user_id == user_id,
                UserMistakePattern.tag.in_(normalized_tags),
            )
        )
        existing_patterns = {
            pattern.tag: pattern for pattern in existing_patterns_result.scalars().all()
        }

    for tag in normalized_tags:
        pattern = existing_patterns.get(tag)
        if pattern is None:
            session.add(
                UserMistakePattern(
                    user_id=user_id,
                    tag=tag,
                    frequency=1,
                    first_seen_at=now,
                    last_seen_at=now,
                    last_example_original=correction.original_text,
                    last_example_corrected=correction.corrected_text,
                    severity_score=severity_score,
                )
            )
            continue

        previous_frequency = pattern.frequency
        pattern.frequency = previous_frequency + 1
        pattern.last_seen_at = now
        pattern.last_example_original = correction.original_text
        pattern.last_example_corrected = correction.corrected_text
        previous_score = pattern.severity_score or 0.0
        pattern.severity_score = round(
            ((previous_score * previous_frequency) + severity_score) / pattern.frequency,
            2,
        )

    summary = await _get_or_create_learning_summary_record(session, user_id=user_id)
    message_length = _estimate_message_length(user_message.content)
    previous_count = summary.total_corrections_count
    summary.total_corrections_count = previous_count + 1
    if summary.average_message_length is None:
        summary.average_message_length = float(message_length)
    else:
        summary.average_message_length = round(
            ((summary.average_message_length * previous_count) + message_length)
            / summary.total_corrections_count,
            2,
        )

    top_weak_areas = await _get_top_weak_areas(session, user_id=user_id)
    summary.top_weak_areas = top_weak_areas
    recommendation = build_focus_recommendation(top_weak_areas)
    summary.last_recommended_focus = recommendation.focus_title

    await session.commit()
    await session.refresh(summary)


async def record_completed_translation_item(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    source_sentence: str,
    attempts_used: int,
    preferred_level: str | None,
) -> None:
    normalized_sentence = _normalize_completed_translation_sentence(source_sentence)
    if not normalized_sentence:
        return

    summary = await _get_or_create_learning_summary_record(session, user_id=user_id)
    existing_sentences = list(summary.completed_translation_sources or [])
    normalized_key = _translation_sentence_key(normalized_sentence)
    existing_keys = {_translation_sentence_key(sentence) for sentence in existing_sentences}
    total_completed = summary.total_translation_items_completed or 0
    total_attempt_count = summary.total_translation_attempts or 0
    first_try_success_count = summary.translation_first_try_success_count or 0

    if normalized_key not in existing_keys:
        existing_sentences.append(normalized_sentence)
        summary.completed_translation_sources = existing_sentences[-_MAX_COMPLETED_TRANSLATION_HISTORY:]
        total_completed += 1
        total_attempt_count += max(attempts_used, 1)
        if attempts_used <= 1:
            first_try_success_count += 1

    summary.total_translation_items_completed = total_completed
    summary.total_translation_attempts = total_attempt_count
    summary.translation_first_try_success_count = first_try_success_count
    summary.average_translation_attempts = (
        round(total_attempt_count / total_completed, 2) if total_completed else None
    )
    summary.detected_translation_level = _detect_translation_level(
        preferred_level=preferred_level,
        completed_count=total_completed,
        total_attempts=total_attempt_count,
        first_try_success_count=first_try_success_count,
        top_weak_areas=summary.top_weak_areas,
    )
    await session.commit()


def get_effective_translation_level(
    *,
    preferred_level: str | None,
    learning_summary: UserLearningSummary | None,
) -> str | None:
    if learning_summary is not None and learning_summary.detected_translation_level:
        return learning_summary.detected_translation_level
    return _normalize_level_value(preferred_level) or preferred_level


async def try_update_personalization_after_correction(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    user_message: PracticeMessage,
    correction: MessageCorrection,
) -> None:
    try:
        await update_personalization_after_correction(
            session=session,
            user_id=user_id,
            user_message=user_message,
            correction=correction,
        )
    except Exception:
        await session.rollback()


async def get_personalization_summary(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> UserLearningSummary | None:
    return await _get_learning_summary_record(session, user_id=user_id)


async def list_user_mistake_patterns(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int = 20,
) -> list[UserMistakePattern]:
    result = await session.execute(
        select(UserMistakePattern)
        .where(UserMistakePattern.user_id == user_id)
        .order_by(
            UserMistakePattern.frequency.desc(),
            desc(UserMistakePattern.severity_score).nullslast(),
            UserMistakePattern.last_seen_at.desc(),
        )
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_personalization_recommendation(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> FocusRecommendation:
    summary = await _get_learning_summary_record(session, user_id=user_id)
    top_weak_areas = summary.top_weak_areas if summary is not None else []
    return build_focus_recommendation(top_weak_areas)
