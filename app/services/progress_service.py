from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation_message import ConversationMessage
from app.models.conversation_session import ConversationSession
from app.models.message_correction import MessageCorrection
from app.models.mistake_review import MistakeReview
from app.models.practice_message import PracticeMessage
from app.models.practice_session import PracticeSession
from app.models.user import User
from app.schemas.learning_profile import LearningProfileAreaResponse
from app.schemas.progress import ProgressRecommendedPracticeResponse, ProgressResponse
from app.services.user_learning_profile_service import (
    compute_translation_attempt_score,
    get_or_create_user_learning_profile,
    learning_area_label,
    normalize_learning_area,
)

_WINDOW_DAYS = 7


@dataclass(slots=True)
class _TranslationAttemptRecord:
    created_at: datetime
    score: int
    correction: MessageCorrection


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_round(value: float) -> int:
    return int(round(value)) if value > 0 else 0


def _average(values: Iterable[int]) -> int:
    numeric = list(values)
    if not numeric:
        return 0
    return _safe_round(sum(numeric) / len(numeric))


def _start_of_day(value: datetime) -> date:
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return normalized.astimezone(timezone.utc).date()


def _current_streak(activity_dates: set[date]) -> int:
    if not activity_dates:
        return 0

    today = _now().date()
    streak = 0
    cursor = today
    while cursor in activity_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _window_average(
    rows: Iterable[tuple[datetime, int]],
    *,
    days: int = _WINDOW_DAYS,
    offset_days: int = 0,
) -> int:
    end = _now() - timedelta(days=offset_days)
    start = end - timedelta(days=days)
    scores = [
        score
        for created_at, score in rows
        if start <= created_at < end
    ]
    return _average(scores)


def _recent_improvements(
    *,
    translation_rows: list[_TranslationAttemptRecord],
    conversation_rows: list[tuple[datetime, int]],
    mistake_reviews: list[MistakeReview],
) -> list[str]:
    improvements: list[str] = []

    translation_pairs = [(row.created_at, row.score) for row in translation_rows]
    current_translation = _window_average(translation_pairs, offset_days=0)
    previous_translation = _window_average(translation_pairs, offset_days=_WINDOW_DAYS)
    if previous_translation > 0 and current_translation >= previous_translation + 5:
        improvements.append(
            f"Your average translation score improved by {current_translation - previous_translation}% this week."
        )

    current_conversation = _window_average(conversation_rows, offset_days=0)
    previous_conversation = _window_average(conversation_rows, offset_days=_WINDOW_DAYS)
    if previous_conversation > 0 and current_conversation >= previous_conversation + 5:
        improvements.append(
            f"Your conversation score improved by {current_conversation - previous_conversation}% this week."
        )

    recent_review_count = sum(
        1
        for review in mistake_reviews
        if review.is_improved and review.created_at >= _now() - timedelta(days=_WINDOW_DAYS)
    )
    if recent_review_count > 0:
        suffix = "mistake" if recent_review_count == 1 else "mistakes"
        improvements.append(f"You fixed {recent_review_count} {suffix} in review this week.")

    if not improvements and translation_rows:
        recent_translation_scores = [row.score for row in translation_rows[-5:]]
        if recent_translation_scores and _average(recent_translation_scores) >= 75:
            improvements.append("Your recent translation answers are becoming more accurate.")

    if not improvements and conversation_rows:
        recent_conversation_scores = [score for _, score in conversation_rows[-5:]]
        if recent_conversation_scores and _average(recent_conversation_scores) >= 70:
            improvements.append("Your recent speaking replies sound more confident and complete.")

    if not improvements and (translation_rows or conversation_rows or mistake_reviews):
        improvements.append("You are building consistency, and that makes future practice more personal.")

    return improvements[:2]


def _recommended_next_practice(
    *,
    recommended_focus_area: str | None,
    repeated_mistakes_count: int,
    average_translation_score: int,
    average_conversation_score: int,
    practice_preference: str | None,
) -> ProgressRecommendedPracticeResponse:
    focus_area = normalize_learning_area(recommended_focus_area)
    focus_label = learning_area_label(focus_area).lower()

    if repeated_mistakes_count > 0 and focus_area:
        return ProgressRecommendedPracticeResponse(
            type="mistake_review",
            title=f"Review {focus_label} mistakes",
        )

    if practice_preference == "speaking" or (
        average_conversation_score > 0 and average_conversation_score < max(average_translation_score, 70)
    ):
        return ProgressRecommendedPracticeResponse(
            type="roleplay_speaking",
            title="Start a roleplay speaking session",
        )

    return ProgressRecommendedPracticeResponse(
        type="translation_practice",
        title=f"Practice {focus_label}" if focus_area else "Start translation practice",
    )


async def _fetch_translation_attempts(
    session: AsyncSession,
    *,
    user_id: object,
) -> list[_TranslationAttemptRecord]:
    result = await session.execute(
        select(MessageCorrection)
        .join(PracticeMessage, PracticeMessage.id == MessageCorrection.message_id)
        .join(PracticeSession, PracticeSession.id == PracticeMessage.session_id)
        .where(
            PracticeSession.user_id == user_id,
            PracticeSession.mode == "translation_practice",
        )
        .order_by(MessageCorrection.created_at.asc())
    )
    corrections = list(result.scalars().all())
    return [
        _TranslationAttemptRecord(
            created_at=correction.created_at,
            score=compute_translation_attempt_score(
                correction=correction,
                is_correct=correction.severity == "none",
            ),
            correction=correction,
        )
        for correction in corrections
    ]


