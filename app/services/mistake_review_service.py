from __future__ import annotations

import hashlib
from dataclasses import dataclass
from difflib import SequenceMatcher
import re
import uuid
from typing import Any

from fastapi import HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.mistake_review import MistakeReview
from app.models.user import User
from app.prompts.mistake_review_prompt import build_mistake_retry_evaluation_prompt
from app.schemas.ai_chat import VoiceTranscriptionMetadata
from app.schemas.mistake_review import (
    MistakeReviewItemResponse,
    MistakeReviewListResponse,
    MistakeRetryRequest,
    MistakeRetryResponse,
    MistakeRetryVoiceResponse,
)
from app.services.ai_provider import (
    AIConversationTurn,
    AIProviderConfigurationError,
    AIProviderParseError,
    AIProviderResponseError,
    generate_structured_json,
)
from app.services.stt_provider import (
    STTProviderConfigurationError,
    STTProviderResponseError,
    transcribe_audio,
)
from app.services.user_learning_profile_service import (
    apply_mistake_review_result,
    get_or_create_user_learning_profile,
    learning_area_label,
    normalize_learning_area,
)
from app.services.voice_chat_service import ALLOWED_AUDIO_CONTENT_TYPES

_MAX_REVIEW_ITEMS = 5


@dataclass(slots=True)
class ReviewMistakeItem:
    id: str
    type: str
    wrong_sentence: str
    correct_sentence: str
    explanation: str
    retry_question: str
    focus_area: str
    seen_count: int
    status: str
    score: int | None
    priority: tuple[int, int, int, float]
    improvement_count: int
    raw_item: dict[str, Any]


