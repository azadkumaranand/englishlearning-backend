from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation_session import ConversationSession
from app.models.message_correction import MessageCorrection
from app.models.practice_session import PracticeSession
from app.models.practice_translation_item import PracticeTranslationItem
from app.models.user import User
from app.models.user_learning_profile import UserLearningProfile
from app.schemas.learning_profile import (
    LearningProfileAreaResponse,
    LearningProfileMistakeResponse,
    LearningProfileResponse,
)
from app.schemas.mistake_review import MistakeRetryResponse

_DIFFICULTY_ORDER = ("beginner", "intermediate", "advanced")
_AREA_LABELS: dict[str, str] = {
    "tense": "Tense usage",
    "grammar": "Grammar",
    "vocabulary": "Vocabulary",
    "sentence_structure": "Sentence structure",
    "word_order": "Word order",
    "meaning": "Meaning",
    "word_by_word_translation": "Word-by-word translation",
    "spelling": "Spelling",
    "general_fluency": "General fluency",
}
_TAG_TO_AREA: dict[str, str] = {
    "past_tense": "tense",
    "present_tense": "tense",
    "future_tense": "tense",
    "tense": "tense",
    "articles": "grammar",
    "prepositions": "grammar",
    "grammar": "grammar",
    "sentence_structure": "sentence_structure",
    "word_order": "word_order",
    "meaning": "meaning",
    "word_by_word_translation": "word_by_word_translation",
    "short_answers": "sentence_structure",
    "vocabulary": "vocabulary",
    "spelling": "spelling",
}