async def _fetch_conversation_scores(
    session: AsyncSession,
    *,
    user_id: object,
) -> list[tuple[datetime, int]]:
    result = await session.execute(
        select(ConversationMessage.created_at, ConversationMessage.score)
        .join(ConversationSession, ConversationSession.id == ConversationMessage.session_id)
        .where(
            ConversationSession.user_id == user_id,
            ConversationMessage.role == "user",
            ConversationMessage.score.is_not(None),
        )
        .order_by(ConversationMessage.created_at.asc())
    )
    return [
        (created_at, int(score))
        for created_at, score in result.all()
        if score is not None
    ]


async def _fetch_practice_sessions(
    session: AsyncSession,
    *,
    user_id: object,
) -> tuple[list[PracticeSession], list[ConversationSession]]:
    translation_result = await session.execute(
        select(PracticeSession)
        .where(PracticeSession.user_id == user_id)
        .order_by(PracticeSession.started_at.asc())
    )
    conversation_result = await session.execute(
        select(ConversationSession)
        .where(ConversationSession.user_id == user_id)
        .order_by(ConversationSession.started_at.asc())
    )
    return list(translation_result.scalars().all()), list(conversation_result.scalars().all())


async def _fetch_mistake_reviews(
    session: AsyncSession,
    *,
    user_id: object,
) -> list[MistakeReview]:
    result = await session.execute(
        select(MistakeReview)
        .where(MistakeReview.user_id == user_id)
        .order_by(MistakeReview.created_at.asc())
    )
    return list(result.scalars().all())


async def build_progress_response(
    session: AsyncSession,
    *,
    user: User,
) -> ProgressResponse:
    profile = await get_or_create_user_learning_profile(
        session,
        user_id=user.id,
        preferred_level=user.english_level,
    )
    translation_rows = await _fetch_translation_attempts(session, user_id=user.id)
    conversation_rows = await _fetch_conversation_scores(session, user_id=user.id)
    translation_sessions, conversation_sessions = await _fetch_practice_sessions(session, user_id=user.id)
    mistake_reviews = await _fetch_mistake_reviews(session, user_id=user.id)

    average_translation_score = _average(row.score for row in translation_rows)
    average_conversation_score = _average(score for _, score in conversation_rows)
    average_mistake_review_score = _average(review.score for review in mistake_reviews)

    overall_components = [
        score
        for score in [average_translation_score, average_conversation_score, average_mistake_review_score]
        if score > 0
    ]
    overall_score = _average(overall_components)

    weak_area_items = sorted(
        [
            (normalize_learning_area(area), int(count))
            for area, count in (profile.weak_areas_json or {}).items()
            if normalize_learning_area(area) and int(count) > 0
        ],
        key=lambda item: (-item[1], learning_area_label(item[0])),
    )
    top_weak_areas = [
        LearningProfileAreaResponse(
            type=area or "grammar",
            count=count,
            label=learning_area_label(area),
        )
        for area, count in weak_area_items[:3]
    ]

    activity_dates = {
        _start_of_day(row.created_at)
        for row in translation_rows
    }
    activity_dates.update(_start_of_day(created_at) for created_at, _score in conversation_rows)
    activity_dates.update(_start_of_day(review.created_at) for review in mistake_reviews)

    total_questions_answered = len(translation_rows) + len(conversation_rows) + len(mistake_reviews)
    total_practice_sessions = len(translation_sessions) + len(conversation_sessions)
    total_conversations = len(conversation_sessions)

    if total_practice_sessions == 0 and total_questions_answered == 0 and total_conversations == 0:
        return ProgressResponse(
            overall_score=0,
            average_translation_score=0,
            average_conversation_score=0,
            total_practice_sessions=0,
            total_questions_answered=0,
            total_conversations=0,
            streak_days=0,
            top_weak_areas=[],
            recent_improvements=[],
            recommended_next_practice=ProgressRecommendedPracticeResponse(
                type="translation_practice",
                title="Start your first translation practice",
            ),
        )

    recent_improvements = _recent_improvements(
        translation_rows=translation_rows,
        conversation_rows=conversation_rows,
        mistake_reviews=mistake_reviews,
    )

    return ProgressResponse(
        overall_score=overall_score or int(round(profile.average_score or 0)),
        average_translation_score=average_translation_score,
        average_conversation_score=average_conversation_score,
        total_practice_sessions=total_practice_sessions,
        total_questions_answered=total_questions_answered,
        total_conversations=total_conversations,
        streak_days=_current_streak(activity_dates),
        top_weak_areas=top_weak_areas,
        recent_improvements=recent_improvements,
        recommended_next_practice=_recommended_next_practice(
            recommended_focus_area=profile.recommended_focus_area,
            repeated_mistakes_count=len(
                [
                    item
                    for item in list(profile.repeated_mistakes_json or [])
                    if str(item.get("status", "needs_practice")) != "resolved"
                ]
            ),
            average_translation_score=average_translation_score,
            average_conversation_score=average_conversation_score,
            practice_preference=user.practice_preference,
        ),
    )