def _stable_mistake_id(item: dict[str, Any]) -> str:
    payload = "|".join(
        [
            str(normalize_learning_area(str(item.get("type", "") or "")) or "grammar"),
            str(item.get("wrong", "") or "").strip().lower(),
            str(item.get("correct", "") or "").strip().lower(),
            str(item.get("retry_question", "") or "").strip().lower(),
        ]
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _normalize_status(item: dict[str, Any]) -> str:
    status_value = str(item.get("status", "") or "needs_practice").strip().lower()
    if status_value in {"needs_practice", "improved", "resolved"}:
        return status_value
    return "needs_practice"


def _fallback_retry_question(item: dict[str, Any]) -> str:
    retry_question = str(item.get("retry_question", "") or "").strip()
    if retry_question:
        return retry_question

    source_sentence = str(item.get("source_sentence", "") or "").strip()
    if source_sentence:
        return f"Translate: {source_sentence}"

    return "Rewrite this idea in correct natural English."


def _normalized_review_item(item: dict[str, Any]) -> dict[str, Any]:
    area = normalize_learning_area(str(item.get("type", "") or "")) or "grammar"
    normalized = dict(item)
    normalized["type"] = area
    normalized["focus_area"] = normalize_learning_area(
        str(item.get("focus_area", "") or area)
    ) or area
    normalized["wrong"] = str(item.get("wrong", "") or "").strip()
    normalized["correct"] = str(item.get("correct", "") or "").strip()
    normalized["explanation"] = str(item.get("explanation", "") or "Review the verb tense and sentence form.").strip()
    normalized["retry_question"] = _fallback_retry_question(item)
    normalized["count"] = max(int(item.get("count", 1) or 1), 1)
    normalized["score"] = int(item.get("score", 0) or 0) if item.get("score") is not None else None
    normalized["status"] = _normalize_status(item)
    normalized["improvement_count"] = max(int(item.get("improvement_count", 0) or 0), 0)
    normalized["id"] = _stable_mistake_id(normalized)
    return normalized


def _review_priority(
    *,
    item: dict[str, Any],
    recommended_focus_area: str | None,
    source_kind: str,
) -> tuple[int, int, int, float]:
    focus_bonus = 0
    if recommended_focus_area and item["focus_area"] == recommended_focus_area:
        focus_bonus = 1

    repeated_bonus = 1 if source_kind == "repeated" or item["count"] >= 2 else 0
    low_score_rank = 100 - int(item["score"] or 0)
    seen_rank = item["count"]
    return (focus_bonus, repeated_bonus, seen_rank, float(low_score_rank))


def _build_review_item(
    *,
    item: dict[str, Any],
    recommended_focus_area: str | None,
    source_kind: str,
) -> ReviewMistakeItem | None:
    normalized = _normalized_review_item(item)
    if not normalized["wrong"] or not normalized["correct"]:
        return None
    if normalized["status"] == "resolved" or normalized["improvement_count"] >= 2:
        return None

    return ReviewMistakeItem(
        id=normalized["id"],
        type=normalized["type"],
        wrong_sentence=normalized["wrong"],
        correct_sentence=normalized["correct"],
        explanation=normalized["explanation"],
        retry_question=normalized["retry_question"],
        focus_area=normalized["focus_area"],
        seen_count=normalized["count"],
        status=normalized["status"],
        score=normalized["score"],
        priority=_review_priority(
            item=normalized,
            recommended_focus_area=recommended_focus_area,
            source_kind=source_kind,
        ),
        improvement_count=normalized["improvement_count"],
        raw_item=normalized,
    )


async def list_review_mistakes(
    session: AsyncSession,
    *,
    user: User,
) -> list[ReviewMistakeItem]:
    profile = await get_or_create_user_learning_profile(
        session,
        user_id=user.id,
        preferred_level=user.english_level,
    )
    recommended_focus_area = normalize_learning_area(profile.recommended_focus_area)

    candidates: dict[str, ReviewMistakeItem] = {}

    for source_kind, items in (
        ("repeated", list(profile.repeated_mistakes_json or [])),
        ("recent", list(profile.recent_mistakes_json or [])),
    ):
        for item in items:
            review_item = _build_review_item(
                item=item,
                recommended_focus_area=recommended_focus_area,
                source_kind=source_kind,
            )
            if review_item is None:
                continue

            existing = candidates.get(review_item.id)
            if existing is None or review_item.priority > existing.priority:
                candidates[review_item.id] = review_item

    sorted_items = sorted(
        candidates.values(),
        key=lambda item: (
            item.priority[0],
            item.priority[1],
            item.priority[2],
            item.priority[3],
        ),
        reverse=True,
    )
    return sorted_items[:_MAX_REVIEW_ITEMS]


async def get_mistake_review_payload(
    session: AsyncSession,
    *,
    user: User,
) -> MistakeReviewListResponse:
    mistakes = await list_review_mistakes(session, user=user)
    return MistakeReviewListResponse(
        mistakes=[
            MistakeReviewItemResponse(
                id=item.id,
                type=item.type,  # type: ignore[arg-type]
                wrong_sentence=item.wrong_sentence,
                correct_sentence=item.correct_sentence,
                explanation=item.explanation,
                retry_question=item.retry_question,
                focus_area=item.focus_area,  # type: ignore[arg-type]
                seen_count=item.seen_count,
                status=item.status,  # type: ignore[arg-type]
            )
            for item in mistakes
        ]
    )


def _normalize_for_comparison(value: str) -> str:
    lowered = value.lower()
    lowered = re.sub(r"[^a-z0-9\\s]", " ", lowered)
    lowered = re.sub(r"\b(a|an|the)\b", " ", lowered)
    return " ".join(lowered.split()).strip()


def _text_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def _fallback_retry_result(item: ReviewMistakeItem, retry_answer: str) -> MistakeRetryResponse:
    normalized_answer = _normalize_for_comparison(retry_answer)
    normalized_correct = _normalize_for_comparison(item.correct_sentence)
    similarity = _text_similarity(normalized_answer, normalized_correct)

    if similarity >= 0.84 or normalized_answer == normalized_correct:
        return MistakeRetryResponse(
            is_improved=True,
            score=92,
            correct_answer=item.correct_sentence,
            natural_answer=item.correct_sentence,
            feedback="Much better. Your retry is clear and natural enough.",
            remaining_issue=None,
            status="improved",
        )

    return MistakeRetryResponse(
        is_improved=False,
        score=58,
        correct_answer=item.correct_sentence,
        natural_answer=item.correct_sentence,
        feedback="Good effort. The main grammar or meaning issue is still there.",
        remaining_issue=f"Focus on {learning_area_label(item.focus_area).lower()} in this sentence.",
        status="needs_more_practice",
    )


async def _evaluate_retry_with_llm(
    *,
    item: ReviewMistakeItem,
    retry_answer: str,
) -> MistakeRetryResponse:
    provider_result = await generate_structured_json(
        system_prompt=build_mistake_retry_evaluation_prompt(
            focus_area=learning_area_label(item.focus_area),
            wrong_sentence=item.wrong_sentence,
            correct_sentence=item.correct_sentence,
            explanation=item.explanation,
            retry_question=item.retry_question,
        ),
        conversation=[
            AIConversationTurn(role="user", content=f"Learner retry answer: {retry_answer}")
        ],
        schema_name="mistake_review_retry",
        json_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "is_improved": {"type": "boolean"},
                "score": {"type": "integer", "minimum": 0, "maximum": 100},
                "correct_answer": {"type": "string"},
                "natural_answer": {"type": "string"},
                "feedback": {"type": "string"},
                "remaining_issue": {"type": ["string", "null"]},
                "status": {
                    "type": "string",
                    "enum": ["improved", "needs_more_practice"],
                },
            },
            "required": [
                "is_improved",
                "score",
                "correct_answer",
                "natural_answer",
                "feedback",
                "remaining_issue",
                "status",
            ],
        },
    )
    result = MistakeRetryResponse.model_validate(provider_result.data)
    return result