def _normalize_difficulty(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized == "not_sure":
        return "beginner"
    if normalized in _DIFFICULTY_ORDER:
        return normalized
    return "beginner"


def normalize_learning_area(tag: str | None) -> str | None:
    if not tag:
        return None
    normalized = tag.strip().lower()
    if not normalized:
        return None
    return _TAG_TO_AREA.get(normalized, normalized)


def learning_area_label(area: str | None) -> str:
    normalized = normalize_learning_area(area)
    if normalized is None:
        return "General fluency"
    return _AREA_LABELS.get(normalized, normalized.replace("_", " ").title())


def _sorted_area_counts(area_counts: dict[str, int] | None) -> list[tuple[str, int]]:
    items = [
        (normalize_learning_area(area), int(count))
        for area, count in (area_counts or {}).items()
        if normalize_learning_area(area) and int(count) > 0
    ]
    return sorted(
        [(area, count) for area, count in items if area is not None],
        key=lambda item: (-item[1], learning_area_label(item[0])),
    )


def ordered_learning_areas(area_counts: dict[str, int] | None) -> list[str]:
    return [area for area, _count in _sorted_area_counts(area_counts)]


def _area_responses(area_counts: dict[str, int] | None) -> list[LearningProfileAreaResponse]:
    return [
        LearningProfileAreaResponse(
            type=area,
            count=count,
            label=learning_area_label(area),
        )
        for area, count in _sorted_area_counts(area_counts)
    ]


def _parse_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _mistake_response(item: dict) -> LearningProfileMistakeResponse:
    area = normalize_learning_area(str(item.get("type", "") or "")) or "grammar"
    return LearningProfileMistakeResponse(
        type=area,
        label=learning_area_label(area),
        wrong=str(item.get("wrong", "") or ""),
        correct=str(item.get("correct", "") or ""),
        count=max(int(item.get("count", 1) or 1), 1),
        last_seen_at=_parse_datetime(item.get("last_seen_at")),
    )


def compute_translation_attempt_score(*, correction: MessageCorrection, is_correct: bool) -> int:
    if is_correct or correction.severity == "none":
        return 96

    base = {
        "low": 78,
        "medium": 62,
        "high": 45,
        "none": 85,
    }.get(correction.severity, 60)
    penalty = max(len(correction.tags or []) - 1, 0) * 4
    return max(20, min(99, base - penalty))


def _next_difficulty(current: str, direction: int) -> str:
    index = _DIFFICULTY_ORDER.index(current)
    bounded = min(max(index + direction, 0), len(_DIFFICULTY_ORDER) - 1)
    return _DIFFICULTY_ORDER[bounded]


def _adjust_current_difficulty(
    *,
    current_difficulty: str | None,
    preferred_level: str | None,
    average_score: float,
    total_attempts: int,
) -> str:
    current = _normalize_difficulty(current_difficulty or preferred_level)
    if total_attempts >= 5 and total_attempts % 5 == 0 and average_score >= 85:
        return _next_difficulty(current, 1)
    if total_attempts >= 3 and total_attempts % 3 == 0 and average_score < 60:
        return _next_difficulty(current, -1)
    return current


def _primary_focus_area(weak_areas: dict[str, int] | None) -> str | None:
    sorted_areas = _sorted_area_counts(weak_areas)
    if not sorted_areas:
        return None
    return sorted_areas[0][0]


def _same_mistake_identity(left: dict, right: dict) -> bool:
    return (
        normalize_learning_area(str(left.get("type", "") or ""))
        == normalize_learning_area(str(right.get("type", "") or ""))
        and str(left.get("wrong", "") or "").strip().lower()
        == str(right.get("wrong", "") or "").strip().lower()
        and str(left.get("correct", "") or "").strip().lower()
        == str(right.get("correct", "") or "").strip().lower()
        and str(left.get("retry_question", "") or "").strip().lower()
        == str(right.get("retry_question", "") or "").strip().lower()
    )


def _build_translation_mistake_item(
    *,
    area: str,
    correction: MessageCorrection,
    translation_item: PracticeTranslationItem,
    score: int,
    now: datetime,
) -> dict:
    retry_question = (
        f"Translate: {translation_item.source_sentence}"
        if translation_item.source_sentence.strip()
        else "Rewrite this idea in correct natural English."
    )
    return {
        "type": area,
        "focus_area": area,
        "wrong": correction.original_text,
        "correct": correction.corrected_text,
        "explanation": correction.explanation,
        "retry_question": retry_question,
        "source_sentence": translation_item.source_sentence,
        "count": 1,
        "score": score,
        "status": "needs_practice",
        "improvement_count": 0,
        "last_seen_at": now.isoformat(),
    }


def _merge_repeated_mistakes(
    existing_items: list[dict],
    *,
    new_items: list[dict],
) -> list[dict]:
    merged = [dict(item) for item in existing_items]
    for new_item in new_items:
        area = normalize_learning_area(str(new_item.get("type", "") or ""))
        wrong = str(new_item.get("wrong", "") or "").strip()
        correct = str(new_item.get("correct", "") or "").strip()
        if not area or not wrong or not correct:
            continue

        match = next(
            (item for item in merged if _same_mistake_identity(item, new_item)),
            None,
        )
        if match is None:
            merged.append(dict(new_item))
            continue

        match["count"] = max(int(match.get("count", 1) or 1), 1) + 1
        match["last_seen_at"] = new_item["last_seen_at"]
        match["score"] = new_item.get("score", match.get("score"))
        match["explanation"] = new_item.get("explanation", match.get("explanation"))
        match["retry_question"] = new_item.get("retry_question", match.get("retry_question"))
        match["focus_area"] = new_item.get("focus_area", match.get("focus_area"))
        match["source_sentence"] = new_item.get("source_sentence", match.get("source_sentence"))
        match["status"] = "needs_practice"

    merged.sort(
        key=lambda item: (
            max(int(item.get("count", 1) or 1), 1),
            _parse_datetime(item.get("last_seen_at")).timestamp(),
        ),
        reverse=True,
    )
    return merged[:10]


def _prepend_recent_mistakes(existing_items: list[dict], *, new_items: list[dict]) -> list[dict]:
    combined: list[dict] = []
    seen: list[dict] = []
    for item in [*new_items, *existing_items]:
        current = dict(item)
        if any(_same_mistake_identity(current, existing) for existing in seen):
            continue
        seen.append(current)
        combined.append(current)
    return combined[:10]


def _update_stored_mistake_items(
    items: list[dict],
    *,
    review_item: dict,
    result: MistakeRetryResponse,
    now: datetime,
) -> list[dict]:
    updated_items: list[dict] = []
    found = False
    for item in items:
        current = dict(item)
        if not _same_mistake_identity(current, review_item):
            updated_items.append(current)
            continue

        found = True
        improvement_count = max(int(current.get("improvement_count", 0) or 0), 0)
        if result.is_improved:
            improvement_count += 1
        current["improvement_count"] = improvement_count
        current["status"] = "resolved" if improvement_count >= 2 else ("improved" if result.is_improved else "needs_practice")
        current["score"] = result.score
        current["last_seen_at"] = now.isoformat()
        current["feedback"] = result.feedback
        current["remaining_issue"] = result.remaining_issue
        current["correct"] = result.correct_answer
        current["natural_answer"] = result.natural_answer
        updated_items.append(current)

    if not found:
        fallback = dict(review_item)
        fallback["improvement_count"] = 1 if result.is_improved else 0
        fallback["status"] = "improved" if result.is_improved else "needs_practice"
        fallback["score"] = result.score
        fallback["last_seen_at"] = now.isoformat()
        fallback["feedback"] = result.feedback
        fallback["remaining_issue"] = result.remaining_issue
        fallback["correct"] = result.correct_answer
        fallback["natural_answer"] = result.natural_answer
        updated_items.insert(0, fallback)

    return updated_items[:10]


def _build_summary_response(profile: UserLearningProfileResponseLike) -> str:
    if profile.average_score >= 85:
        intro = "You are improving well."
    elif profile.average_score >= 60:
        intro = "You are making steady progress."
    else:
        intro = "Keep practicing short, clear English sentences."

    weak_labels = [area.label.lower() for area in profile.weak_areas[:2]]
    if weak_labels:
        if len(weak_labels) == 1:
            focus = f" Focus more on {weak_labels[0]}."
        else:
            focus = f" Focus more on {weak_labels[0]} and {weak_labels[1]}."
    else:
        focus = " Keep practicing daily to build your first learning pattern."

    if profile.recommended_focus_area:
        today = f" Today we'll focus on {learning_area_label(profile.recommended_focus_area).lower()}."
    else:
        today = ""
    return f"{intro}{focus}{today}"


class UserLearningProfileResponseLike:
    average_score: int
    weak_areas: list[LearningProfileAreaResponse]
    recommended_focus_area: str | None


async def get_user_learning_profile_record(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> UserLearningProfile | None:
    result = await session.execute(
        select(UserLearningProfile).where(UserLearningProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_or_create_user_learning_profile(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    preferred_level: str | None,
) -> UserLearningProfile:
    profile = await get_user_learning_profile_record(session, user_id=user_id)
    if profile is not None:
        return profile

    profile = UserLearningProfile(
        user_id=user_id,
        average_score=0.0,
        total_practice_sessions=0,
        total_attempts=0,
        total_correct_attempts=0,
        weak_areas_json={},
        strong_areas_json={},
        repeated_mistakes_json=[],
        recent_mistakes_json=[],
        recommended_focus_area=None,
        current_difficulty=_normalize_difficulty(preferred_level),
    )
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return profile


async def _count_translation_practice_sessions(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> int:
    result = await session.execute(
        select(func.count(PracticeSession.id)).where(
            PracticeSession.user_id == user_id,
            PracticeSession.mode == "translation_practice",
        )
    )
    return int(result.scalar_one() or 0)


async def _count_all_practice_sessions(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> int:
    translation_result = await session.execute(
        select(func.count(PracticeSession.id)).where(PracticeSession.user_id == user_id)
    )
    conversation_result = await session.execute(
        select(func.count(ConversationSession.id)).where(ConversationSession.user_id == user_id)
    )
    return int(translation_result.scalar_one() or 0) + int(conversation_result.scalar_one() or 0)


async def build_learning_profile_response(
    session: AsyncSession,
    *,
    user: User,
) -> LearningProfileResponse:
    profile = await get_or_create_user_learning_profile(
        session,
        user_id=user.id,
        preferred_level=user.english_level,
    )
    weak_areas = _area_responses(profile.weak_areas_json)
    strong_areas = _area_responses(profile.strong_areas_json)
    repeated_mistakes = [
        _mistake_response(item)
        for item in list(profile.repeated_mistakes_json or [])
        if max(int(item.get("count", 1) or 1), 1) >= 2
    ]
    recent_mistakes = [
        _mistake_response(item)
        for item in list(profile.recent_mistakes_json or [])
    ]
    response = LearningProfileResponse(
        average_score=int(round(profile.average_score or 0)),
        average_conversation_score=int(round(profile.average_conversation_score or 0)),
        speaking_confidence_score=int(round(profile.speaking_confidence_score or 0)),
        total_conversation_turns=profile.total_conversation_turns or 0,
        total_practice_sessions=profile.total_practice_sessions or 0,
        total_attempts=profile.total_attempts or 0,
        total_correct_attempts=profile.total_correct_attempts or 0,
        weak_areas=weak_areas,
        strong_areas=strong_areas,
        repeated_mistakes=repeated_mistakes,
        recent_mistakes=recent_mistakes,
        recommended_focus_area=normalize_learning_area(profile.recommended_focus_area),
        current_difficulty=_normalize_difficulty(profile.current_difficulty or user.english_level),
        summary="",
    )
    response.summary = _build_summary_response(response)
    return response


async def update_user_learning_profile_after_translation_attempt(
    session: AsyncSession,
    *,
    user: User,
    practice_session: PracticeSession,
    translation_item: PracticeTranslationItem,
    correction: MessageCorrection,
    is_correct: bool,
) -> UserLearningProfile:
    profile = await get_or_create_user_learning_profile(
        session,
        user_id=user.id,
        preferred_level=user.english_level,
    )
    now = datetime.now(timezone.utc)
    score = compute_translation_attempt_score(correction=correction, is_correct=is_correct)
    next_total_attempts = (profile.total_attempts or 0) + 1
    next_total_correct = (profile.total_correct_attempts or 0) + (1 if score >= 85 else 0)

    previous_average = float(profile.average_score or 0.0)
    profile.average_score = round(
        ((previous_average * (next_total_attempts - 1)) + score) / next_total_attempts,
        2,
    )
    profile.total_attempts = next_total_attempts
    profile.total_correct_attempts = next_total_correct
    profile.total_practice_sessions = await _count_translation_practice_sessions(
        session,
        user_id=user.id,
    )
    profile.last_practiced_at = now

    weak_areas = dict(profile.weak_areas_json or {})
    strong_areas = dict(profile.strong_areas_json or {})
    repeated_mistakes = list(profile.repeated_mistakes_json or [])
    recent_mistakes = list(profile.recent_mistakes_json or [])

    normalized_tags = [
        area
        for area in {
            normalize_learning_area(tag)
            for tag in (correction.tags or [])
        }
        if area
    ]

    mistake_items: list[dict] = []
    if score < 85:
        for area in normalized_tags or ["sentence_structure"]:
            weak_areas[area] = int(weak_areas.get(area, 0) or 0) + 1
            mistake_items.append(
                _build_translation_mistake_item(
                    area=area,
                    correction=correction,
                    translation_item=translation_item,
                    score=score,
                    now=now,
                )
            )
    else:
        strong_area = normalize_learning_area(translation_item.focus_tag) or "general_fluency"
        strong_areas[strong_area] = int(strong_areas.get(strong_area, 0) or 0) + 1

    profile.weak_areas_json = weak_areas
    profile.strong_areas_json = strong_areas
    profile.repeated_mistakes_json = _merge_repeated_mistakes(
        repeated_mistakes,
        new_items=mistake_items,
    )
    profile.recent_mistakes_json = _prepend_recent_mistakes(
        recent_mistakes,
        new_items=mistake_items,
    )
    profile.recommended_focus_area = _primary_focus_area(weak_areas)
    profile.current_difficulty = _adjust_current_difficulty(
        current_difficulty=profile.current_difficulty,
        preferred_level=user.english_level,
        average_score=float(profile.average_score or 0.0),
        total_attempts=profile.total_attempts,
    )

    await session.commit()
    await session.refresh(profile)
    return profile


async def try_update_user_learning_profile_after_translation_attempt(
    session: AsyncSession,
    *,
    user: User,
    practice_session: PracticeSession,
    translation_item: PracticeTranslationItem,
    correction: MessageCorrection,
    is_correct: bool,
) -> None:
    try:
        await update_user_learning_profile_after_translation_attempt(
            session=session,
            user=user,
            practice_session=practice_session,
            translation_item=translation_item,
            correction=correction,
            is_correct=is_correct,
        )
    except Exception:
        await session.rollback()


async def update_user_learning_profile_after_conversation_turn(
    session: AsyncSession,
    *,
    user: User,
    conversation_session: ConversationSession,
    score: int,
    confidence_score: int,
    mistakes: list[dict],
    corrected_sentence: str,
    natural_sentence: str,
    learner_message: str,
    ai_prompt: str,
    encouragement: str,
    tip: str,
) -> UserLearningProfile:
    profile = await get_or_create_user_learning_profile(
        session,
        user_id=user.id,
        preferred_level=user.english_level,
    )
    now = datetime.now(timezone.utc)
    next_total_attempts = (profile.total_attempts or 0) + 1
    next_total_correct = (profile.total_correct_attempts or 0) + (1 if score >= 85 else 0)
    previous_average = float(profile.average_score or 0.0)
    previous_conversation_average = float(profile.average_conversation_score or 0.0)
    previous_confidence_average = float(profile.speaking_confidence_score or 0.0)
    previous_conversation_turns = int(profile.total_conversation_turns or 0)
    next_conversation_turns = previous_conversation_turns + 1

    profile.total_attempts = next_total_attempts
    profile.total_correct_attempts = next_total_correct
    profile.total_conversation_turns = next_conversation_turns
    profile.average_score = round(
        ((previous_average * (next_total_attempts - 1)) + score) / next_total_attempts,
        2,
    )
    profile.average_conversation_score = round(
        ((previous_conversation_average * previous_conversation_turns) + score)
        / next_conversation_turns,
        2,
    )
    profile.speaking_confidence_score = round(
        ((previous_confidence_average * previous_conversation_turns) + confidence_score)
        / next_conversation_turns,
        2,
    )
    profile.total_practice_sessions = await _count_all_practice_sessions(session, user_id=user.id)
    profile.last_practiced_at = now

    weak_areas = dict(profile.weak_areas_json or {})
    strong_areas = dict(profile.strong_areas_json or {})
    repeated_mistakes = list(profile.repeated_mistakes_json or [])
    recent_mistakes = list(profile.recent_mistakes_json or [])

    mistake_items: list[dict] = []
    normalized_mistakes = [
        {
            "type": normalize_learning_area(str(item.get("type", "") or "")) or "grammar",
            "issue": str(item.get("issue", "") or "").strip(),
            "fix": str(item.get("fix", "") or "").strip(),
            "reason": str(item.get("reason", "") or "").strip(),
        }
        for item in mistakes
    ]

    if normalized_mistakes:
        for mistake in normalized_mistakes:
            area = mistake["type"]
            weak_areas[area] = int(weak_areas.get(area, 0) or 0) + 1
            mistake_items.append(
                {
                    "type": area,
                    "focus_area": area,
                    "wrong": learner_message,
                    "correct": corrected_sentence,
                    "natural_answer": natural_sentence,
                    "explanation": mistake["reason"] or encouragement,
                    "retry_question": f"Scenario retry: {ai_prompt}",
                    "count": 1,
                    "score": score,
                    "status": "needs_practice",
                    "improvement_count": 0,
                    "last_seen_at": now.isoformat(),
                }
            )
    elif score >= 85:
        strong_areas["confidence"] = int(strong_areas.get("confidence", 0) or 0) + 1

    if confidence_score >= 85:
        strong_areas["confidence"] = int(strong_areas.get("confidence", 0) or 0) + 1

    profile.weak_areas_json = {key: value for key, value in weak_areas.items() if value > 0}
    profile.strong_areas_json = {key: value for key, value in strong_areas.items() if value > 0}
    profile.repeated_mistakes_json = _merge_repeated_mistakes(
        repeated_mistakes,
        new_items=mistake_items,
    )
    profile.recent_mistakes_json = _prepend_recent_mistakes(
        recent_mistakes,
        new_items=mistake_items,
    )
    profile.recommended_focus_area = _primary_focus_area(profile.weak_areas_json)
    if score >= 88 and profile.average_conversation_score >= 85:
        profile.current_difficulty = _adjust_current_difficulty(
            current_difficulty=profile.current_difficulty,
            preferred_level=user.english_level,
            average_score=float(profile.average_conversation_score or 0.0),
            total_attempts=profile.total_conversation_turns,
        )

    await session.commit()
    await session.refresh(profile)
    return profile


async def apply_mistake_review_result(
    session: AsyncSession,
    *,
    user: User,
    review_item: dict,
    result: MistakeRetryResponse,
) -> UserLearningProfile:
    profile = await get_or_create_user_learning_profile(
        session,
        user_id=user.id,
        preferred_level=user.english_level,
    )
    now = datetime.now(timezone.utc)
    area = normalize_learning_area(str(review_item.get("focus_area", "") or review_item.get("type", "") or ""))
    weak_areas = dict(profile.weak_areas_json or {})
    strong_areas = dict(profile.strong_areas_json or {})

    if area:
        current_count = int(weak_areas.get(area, 0) or 0)
        if result.is_improved:
            weak_areas[area] = max(current_count - 1, 0)
            strong_areas[area] = int(strong_areas.get(area, 0) or 0) + 1
        else:
            weak_areas[area] = current_count + 1

    profile.weak_areas_json = {key: value for key, value in weak_areas.items() if value > 0}
    profile.strong_areas_json = {key: value for key, value in strong_areas.items() if value > 0}
    profile.repeated_mistakes_json = _update_stored_mistake_items(
        list(profile.repeated_mistakes_json or []),
        review_item=review_item,
        result=result,
        now=now,
    )
    profile.recent_mistakes_json = _update_stored_mistake_items(
        list(profile.recent_mistakes_json or []),
        review_item=review_item,
        result=result,
        now=now,
    )
    profile.recommended_focus_area = _primary_focus_area(profile.weak_areas_json)
    profile.last_practiced_at = now

    await session.commit()
    await session.refresh(profile)
    return profile