async def _find_review_mistake_by_id(
    session: AsyncSession,
    *,
    user: User,
    mistake_id: str,
) -> ReviewMistakeItem:
    profile = await get_or_create_user_learning_profile(
        session,
        user_id=user.id,
        preferred_level=user.english_level,
    )
    all_items = [
        *list(profile.repeated_mistakes_json or []),
        *list(profile.recent_mistakes_json or []),
    ]
    for item in all_items:
        review_item = _build_review_item(
            item=item,
            recommended_focus_area=normalize_learning_area(profile.recommended_focus_area),
            source_kind="repeated" if int(item.get("count", 1) or 1) >= 2 else "recent",
        )
        if review_item and review_item.id == mistake_id:
            return review_item

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mistake review item not found")


async def submit_mistake_retry(
    session: AsyncSession,
    *,
    user: User,
    payload: MistakeRetryRequest,
) -> MistakeRetryResponse:
    review_item = await _find_review_mistake_by_id(
        session,
        user=user,
        mistake_id=payload.mistake_id,
    )

    try:
        result = await _evaluate_retry_with_llm(
            item=review_item,
            retry_answer=payload.retry_answer,
        )
    except (
        AIProviderConfigurationError,
        AIProviderParseError,
        AIProviderResponseError,
        ValidationError,
    ):
        result = _fallback_retry_result(review_item, payload.retry_answer)

    review = MistakeReview(
        user_id=user.id,
        mistake_id=payload.mistake_id,
        retry_answer=payload.retry_answer,
        score=result.score,
        is_improved=result.is_improved,
        feedback_json={
            "correct_answer": result.correct_answer,
            "natural_answer": result.natural_answer,
            "feedback": result.feedback,
            "remaining_issue": result.remaining_issue,
            "status": result.status,
            "input_mode": payload.input_mode,
        },
    )
    session.add(review)
    await session.commit()

    await apply_mistake_review_result(
        session,
        user=user,
        review_item=review_item.raw_item,
        result=result,
    )
    return result


async def submit_voice_mistake_retry(
    session: AsyncSession,
    *,
    user: User,
    mistake_id: str,
    audio_file: UploadFile,
    duration_ms: int | None = None,
    source: str | None = None,
) -> MistakeRetryVoiceResponse:
    if not audio_file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio file is required")

    content_type = audio_file.content_type
    if content_type and content_type not in ALLOWED_AUDIO_CONTENT_TYPES and not content_type.startswith("audio/"):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported audio format")

    file_bytes = await audio_file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio file is empty")
    if len(file_bytes) > get_settings().voice_max_upload_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Audio file is too large")

    try:
        transcription = await transcribe_audio(
            file_bytes=file_bytes,
            file_name=audio_file.filename,
            mime_type=content_type,
            duration_ms=duration_ms,
            source=source,
            use_default_language_hint=True,
        )
    except STTProviderConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except STTProviderResponseError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    result = await submit_mistake_retry(
        session,
        user=user,
        payload=MistakeRetryRequest(
            mistake_id=mistake_id,
            retry_answer=transcription.text,
            input_mode="speech",
        ),
    )
    return MistakeRetryVoiceResponse(
        transcript=transcription.text,
        result=result,
        transcription=VoiceTranscriptionMetadata(
            provider=transcription.provider,
            model=transcription.model,
            mime_type=transcription.mime_type,
            duration_ms=transcription.duration_ms,
            source=transcription.source,
            language=transcription.language,
            file_name=transcription.file_name,
        ),
    )
