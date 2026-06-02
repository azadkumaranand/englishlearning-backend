from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import logging
import re
from types import SimpleNamespace
from typing import Any
import uuid

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message_correction import MessageCorrection
from app.models.practice_message import PracticeMessage
from app.models.practice_session import PracticeSession
from app.models.practice_translation_item import PracticeTranslationItem
from app.models.user_learning_profile import UserLearningProfile
from app.schemas.correction import (
    TranslationEvaluationAnalysis,
    TranslationTutorEvaluationPayload,
    get_translation_evaluation_json_schema,
)
from app.services.ai_provider import (
    AIConversationTurn,
    AIProviderConfigurationError,
    AIProviderParseError,
    AIProviderResponseError,
    generate_ai_reply,
    generate_structured_json,
)
from app.services.personalization_service import (
    get_effective_translation_level,
    get_personalization_summary,
    record_completed_translation_item,
    try_update_personalization_after_correction,
)
from app.services.practice_session_service import (
    build_practice_session_completion_summary,
    complete_practice_session,
    create_practice_message,
    get_user_practice_session,
)
from app.services.recommendation_service import build_focus_recommendation
from app.services.user_learning_profile_service import (
    get_or_create_user_learning_profile,
    learning_area_label,
    ordered_learning_areas,
    try_update_user_learning_profile_after_translation_attempt,
)
from app.services.translation_item_service import (
    create_translation_item,
    get_active_translation_item,
    list_completed_translation_source_sentences,
    mark_translation_item_completed,
    record_translation_item_retry,
)
from app.prompts.translation_prompt import (
    build_translation_clarification_prompt,
    build_translation_evaluation_prompt,
    build_translation_starter_prompt,
)

logger = logging.getLogger(__name__)
_TRANSLATION_PROMPT_ATTEMPTS = 3
_AUTO_COMPLETE_TRANSLATION_ITEMS = 3


@dataclass(slots=True)
class TranslationPromptDraft:
    source_sentence: str
    reference_translation: str
    assistant_prompt: str
    source: str = "fallback"
    provider: str | None = None
    model: str | None = None
    response_id: str | None = None
    focus_tag: str | None = None


_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
_CLARIFICATION_PREFIX_RE = re.compile(
    r"^(why|how|what|when|where|who|can|could|should|would|is|are|do|does|did|please explain|explain)\b",
    re.IGNORECASE,
)
_TUTOR_MISTAKE_TAGS = {
    "tense",
    "grammar",
    "vocabulary",
    "sentence_structure",
    "word_order",
    "meaning",
    "word_by_word_translation",
    "spelling",
}


def _normalize_text(value: str) -> str:
    return " ".join(value.split()).strip()


def _sentence_key(value: str) -> str:
    lowered = value.lower()
    lowered = re.sub(r"[^\w\s]", " ", lowered, flags=re.UNICODE)
    return " ".join(lowered.split()).strip()


def _contains_devanagari(value: str) -> bool:
    return bool(_DEVANAGARI_RE.search(value))


def _read_reply_context(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(metadata, dict):
        return None
    reply_context = metadata.get("reply_context")
    return reply_context if isinstance(reply_context, dict) else None


def _looks_like_clarification_question(
    *,
    content: str,
    user_message_metadata: dict[str, Any] | None,
) -> bool:
    reply_context = _read_reply_context(user_message_metadata)
    if reply_context is None:
        return False

    reply_kind = reply_context.get("kind")
    if reply_kind in {"message", "correction"}:
        return True

    normalized = _normalize_text(content).lower()
    if not normalized:
        return False
    if "?" in content:
        return True
    if _CLARIFICATION_PREFIX_RE.match(normalized):
        return True

    clarification_markers = (
        "subject",
        "verb",
        "tense",
        "grammar",
        "meaning",
        "mean",
        "word order",
        "why not",
        "why are you",
        "explain",
    )
    return any(marker in normalized for marker in clarification_markers)


def _ensure_sentence_punctuation(value: str) -> str:
    stripped = value.strip()
    if not stripped or stripped.endswith(("।", ".", "?", "!")):
        return stripped
    return f"{stripped}।" if _contains_devanagari(stripped) else f"{stripped}."


def _format_translation_prompt_message(
    *,
    source_sentence: str,
    intro: str,
) -> str:
    if not _ensure_sentence_punctuation(source_sentence):
        return intro.strip()
    return f"{intro.strip()}\n\nRead the Hindi sentence below and reply in English."


def _merge_completed_source_sentences(*sentence_groups: list[str]) -> list[str]:
    merged: list[str] = []
    seen_keys: set[str] = set()
    for group in sentence_groups:
        for sentence in group:
            normalized = _normalize_text(sentence)
            if not normalized:
                continue
            key = _sentence_key(normalized)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            merged.append(normalized)
    return merged


def _normalize_for_comparison(value: str) -> str:
    lowered = value.lower()
    lowered = re.sub(r"[^a-z0-9\\s]", " ", lowered)
    lowered = re.sub(r"\b(a|an|the)\b", " ", lowered)
    return " ".join(lowered.split()).strip()


def _text_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def _severity_from_score(score: int) -> str:
    if score >= 85:
        return "none"
    if score >= 70:
        return "low"
    if score >= 55:
        return "medium"
    return "high"


def _feedback_level_from_score(score: int) -> str:
    if score >= 85:
        return "excellent"
    if score >= 60:
        return "good"
    return "needs_practice"


def _status_from_score(score: int, *, is_correct: bool) -> str:
    if is_correct or score >= 85:
        return "correct"
    if score >= 60:
        return "almost"
    return "needs_practice"


def _normalize_tutor_mistakes(mistakes: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in mistakes:
        mistake_type = str(item.get("type", "") or "").strip().lower()
        if mistake_type not in _TUTOR_MISTAKE_TAGS:
            mistake_type = "sentence_structure"
        wrong = str(item.get("wrong", "") or "").strip() or "Part of your sentence"
        correct = str(item.get("correct", "") or "").strip() or "needs a better English pattern"
        explanation = str(item.get("explanation", "") or "").strip() or "Focus on the meaning first."
        normalized.append(
            {
                "type": mistake_type,
                "wrong": wrong,
                "correct": correct,
                "explanation": explanation,
            }
        )
    return normalized[:3]


def _legacy_explanation_from_sections(
    *,
    feedback_level: str,
    what_is_wrong: str,
    why_it_is_wrong: str,
    key_learning: str,
) -> str:
    if feedback_level == "excellent":
        return f"[Good]: {what_is_wrong}\n[Tip]: {key_learning}"
    return f"[Mistake]: {what_is_wrong}\n[Why]: {why_it_is_wrong}\n[Tip]: {key_learning}"


def _dump_model(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


def _fallback_practice_examples(pattern_name: str) -> list[dict[str, str]]:
    lowered = pattern_name.lower()
    if "present continuous" in lowered:
        return [
            {"native": "मैं अभी खाना खा रहा हूँ।", "english": "I am eating food right now."},
            {"native": "वे इस समय बस का इंतज़ार कर रहे हैं।", "english": "They are waiting for the bus right now."},
        ]
    if "present perfect" in lowered:
        return [
            {"native": "मैं अपना काम पूरा कर चुका हूँ।", "english": "I have finished my work."},
            {"native": "वह अभी घर पहुँची है।", "english": "She has just reached home."},
        ]
    if "future" in lowered or "going to" in lowered:
        return [
            {"native": "मैं कल अपने दोस्त से मिलूँगा।", "english": "I will meet my friend tomorrow."},
            {"native": "हम अगले हफ्ते दिल्ली जाने वाले हैं।", "english": "We are going to go to Delhi next week."},
        ]
    if "be" in lowered or "state" in lowered or "adjective" in lowered:
        return [
            {"native": "कल मैं स्कूल के लिए देर से पहुँचा।", "english": "Yesterday, I was late to school."},
            {"native": "आज वह मीटिंग के लिए तैयार है।", "english": "Today, she is ready for the meeting."},
        ]
    return [
        {"native": "मैं रोज़ सुबह जल्दी उठता हूँ।", "english": "I wake up early every morning."},
        {"native": "हम शाम को पार्क जाते हैं।", "english": "We go to the park in the evening."},
    ]


def _normalize_translation_analysis(
    *,
    learner_answer: str,
    source_sentence: str,
    reference_translation: str,
    payload: TranslationTutorEvaluationPayload,
) -> TranslationEvaluationAnalysis:
    score = max(0, min(payload.score, 100))
    best_answer = payload.best_answer.strip() or reference_translation
    normalized_variations = [item.strip() for item in payload.natural_variations if item.strip()]
    normalized_variations = [best_answer, *normalized_variations]
    deduped_variations: list[str] = []
    seen_variations: set[str] = set()
    for item in normalized_variations:
        key = item.lower()
        if key in seen_variations:
            continue
        seen_variations.add(key)
        deduped_variations.append(item)
    is_correct = payload.status == "correct"
    mistake = payload.mistake
    raw_mistakes = []
    detected_type = "meaning"
    pattern_name = payload.pattern.name.lower()
    mistake_text = f"{mistake.explanation} {payload.pattern.name}".lower()
    if "tense" in mistake_text or "past" in pattern_name or "present" in pattern_name or "future" in pattern_name:
        detected_type = "tense"
    elif "word order" in mistake_text:
        detected_type = "word_order"
    elif "word by word" in mistake_text:
        detected_type = "word_by_word_translation"
    elif "vocabulary" in mistake_text or "word choice" in mistake_text:
        detected_type = "vocabulary"
    elif "grammar" in mistake_text or "modal" in pattern_name or "be verb" in pattern_name:
        detected_type = "grammar"
    if mistake.has_error and mistake.correction.strip():
        raw_mistakes.append(
            {
                "type": detected_type,
                "wrong": mistake.wrong_part.strip() or learner_answer,
                "correct": mistake.correction.strip(),
                "explanation": mistake.explanation.strip() or payload.pattern.name,
            }
        )
    normalized_mistakes = _normalize_tutor_mistakes(raw_mistakes)
    normalized_tags = [
        item["type"]
        for item in normalized_mistakes
        if item["type"] in _TUTOR_MISTAKE_TAGS
    ]
    retry_needed = payload.status != "correct"
    retry_hint = (
        f"Use this structure: {payload.pattern.structure}"
        if retry_needed and score < 85
        else None
    )
    retry_prompt = (
        f"Translate again using this structure: {payload.pattern.structure}"
        if retry_needed
        else "You are ready for the next sentence."
    )
    feedback_level = _feedback_level_from_score(score)
    user_mistake = {
        "is_wrong": mistake.has_error,
        "wrong_part": mistake.wrong_part.strip(),
        "replace_with": mistake.correction.strip(),
        "reason": mistake.explanation.strip(),
    }
    mapped_breakdown = [
        {
            "native_part": item.native.strip(),
            "english_part": item.english.strip(),
            "role": (item.note or "").strip() or "Meaning",
        }
        for item in payload.meaning_mapping
        if item.native.strip() and item.english.strip()
    ]
    practice_examples: list[dict[str, str]] = []
    seen_examples: set[str] = set()
    for item in payload.pattern.examples:
        native = item.native.strip()
        english = item.english.strip()
        if not native or not english:
            continue
        if english.lower() == best_answer.lower():
            continue
        key = f"{native.lower()}::{english.lower()}"
        if key in seen_examples:
            continue
        seen_examples.add(key)
        practice_examples.append({"native": native, "english": english})
    for item in _fallback_practice_examples(payload.pattern.name):
        if len(practice_examples) >= 2:
            break
        key = f"{item['native'].lower()}::{item['english'].lower()}"
        if key in seen_examples or item["english"].lower() == best_answer.lower():
            continue
        seen_examples.add(key)
        practice_examples.append(item)
    practice_examples = practice_examples[:2]
    why_pattern = (
        payload.pattern.usage_note.strip()
        if payload.pattern.usage_note.strip()
        else (
            payload.meaning_mapping[0].note.strip()
            if payload.meaning_mapping and payload.meaning_mapping[0].note
            else f"This sentence uses the pattern '{payload.pattern.name}'."
        )
    )
    return TranslationEvaluationAnalysis(
        original=learner_answer,
        corrected=best_answer,
        explanation=_legacy_explanation_from_sections(
            feedback_level=feedback_level,
            what_is_wrong=user_mistake["reason"] if user_mistake["is_wrong"] and user_mistake["reason"] else payload.pattern.name,
            why_it_is_wrong=best_answer,
            key_learning=payload.pattern.translation_tip,
        ),
        natural_version=normalized_variations[0] if normalized_variations else best_answer,
        retry_prompt=retry_prompt,
        tags=normalized_tags,
        severity=_severity_from_score(score),  # type: ignore[arg-type]
        is_correct=is_correct,
        assistant_reply="Good job. You are ready for the next sentence." if is_correct else "Good try. Please try the same sentence again.",
        score=score,
        status=payload.status,
        native_sentence=source_sentence,
        best_answer=best_answer,
        feedback_level=feedback_level,
        correct_answer=best_answer,
        quick_feedback=(
            "Correct. This structure works well."
            if is_correct
            else (user_mistake["reason"] or why_pattern)
        ),
        tense_explanation={
            "tense_or_pattern": payload.pattern.name,
            "why_this_pattern": why_pattern,
            "structure": payload.pattern.structure,
            "native_to_english_mapping": mapped_breakdown,
            "correct_translation_using_structure": best_answer,
            "similar_example": {
                "native": practice_examples[0]["native"] if practice_examples else "",
                "english": practice_examples[0]["english"] if practice_examples else best_answer,
            },
        },
        user_mistake=user_mistake,
        retry={
            "needed": retry_needed,
            "prompt": retry_prompt,
            "hint": retry_hint,
        },
        what_is_wrong={
            "title": "What to fix",
            "explanation": (
                user_mistake["reason"]
                or f"Use this pattern: {payload.pattern.structure}"
            ),
        },
        why_it_is_wrong={
            "title": "Why",
            "explanation": (
                f"This sentence needs the pattern '{payload.pattern.name}'. "
                f"Best translation: {best_answer}"
            ),
        },
        think_like_this={
            "wrong_thinking": (
                "I translated the native sentence word by word."
                if user_mistake["is_wrong"]
                else "I followed the meaning correctly."
            ),
            "correct_thinking": "First choose the English pattern, then build the sentence with that structure.",
        },
        grammar_breakdown={
            "topic": payload.pattern.name,
            "user_sentence_analysis": (
                user_mistake["reason"]
                or "Your answer used a different English pattern than this sentence needs."
            ),
            "correct_sentence_analysis": (
                f"The corrected sentence follows this structure: {payload.pattern.structure}."
            ),
            "structure": payload.pattern.structure,
            "example_pattern": practice_examples[0]["english"] if practice_examples else best_answer,
            "tense_used": payload.pattern.name,
            "why_this_tense": why_pattern,
            "native_language_note": (
                " | ".join(item.note.strip() for item in payload.meaning_mapping if item.note and item.note.strip())
            ),
        },
        translation_tip=payload.pattern.translation_tip,
        practice_examples=practice_examples,
        key_learning=payload.pattern.translation_tip,
        natural_variations=deduped_variations[:3] or [best_answer],
        mistakes=normalized_mistakes,  # type: ignore[arg-type]
        retry_strategy={
            "should_retry": retry_needed,
            "retry_type": "next_question" if not retry_needed else ("hint" if retry_hint else "same_sentence"),
            "retry_prompt": retry_prompt,
            "hint": retry_hint,
        },
        encouragement="Good job. Go to the next sentence." if is_correct else "Good try. Use the structure and try again.",
        should_move_next=payload.status == "correct",
    )


def _should_accept_translation_answer(
    *,
    learner_answer: str,
    reference_translation: str,
    analysis: TranslationEvaluationAnalysis,
) -> bool:
    if analysis.is_correct:
        return True

    normalized_answer = _normalize_for_comparison(learner_answer)
    normalized_reference = _normalize_for_comparison(reference_translation)
    normalized_corrected = _normalize_for_comparison(analysis.corrected)
    normalized_natural = _normalize_for_comparison(analysis.natural_version)

    if normalized_answer and normalized_answer == normalized_reference:
        return True

    reference_similarity = _text_similarity(normalized_answer, normalized_reference)
    corrected_similarity = _text_similarity(normalized_answer, normalized_corrected)
    natural_similarity = _text_similarity(normalized_answer, normalized_natural)

    if analysis.severity == "none":
        return True

    if analysis.severity == "low" and not analysis.tags:
        if max(reference_similarity, corrected_similarity, natural_similarity) >= 0.84:
            return True

    return False


def _build_success_translation_analysis(
    *,
    learner_answer: str,
    source_sentence: str,
    reference_translation: str,
    assistant_reply: str | None = None,
) -> TranslationEvaluationAnalysis:
    return TranslationEvaluationAnalysis(
        original=learner_answer,
        corrected=reference_translation,
        explanation="[Good]: Your translation is clear and natural.\n[Tip]: Keep using complete English sentences like this.",
        natural_version=reference_translation,
        retry_prompt="Try the next sentence.",
        tags=[],
        severity="none",
        is_correct=True,
        assistant_reply=assistant_reply or "Good job. You are ready for the next sentence.",
        score=96,
        status="correct",
        native_sentence=source_sentence,
        best_answer=reference_translation,
        feedback_level="excellent",
        correct_answer=reference_translation,
        quick_feedback="Clear answer. You can move on.",
        tense_explanation={
            "tense_or_pattern": "Simple Past",
            "why_this_pattern": "The sentence describes something that already happened.",
            "structure": "Subject + past verb + details",
            "native_to_english_mapping": [],
            "correct_translation_using_structure": reference_translation,
            "similar_example": {
                "native": "",
                "english": reference_translation,
            },
        },
        user_mistake={
            "is_wrong": False,
            "wrong_part": "",
            "replace_with": "",
            "reason": "",
        },
        retry={
            "needed": False,
            "prompt": "You are ready for the next sentence.",
            "hint": None,
        },
        what_is_wrong={
            "title": "What to fix",
            "explanation": "Nothing important to fix here.",
        },
        why_it_is_wrong={
            "title": "Why",
            "explanation": "Your sentence already gives the right meaning in natural English.",
        },
        think_like_this={
            "wrong_thinking": "I must copy every word exactly.",
            "correct_thinking": "I can say the full meaning in natural English.",
        },
        grammar_breakdown={
            "topic": "Natural past sentence",
            "user_sentence_analysis": "Your sentence already gives the correct idea in natural English.",
            "correct_sentence_analysis": "The sentence sounds clear and natural for a past event.",
            "structure": "Subject + past verb + details",
            "example_pattern": "I reached the office late yesterday.",
            "tense_used": "Simple Past",
            "why_this_tense": "The event already happened, so past tense is correct.",
            "native_language_note": "",
        },
        translation_tip="Look for the main time word first, then choose the matching English pattern.",
        practice_examples=[
            {"native": "कल मैं जल्दी घर पहुँचा।", "english": "Yesterday, I reached home early."},
            {"native": "हमने रात को खाना खाया।", "english": "We ate dinner at night."},
        ],
        key_learning="Keep saying the meaning clearly in full English sentences.",
        natural_variations=[reference_translation],
        mistakes=[],
        retry_strategy={
            "should_retry": False,
            "retry_type": "next_question",
            "retry_prompt": "You are ready for the next sentence.",
            "hint": None,
        },
        encouragement=assistant_reply or "Good job. You are ready for the next sentence.",
        should_move_next=True,
    )


def _stabilize_translation_analysis(
    *,
    learner_answer: str,
    reference_translation: str,
    analysis: TranslationEvaluationAnalysis,
    is_accepted: bool,
) -> TranslationEvaluationAnalysis:
    if is_accepted and (analysis.score >= 85 or analysis.is_correct):
        return analysis.model_copy(
            update={
                "corrected": reference_translation,
                "best_answer": reference_translation,
                "correct_answer": reference_translation,
                "natural_version": analysis.natural_version or reference_translation,
                "is_correct": True,
                "score": max(analysis.score, 85),
                "status": "correct",
                "feedback_level": "excellent",
                "severity": "none",
                "assistant_reply": analysis.assistant_reply or "Good job. You are ready for the next sentence.",
                "quick_feedback": "Correct. This structure works well.",
                "user_mistake": {
                    "is_wrong": False,
                    "wrong_part": "",
                    "replace_with": "",
                    "reason": "",
                },
                "what_is_wrong": {
                    "title": "What to fix",
                    "explanation": "Nothing important to fix here.",
                },
                "why_it_is_wrong": {
                    "title": "Why",
                    "explanation": "Your sentence already gives the right meaning in natural English.",
                },
                "retry": {
                    "needed": False,
                    "prompt": "You are ready for the next sentence.",
                    "hint": None,
                },
                "retry_prompt": "Try the next sentence.",
                "retry_strategy": {
                    "should_retry": False,
                    "retry_type": "next_question",
                    "retry_prompt": "You are ready for the next sentence.",
                    "hint": None,
                },
                "encouragement": "Good job. You are ready for the next sentence.",
                "should_move_next": True,
            }
        )

    normalized_reference = _normalize_for_comparison(reference_translation)
    normalized_corrected = _normalize_for_comparison(analysis.corrected)
    normalized_natural = _normalize_for_comparison(analysis.natural_version)
    if max(
        _text_similarity(normalized_corrected, normalized_reference),
        _text_similarity(normalized_natural, normalized_reference),
    ) < 0.45:
        return analysis.model_copy(
            update={
                "corrected": reference_translation,
                "natural_version": reference_translation,
            }
        )
    return analysis


def _build_fallback_translation_analysis(
    *,
    learner_answer: str,
    source_sentence: str,
    reference_translation: str,
) -> TranslationEvaluationAnalysis:
    normalized_answer = _normalize_for_comparison(learner_answer)
    normalized_reference = _normalize_for_comparison(reference_translation)
    similarity = _text_similarity(normalized_answer, normalized_reference)
    is_correct = similarity >= 0.84 or normalized_answer == normalized_reference

    if is_correct:
        return TranslationEvaluationAnalysis(
            original=learner_answer,
            corrected=reference_translation,
            explanation="[Good]: Your translation is clear and natural.\n[Tip]: Keep using complete English sentences like this.",
            natural_version=reference_translation,
            retry_prompt="Try the next sentence.",
            tags=[],
            severity="none",
            is_correct=True,
            assistant_reply="Good job. You are ready for the next sentence.",
            score=96,
            status="correct",
            native_sentence=source_sentence,
            best_answer=reference_translation,
            feedback_level="excellent",
            correct_answer=reference_translation,
            quick_feedback="Clear answer. You can move on.",
            tense_explanation={
                "tense_or_pattern": "Simple Past",
                "why_this_pattern": "The sentence describes something that already happened.",
                "structure": "Subject + past verb + details",
                "native_to_english_mapping": [],
                "correct_translation_using_structure": reference_translation,
                "similar_example": {
                    "native": "",
                    "english": reference_translation,
                },
            },
            user_mistake={"is_wrong": False, "wrong_part": "", "replace_with": "", "reason": ""},
            retry={"needed": False, "prompt": "You are ready for the next sentence.", "hint": None},
            what_is_wrong={"title": "What to fix", "explanation": "Nothing important to fix here."},
            why_it_is_wrong={"title": "Why", "explanation": "Your sentence already gives the right meaning in natural English."},
            think_like_this={
                "wrong_thinking": "I followed the meaning correctly.",
                "correct_thinking": "I can say the full meaning in natural English.",
            },
            grammar_breakdown={
                "topic": "Simple Past",
                "user_sentence_analysis": "Your sentence already expresses the meaning naturally.",
                "correct_sentence_analysis": "The sentence uses a correct past form for a finished event.",
                "structure": "Subject + past verb + details",
                "example_pattern": reference_translation,
                "tense_used": "Simple Past",
                "why_this_tense": "The event already happened, so past tense fits.",
                "native_language_note": "",
            },
            translation_tip="Find the time word and use the past form for finished actions or states.",
            practice_examples=[
                {"native": "कल मैं जल्दी घर पहुँचा।", "english": "Yesterday, I reached home early."},
                {"native": "हमने रात को खाना खाया।", "english": "We ate dinner at night."},
            ],
            key_learning="Keep using natural English past-tense sentences.",
            natural_variations=[reference_translation],
            mistakes=[],
            retry_strategy={"should_retry": False, "retry_type": "next_question", "retry_prompt": "You are ready for the next sentence.", "hint": None},
            encouragement="Good job. You are ready for the next sentence.",
            should_move_next=True,
        )

    return TranslationEvaluationAnalysis(
        original=learner_answer,
        corrected=reference_translation,
        explanation="[Mistake]: Your answer does not fully match the meaning or grammar.\n[Why]: Some important words or grammar need to be fixed.\n[Tip]: Compare your verb tense and the full meaning carefully.",
        natural_version=reference_translation,
        retry_prompt="Please try the same sentence again in correct English.",
        tags=["sentence_structure"],
        severity="medium",
        is_correct=False,
        assistant_reply="Good try. Please try the same sentence again.",
        score=58,
        status="needs_practice",
        native_sentence=source_sentence,
        best_answer=reference_translation,
        feedback_level="needs_practice",
        correct_answer=reference_translation,
        quick_feedback="Good try. Fix the main meaning and try again.",
        tense_explanation={
            "tense_or_pattern": "Sentence correction",
            "why_this_pattern": "English needs one clear pattern that matches the full meaning.",
            "structure": "Subject + verb + object/details",
            "native_to_english_mapping": [],
            "correct_translation_using_structure": reference_translation,
            "similar_example": {
                "native": "",
                "english": reference_translation,
            },
        },
        user_mistake={
            "is_wrong": True,
            "wrong_part": learner_answer or "your sentence",
            "replace_with": reference_translation,
            "reason": "Your answer does not yet follow the English structure needed for this meaning.",
        },
        retry={
            "needed": True,
            "prompt": "Translate again using the correct English structure.",
            "hint": "Focus on the main meaning first.",
        },
        what_is_wrong={
            "title": "What to fix",
            "explanation": "Your answer does not yet match the full meaning of the Hindi sentence.",
        },
        why_it_is_wrong={
            "title": "Why",
            "explanation": "Some important grammar or meaning is still missing in English.",
        },
        think_like_this={
            "wrong_thinking": "I translated the sentence part by part.",
            "correct_thinking": "First say the whole meaning in simple English.",
        },
        grammar_breakdown={
            "topic": "Sentence correction",
            "user_sentence_analysis": "Your sentence does not express the meaning naturally.",
            "correct_sentence_analysis": "The corrected sentence expresses the meaning clearly.",
            "structure": "Subject + verb + object/details",
            "example_pattern": "",
            "tense_used": "",
            "why_this_tense": "",
            "native_language_note": "",
        },
        translation_tip="First find the main meaning, then choose one English pattern that fits it.",
        practice_examples=[
            {"native": "मैं अभी काम कर रहा हूँ।", "english": "I am working right now."},
            {"native": "कल मैं स्कूल के लिए देर से पहुँचा।", "english": "Yesterday, I was late to school."},
        ],
        key_learning="Start with the full meaning, then build one clear English sentence.",
        natural_variations=[reference_translation],
        mistakes=[
            {
                "type": "sentence_structure",
                "wrong": learner_answer or "Your answer",
                "correct": reference_translation,
                "explanation": "Match the full meaning with one clear English sentence.",
            }
        ],
        retry_strategy={
            "should_retry": True,
            "retry_type": "same_sentence",
            "retry_prompt": "Translate the same sentence again in simple English.",
            "hint": "Focus on the main meaning first.",
        },
        encouragement="Good try. Please try the same sentence again.",
        should_move_next=False,
    )


def _build_fallback_translation_clarification_reply(
    *,
    learner_question: str,
    reference_translation: str,
) -> str:
    normalized = learner_question.lower()
    if "subject" in normalized or "word order" in normalized:
        subject = reference_translation.split(" ", 1)[0]
        return (
            f"In normal English statements, the subject usually comes before the main verb. "
            f"That is why this answer starts with '{subject}' in '{reference_translation}'."
        )

    return (
        "I was explaining the same Hindi sentence, not a new one. "
        f"The target meaning here is: '{reference_translation}'. "
        "Ask about any word or grammar point, and I will explain that exact sentence."
    )


async def _build_translation_clarification_message(
    session: AsyncSession,
    *,
    practice_session: PracticeSession,
    translation_item: PracticeTranslationItem,
    learner_question: str,
    learner_level: str | None,
    user_message_metadata: dict[str, Any] | None,
) -> PracticeMessage:
    reply_context = _read_reply_context(user_message_metadata) or {}
    reply_preview_text = reply_context.get("preview_text")
    replied_message_text = None
    original_answer = reply_context.get("original_text")
    corrected_answer = reply_context.get("corrected_text")
    correction_explanation = None
    correction_natural_version = None
    correction_retry_prompt = None

    if isinstance(reply_context.get("source_message_id"), str):
        try:
            source_message_id = uuid.UUID(reply_context["source_message_id"])
        except ValueError:
            source_message_id = None

        if source_message_id is not None:
            source_message = await session.get(PracticeMessage, source_message_id)
            if source_message is not None:
                replied_message_text = source_message.content

            result = await session.execute(
                select(MessageCorrection).where(MessageCorrection.message_id == source_message_id)
            )
            source_correction = result.scalar_one_or_none()
            if source_correction is not None:
                original_answer = original_answer or source_correction.original_text
                corrected_answer = corrected_answer or source_correction.corrected_text
                correction_explanation = source_correction.explanation
                correction_natural_version = source_correction.natural_version
                correction_retry_prompt = source_correction.retry_prompt
                reply_preview_text = reply_preview_text or source_correction.corrected_text

    system_prompt = build_translation_clarification_prompt(
        english_level=learner_level,
        source_sentence=translation_item.source_sentence,
        reference_translation=translation_item.reference_translation,
        learner_question=learner_question,
        reply_preview_text=reply_preview_text if isinstance(reply_preview_text, str) else None,
        replied_message_text=(
            replied_message_text if isinstance(replied_message_text, str) else None
        ),
        original_answer=original_answer if isinstance(original_answer, str) else None,
        corrected_answer=corrected_answer if isinstance(corrected_answer, str) else None,
        correction_explanation=(
            correction_explanation if isinstance(correction_explanation, str) else None
        ),
        correction_natural_version=(
            correction_natural_version
            if isinstance(correction_natural_version, str)
            else None
        ),
        correction_retry_prompt=(
            correction_retry_prompt if isinstance(correction_retry_prompt, str) else None
        ),
    )

    try:
        provider_result = await generate_ai_reply(
            system_prompt=system_prompt,
            conversation=[AIConversationTurn(role="user", content=learner_question)],
        )
        assistant_content = _normalize_text(provider_result.content)
        metadata = {
            "practice_kind": "translation_clarification",
            "translation_item_id": str(translation_item.id),
            "continue_action_label": "Continue learning",
            "provider": provider_result.provider,
            "model": provider_result.model,
            "response_id": provider_result.response_id,
        }
    except (AIProviderConfigurationError, AIProviderResponseError):
        assistant_content = _build_fallback_translation_clarification_reply(
            learner_question=learner_question,
            reference_translation=translation_item.reference_translation,
        )
        metadata = {
            "practice_kind": "translation_clarification",
            "translation_item_id": str(translation_item.id),
            "continue_action_label": "Continue learning",
        }

    return await create_practice_message(
        session=session,
        practice_session=practice_session,
        role="assistant",
        content=assistant_content,
        metadata_json=metadata,
    )


def _general_fluency_examples(
    total_completed_translations: int,
    *,
    effective_level: str | None,
) -> list[tuple[str, str]]:
    level = (effective_level or "beginner").lower()
    if total_completed_translations >= 12 or level == "advanced":
        return [
            (
                "अगर मुझे समय मिला, तो मैं शाम को अपने दोस्त के साथ अंग्रेज़ी बोलने की प्रैक्टिस करूँगा",
                "If I get time, I will practice speaking English with my friend in the evening.",
            ),
            (
                "मीटिंग खत्म होने के बाद मैंने अपनी टीम को प्रोजेक्ट की अगली योजना समझाई",
                "After the meeting ended, I explained the next project plan to my team.",
            ),
            (
                "जब मैं यात्रा करता हूँ, तो मैं नए लोगों से बात करके अपनी अंग्रेज़ी बेहतर बनाने की कोशिश करता हूँ",
                "When I travel, I try to improve my English by talking to new people.",
            ),
            (
                "हाल ही में मैंने महसूस किया कि नियमित अभ्यास से मेरी अंग्रेज़ी बोलने की झिझक कम हो गई है",
                "Recently, I realized that regular practice has reduced my hesitation in speaking English.",
            ),
            (
                "अगर मुझे प्रस्तुति देनी हो, तो मैं पहले मुख्य बिंदु लिखता हूँ और फिर उन्हें जोर से बोलकर अभ्यास करता हूँ",
                "If I have to give a presentation, I first write the main points and then practice saying them aloud.",
            ),
            (
                "कभी-कभी मैं नई शब्दावली याद रखने के लिए उसे अपनी रोज़मर्रा की बातचीत में जानबूझकर इस्तेमाल करता हूँ",
                "Sometimes I intentionally use new vocabulary in my daily conversations to remember it.",
            ),
        ]
    if total_completed_translations >= 6 or level == "intermediate":
        return [
            (
                "आज सुबह मैंने जल्दी नाश्ता किया क्योंकि मुझे समय पर ऑफिस पहुँचना था",
                "This morning, I ate breakfast early because I had to reach the office on time.",
            ),
            (
                "वीकेंड पर मैं अपने परिवार के साथ बाहर खाना खाने जाना पसंद करता हूँ",
                "On weekends, I like to go out to eat with my family.",
            ),
            (
                "मैंने अपने दोस्त को फोन किया ताकि हम कल की योजना के बारे में बात कर सकें",
                "I called my friend so that we could talk about tomorrow's plan.",
            ),
            (
                "जब बारिश शुरू हुई, तब हम जल्दी से दुकान के अंदर चले गए",
                "When it started raining, we quickly went inside the shop.",
            ),
            (
                "मैंने आज का काम पहले पूरा किया ताकि शाम को आराम से पढ़ाई कर सकूँ",
                "I finished today's work early so that I could study peacefully in the evening.",
            ),
            (
                "अगर आप समय पर निकलेंगे, तो हम ट्रेन आसानी से पकड़ लेंगे",
                "If you leave on time, we will catch the train easily.",
            ),
        ]
    return [
        (
            "मेरा नाम राहुल है और मैं रोज़ अंग्रेज़ी सीखता हूँ",
            "My name is Rahul and I practice English every day.",
        ),
        (
            "मैं रोज़ सुबह अंग्रेज़ी बोलने की प्रैक्टिस करता हूँ",
            "I practice speaking English every morning.",
        ),
        (
            "मुझे अपनी अंग्रेज़ी बेहतर बनानी है",
            "I want to improve my English.",
        ),
        (
            "मैं हर दिन पाँच नए अंग्रेज़ी शब्द सीखता हूँ",
            "I learn five new English words every day.",
        ),
        (
            "मेरी बहन शाम को मेरे साथ अंग्रेज़ी बोलती है",
            "My sister speaks English with me in the evening.",
        ),
        (
            "मैं आज जल्दी घर पहुँचना चाहता हूँ",
            "I want to reach home early today.",
        ),
        (
            "हम रविवार को दादी के घर जाते हैं",
            "We go to our grandmother's house on Sunday.",
        ),
    ]


def _fallback_examples(
    focus_title: str,
    *,
    total_completed_translations: int,
    effective_level: str | None,
) -> list[tuple[str, str]]:
    mapping = {
        "Tense practice": [
            (
                "कल मैं जल्दी उठा और आज मैं समय पर काम कर रहा हूँ",
                "Yesterday I woke up early, and today I am working on time.",
            ),
            (
                "अगले हफ्ते मैं अपने दोस्त से मिलूँगा और उसे अपनी नई नौकरी के बारे में बताऊँगा",
                "Next week I will meet my friend and tell him about my new job.",
            ),
            (
                "मैं रोज़ अभ्यास करता हूँ क्योंकि मैंने पिछले साल बहुत कम अंग्रेज़ी बोली थी",
                "I practice every day because I spoke very little English last year.",
            ),
            (
                "आज वह ऑफिस में है, लेकिन कल वह घर से काम कर रहा था",
                "Today he is in the office, but yesterday he was working from home.",
            ),
        ],
        "Past tense practice": [
            (
                "कल मैं ऑफिस गया था",
                "I went to the office yesterday.",
            ),
            (
                "पिछले हफ्ते हम पार्क गए थे",
                "We went to the park last week.",
            ),
            (
                "कल रात मैंने एक फिल्म देखी",
                "I watched a movie last night.",
            ),
            (
                "पिछले महीने हमने अपने पुराने दोस्तों से मुलाकात की",
                "Last month, we met our old friends.",
            ),
            (
                "कल शाम उसने मुझे एक जरूरी ईमेल भेजा",
                "Yesterday evening, he sent me an important email.",
            ),
            (
                "पिछले रविवार मैं घर पर रहा और किताब पढ़ी",
                "Last Sunday, I stayed at home and read a book.",
            ),
        ],
        "Article usage": [
            (
                "मैंने मेज पर किताब रखी",
                "I put the book on the table.",
            ),
            (
                "उसने दरवाज़ा खोला और कमरे में गया",
                "He opened the door and went into the room.",
            ),
            (
                "मैंने किचन में एक कप देखा",
                "I saw a cup in the kitchen.",
            ),
            (
                "उसने एक नई कुर्सी खरीदी और उसे कमरे में रखा",
                "She bought a new chair and kept it in the room.",
            ),
            (
                "मैंने दीवार पर एक तस्वीर देखी",
                "I saw a picture on the wall.",
            ),
            (
                "बच्चे ने बैग से एक पेंसिल निकाली",
                "The child took a pencil out of the bag.",
            ),
        ],
        "Preposition practice": [
            (
                "मैं सुबह स्टेशन पर था",
                "I was at the station in the morning.",
            ),
            (
                "बैग कुर्सी के पास है",
                "The bag is near the chair.",
            ),
            (
                "हम शाम को रेस्टोरेंट में मिले",
                "We met at the restaurant in the evening.",
            ),
            (
                "मेरी चाबियाँ सोफे के नीचे हैं",
                "My keys are under the sofa.",
            ),
            (
                "वह दोपहर में लाइब्रेरी के सामने खड़ा था",
                "He was standing in front of the library in the afternoon.",
            ),
            (
                "मैंने किताब बैग के अंदर रख दी",
                "I put the book inside the bag.",
            ),
        ],
        "Longer answers": [
            (
                "पिछले हफ्ते मैं अपने दोस्तों के साथ बाज़ार गया और हमने डिनर किया",
                "Last week, I went to the market with my friends and we had dinner.",
            ),
            (
                "आज सुबह मैं जल्दी उठा, चाय पी, और फिर ऑफिस के लिए निकला",
                "This morning, I woke up early, drank tea, and then left for the office.",
            ),
            (
                "वीकेंड पर मैं घर साफ करता हूँ और अपनी फैमिली के साथ समय बिताता हूँ",
                "On weekends, I clean the house and spend time with my family.",
            ),
            (
                "जब मैं ऑफिस से वापस आया, तब मैंने थोड़ी देर आराम किया और फिर अपनी अंग्रेज़ी की क्लास अटेंड की",
                "When I came back from the office, I rested for a while and then attended my English class.",
            ),
            (
                "अगर मौसम अच्छा रहा, तो हम कल पार्क जाएंगे और वहाँ कुछ समय टहलेंगे",
                "If the weather stays nice, we will go to the park tomorrow and walk there for some time.",
            ),
            (
                "मैं रोज़ थोड़ा-थोड़ा अभ्यास करता हूँ क्योंकि मुझे पता है कि लगातार मेहनत से ही सुधार होता है",
                "I practice a little every day because I know that improvement comes only with consistent effort.",
            ),
        ],
    }
    return mapping.get(
        focus_title,
        _general_fluency_examples(
            total_completed_translations,
            effective_level=effective_level,
        ),
    )


def _pick_fallback_example(
    focus_title: str,
    *,
    completed_source_sentences: list[str],
    excluded_source_sentences: list[str] | None = None,
    total_completed_translations: int = 0,
    effective_level: str | None = None,
) -> tuple[str, str]:
    examples = _fallback_examples(
        focus_title,
        total_completed_translations=total_completed_translations,
        effective_level=effective_level,
    )
    disallowed_keys = {
        _sentence_key(sentence)
        for sentence in [*completed_source_sentences, *(excluded_source_sentences or [])]
        if sentence.strip()
    }
    for example in examples:
        if _sentence_key(example[0]) not in disallowed_keys:
            return example
    return examples[0]


def _prompt_metadata(prompt: TranslationPromptDraft) -> dict[str, Any]:
    return {
        "generator_source": prompt.source,
        "provider": prompt.provider,
        "model": prompt.model,
        "response_id": prompt.response_id,
    }


def _prompt_focus_tag(
    top_weak_areas: list[str] | None,
    *,
    recommended_focus_area: str | None = None,
) -> str | None:
    if recommended_focus_area and recommended_focus_area.strip():
        return recommended_focus_area.strip()
    if not top_weak_areas:
        return None
    return next((tag for tag in top_weak_areas if tag.strip()), None)


def build_translation_message_metadata(
    *,
    translation_item: PracticeTranslationItem,
    is_starter: bool,
    is_retry_prompt: bool = False,
) -> dict[str, Any]:
    metadata = {
        "is_starter": is_starter,
        "practice_kind": "translation_prompt",
        "translation_item_id": str(translation_item.id),
        "translation_source_sentence": translation_item.source_sentence,
        "translation_reference_answer": translation_item.reference_translation,
        "translation_round": translation_item.order_index,
        "is_retry_prompt": is_retry_prompt,
        "focus_tag": translation_item.focus_tag,
        "focus_label": (
            learning_area_label(translation_item.focus_tag)
            if translation_item.focus_tag
            else None
        ),
    }
    if translation_item.generator_metadata:
        metadata.update(translation_item.generator_metadata)
    return metadata


async def _load_translation_context(
    session: AsyncSession,
    *,
    practice_session: PracticeSession,
) -> tuple[PracticeSession, list[str], list[str], int, str | None, UserLearningProfile]:
    from app.services.practice_session_service import get_user_practice_session

    loaded_session = await get_user_practice_session(
        session=session,
        user_id=practice_session.user_id,
        session_id=practice_session.id,
        include_messages=True,
        include_user_context=True,
    )
    completed_source_sentences = await list_completed_translation_source_sentences(
        session,
        session_id=loaded_session.id,
    )
    learning_summary = await get_personalization_summary(
        session,
        user_id=loaded_session.user_id,
    )
    user_learning_profile = await get_or_create_user_learning_profile(
        session,
        user_id=loaded_session.user_id,
        preferred_level=loaded_session.user.english_level,
    )
    global_completed_source_sentences = (
        list(learning_summary.completed_translation_sources)
        if learning_summary is not None
        else []
    )
    total_completed_translations = (
        learning_summary.total_translation_items_completed
        if learning_summary is not None
        else 0
    )
    top_weak_areas = ordered_learning_areas(user_learning_profile.weak_areas_json)
    if not top_weak_areas and learning_summary is not None:
        top_weak_areas = list(learning_summary.top_weak_areas or [])
    effective_level = user_learning_profile.current_difficulty or get_effective_translation_level(
        preferred_level=loaded_session.user.english_level,
        learning_summary=learning_summary,
    )
    return (
        loaded_session,
        _merge_completed_source_sentences(
            global_completed_source_sentences,
            completed_source_sentences,
        ),
        top_weak_areas,
        total_completed_translations,
        effective_level,
        user_learning_profile,
    )


async def generate_translation_prompt(
    session: AsyncSession,
    *,
    practice_session: PracticeSession,
    excluded_source_sentences: list[str] | None = None,
) -> TranslationPromptDraft:
    loaded_session, completed_source_sentences, top_weak_areas, total_completed_translations, effective_level, user_learning_profile = await _load_translation_context(
        session,
        practice_session=practice_session,
    )
    learner = loaded_session.user
    learning_profile = learner.learning_profile
    topic = loaded_session.topic

    system_prompt = build_translation_starter_prompt(
        english_level=effective_level or learner.english_level,
        goal=learning_profile.goal if learning_profile else None,
        topic_title=topic.title if topic is not None else None,
        topic_description=topic.description if topic is not None else None,
        top_weak_areas=top_weak_areas,
        recommended_focus_area=user_learning_profile.recommended_focus_area,
        repeated_mistakes=list(user_learning_profile.repeated_mistakes_json or []),
        recent_source_sentences=completed_source_sentences,
        total_completed_translations=total_completed_translations,
    )
    focus_tag = _prompt_focus_tag(
        top_weak_areas,
        recommended_focus_area=user_learning_profile.recommended_focus_area,
    )
    disallowed_source_keys = {
        _sentence_key(sentence)
        for sentence in [*completed_source_sentences, *(excluded_source_sentences or [])]
        if sentence.strip()
    }
    for attempt in range(1, _TRANSLATION_PROMPT_ATTEMPTS + 1):
        try:
            provider_result = await generate_structured_json(
                system_prompt=system_prompt,
                conversation=[],
                schema_name="translation_practice_prompt",
                json_schema={
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "source_sentence": {"type": "string"},
                        "reference_translation": {"type": "string"},
                        "assistant_prompt": {"type": "string"},
                    },
                    "required": [
                        "source_sentence",
                        "reference_translation",
                        "assistant_prompt",
                    ],
                },
            )
        except (AIProviderConfigurationError, AIProviderParseError, AIProviderResponseError) as exc:
            logger.warning(
                "Translation prompt generation failed on attempt %s/%s: %s",
                attempt,
                _TRANSLATION_PROMPT_ATTEMPTS,
                exc,
            )
            continue

        source_sentence = _normalize_text(str(provider_result.data.get("source_sentence", "")))
        reference_translation = _normalize_text(
            str(provider_result.data.get("reference_translation", ""))
        )
        if not source_sentence or not reference_translation:
            logger.warning(
                "Translation prompt attempt %s/%s returned incomplete content",
                attempt,
                _TRANSLATION_PROMPT_ATTEMPTS,
            )
            continue
        if not _contains_devanagari(source_sentence):
            logger.warning(
                "Translation prompt attempt %s/%s rejected non-Devanagari source: %s",
                attempt,
                _TRANSLATION_PROMPT_ATTEMPTS,
                source_sentence,
            )
            continue
        if _sentence_key(source_sentence) in disallowed_source_keys:
            logger.info(
                "Translation prompt attempt %s/%s repeated an excluded/completed sentence",
                attempt,
                _TRANSLATION_PROMPT_ATTEMPTS,
            )
            continue

        return TranslationPromptDraft(
            source_sentence=_ensure_sentence_punctuation(source_sentence),
            reference_translation=reference_translation,
            assistant_prompt=_format_translation_prompt_message(
                source_sentence=source_sentence,
                intro="Translate this Hindi sentence into English.",
            ),
            source="ai",
            provider=provider_result.provider,
            model=provider_result.model,
            response_id=provider_result.response_id,
            focus_tag=focus_tag,
        )

    recommendation = build_focus_recommendation(
        [user_learning_profile.recommended_focus_area, *top_weak_areas]
        if user_learning_profile.recommended_focus_area
        else top_weak_areas
    )
    source_sentence, reference_translation = _pick_fallback_example(
        recommendation.focus_title,
        completed_source_sentences=completed_source_sentences,
        excluded_source_sentences=excluded_source_sentences,
        total_completed_translations=total_completed_translations,
        effective_level=effective_level,
    )
    logger.info(
        "Using fallback translation prompt for focus '%s' at level '%s' after AI generation fallback",
        recommendation.focus_title,
        effective_level or learner.english_level or "unknown",
    )
    return TranslationPromptDraft(
        source_sentence=_ensure_sentence_punctuation(source_sentence),
        reference_translation=reference_translation,
        assistant_prompt=_format_translation_prompt_message(
            source_sentence=source_sentence,
            intro="Translate this Hindi sentence into English.",
        ),
        focus_tag=focus_tag,
    )


async def ensure_active_translation_item(
    session: AsyncSession,
    *,
    practice_session: PracticeSession,
    excluded_source_sentences: list[str] | None = None,
) -> PracticeTranslationItem:
    active_item = await get_active_translation_item(session, session_id=practice_session.id)
    if active_item is not None:
        return active_item

    prompt = await generate_translation_prompt(
        session,
        practice_session=practice_session,
        excluded_source_sentences=excluded_source_sentences,
    )
    return await create_translation_item(
        session=session,
        practice_session=practice_session,
        source_sentence=prompt.source_sentence,
        reference_translation=prompt.reference_translation,
        assistant_prompt=prompt.assistant_prompt,
        focus_tag=prompt.focus_tag,
        generator_metadata=_prompt_metadata(prompt),
    )


async def ensure_translation_session_starter(
    session: AsyncSession,
    *,
    practice_session: PracticeSession,
) -> PracticeMessage:
    translation_item = await ensure_active_translation_item(
        session=session,
        practice_session=practice_session,
    )
    return await create_practice_message(
        session=session,
        practice_session=practice_session,
        role="assistant",
        content=translation_item.assistant_prompt,
        metadata_json=build_translation_message_metadata(
            translation_item=translation_item,
            is_starter=True,
        ),
    )


async def save_translation_correction(
    session: AsyncSession,
    *,
    user_id: Any,
    message_id: Any,
    original_text: str,
    analysis: TranslationEvaluationAnalysis,
) -> MessageCorrection:
    correction = MessageCorrection(
        message_id=message_id,
        original_text=original_text,
        corrected_text=analysis.corrected,
        explanation=analysis.explanation,
        natural_version=analysis.natural_version,
        retry_prompt=analysis.retry_prompt,
        tags=analysis.tags,
        feedback_json={
            "is_correct": analysis.is_correct,
            "score": analysis.score,
            "status": analysis.status,
            "native_sentence": analysis.native_sentence,
            "feedback_level": analysis.feedback_level,
            "user_answer": analysis.original,
            "best_answer": analysis.best_answer,
            "correct_answer": analysis.correct_answer,
            "natural_answer": analysis.natural_version,
            "quick_feedback": analysis.quick_feedback,
            "tense_explanation": _dump_model(analysis.tense_explanation),
            "user_mistake": _dump_model(analysis.user_mistake),
            "retry": _dump_model(analysis.retry),
            "what_is_wrong": _dump_model(analysis.what_is_wrong),
            "why_it_is_wrong": _dump_model(analysis.why_it_is_wrong),
            "think_like_this": _dump_model(analysis.think_like_this),
            "grammar_breakdown": _dump_model(analysis.grammar_breakdown),
            "translation_tip": analysis.translation_tip,
            "practice_examples": [_dump_model(item) for item in analysis.practice_examples],
            "key_learning": analysis.key_learning,
            "natural_variations": analysis.natural_variations,
            "mistakes": [_dump_model(item) for item in analysis.mistakes],
            "retry_strategy": _dump_model(analysis.retry_strategy),
            "encouragement": analysis.encouragement,
            "should_move_next": analysis.should_move_next,
        },
        severity=analysis.severity,
    )
    session.add(correction)
    await session.commit()
    await session.refresh(correction)
    await try_update_personalization_after_correction(
        session=session,
        user_id=user_id,
        user_message=SimpleNamespace(content=original_text),
        correction=correction,
    )
    return correction


async def _build_next_translation_message(
    session: AsyncSession,
    *,
    practice_session: PracticeSession,
    excluded_source_sentences: list[str] | None = None,
) -> PracticeMessage:
    next_item = await ensure_active_translation_item(
        session=session,
        practice_session=practice_session,
        excluded_source_sentences=excluded_source_sentences,
    )
    return await create_practice_message(
        session=session,
        practice_session=practice_session,
        role="assistant",
        content=_format_translation_prompt_message(
            source_sentence=next_item.source_sentence,
            intro="Nice work. Now translate the next Hindi sentence into English.",
        ),
        metadata_json=build_translation_message_metadata(
            translation_item=next_item,
            is_starter=False,
        ),
    )


async def _build_translation_completion_message(
    session: AsyncSession,
    *,
    practice_session: PracticeSession,
    completed_items: int,
    focus_label: str | None,
) -> PracticeMessage:
    focus_sentence = (
        f" Your next focus is {focus_label.lower()}."
        if focus_label
        else " Keep building clear and natural English sentences."
    )
    return await create_practice_message(
        session=session,
        practice_session=practice_session,
        role="assistant",
        content=f"Excellent work. You completed {completed_items} translation items in this session.{focus_sentence}",
        metadata_json={
            "practice_kind": "session_completion",
            "is_session_completion": True,
            "completed_items": completed_items,
            "focus_label": focus_label,
        },
    )


async def handle_translation_practice_turn(
    session: AsyncSession,
    *,
    practice_session: PracticeSession,
    content: str,
    user_message_metadata: dict[str, Any] | None = None,
) -> tuple[PracticeMessage, PracticeMessage, MessageCorrection | None, Any | None]:
    loaded_session, _, _, _, _, _ = await _load_translation_context(
        session,
        practice_session=practice_session,
    )
    loaded_session_id = loaded_session.id
    session_user_id = loaded_session.user_id
    learner = loaded_session.user
    learning_profile = learner.learning_profile
    active_item = await ensure_active_translation_item(
        session=session,
        practice_session=loaded_session,
    )
    active_item_id = active_item.id
    source_sentence = active_item.source_sentence
    reference_translation = active_item.reference_translation

    user_message = await create_practice_message(
        session=session,
        practice_session=loaded_session,
        role="user",
        content=content,
        metadata_json=user_message_metadata,
    )
    user_message_id = user_message.id
    user_message_text = user_message.content

    learner_level = get_effective_translation_level(
        preferred_level=learner.english_level,
        learning_summary=await get_personalization_summary(session, user_id=session_user_id),
    ) or learner.english_level

    if _looks_like_clarification_question(
        content=content,
        user_message_metadata=user_message_metadata,
    ):
        assistant_message = await _build_translation_clarification_message(
            session=session,
            practice_session=loaded_session,
            translation_item=active_item,
            learner_question=content,
            learner_level=learner_level,
            user_message_metadata=user_message_metadata,
        )
        return user_message, assistant_message, None, None

    system_prompt = build_translation_evaluation_prompt(
        english_level=learner_level,
        goal=learning_profile.goal if learning_profile else None,
        source_sentence=source_sentence,
        reference_translation=reference_translation,
    )

    correction: MessageCorrection | None = None
    try:
        provider_result = await generate_structured_json(
            system_prompt=system_prompt,
            conversation=[
                AIConversationTurn(
                    role="user",
                    content=f"Learner answer: {content}",
                )
            ],
            schema_name="translation_practice_evaluation",
            json_schema=get_translation_evaluation_json_schema(),
        )
        tutor_payload = TranslationTutorEvaluationPayload.model_validate(provider_result.data)
        analysis = _normalize_translation_analysis(
            learner_answer=content,
            source_sentence=source_sentence,
            reference_translation=reference_translation,
            payload=tutor_payload,
        )
    except (
        AIProviderConfigurationError,
        AIProviderParseError,
        AIProviderResponseError,
        ValidationError,
    ):
        analysis = _build_fallback_translation_analysis(
            learner_answer=content,
            source_sentence=source_sentence,
            reference_translation=reference_translation,
        )

    is_accepted = _should_accept_translation_answer(
        learner_answer=content,
        reference_translation=reference_translation,
        analysis=analysis,
    )
    if analysis.should_move_next and analysis.score >= 70:
        is_accepted = True
    analysis = _stabilize_translation_analysis(
        learner_answer=content,
        reference_translation=reference_translation,
        analysis=analysis,
        is_accepted=is_accepted,
    )
    correction = await save_translation_correction(
        session=session,
        user_id=session_user_id,
        message_id=user_message_id,
        original_text=user_message_text,
        analysis=analysis,
    )
    await try_update_user_learning_profile_after_translation_attempt(
        session=session,
        user=learner,
        practice_session=loaded_session,
        translation_item=active_item,
        correction=correction,
        is_correct=is_accepted,
    )
    loaded_session = await get_user_practice_session(
        session=session,
        user_id=session_user_id,
        session_id=loaded_session_id,
        include_messages=True,
        include_user_context=True,
    )
    active_item = await get_active_translation_item(session, session_id=loaded_session_id)
    if active_item is None:
        active_item = await session.get(PracticeTranslationItem, active_item_id)
    if active_item is None:
        raise RuntimeError("Active translation item disappeared during translation practice turn")

    if is_accepted:
        await mark_translation_item_completed(
            session=session,
            translation_item=active_item,
            learner_answer=content,
        )
        await record_completed_translation_item(
            session=session,
            user_id=session_user_id,
            source_sentence=source_sentence,
            attempts_used=(active_item.attempt_count or 0) + 1,
            preferred_level=learner.english_level,
        )
        refreshed_session, _, _, _, _, _ = await _load_translation_context(
            session,
            practice_session=loaded_session,
        )
        completed_source_sentences = await list_completed_translation_source_sentences(
            session,
            session_id=loaded_session_id,
        )
        completed_items = len(completed_source_sentences)
        if completed_items >= _AUTO_COMPLETE_TRANSLATION_ITEMS:
            completed_session = await complete_practice_session(
                session=session,
                user_id=session_user_id,
                session_id=loaded_session_id,
            )
            completed_session = await get_user_practice_session(
                session=session,
                user_id=session_user_id,
                session_id=loaded_session_id,
                include_messages=True,
                include_user_context=True,
            )
            completion_summary = await build_practice_session_completion_summary(
                session=session,
                practice_session=completed_session,
                auto_completed=True,
                completed_items=completed_items,
            )
            assistant_message = await _build_translation_completion_message(
                session=session,
                practice_session=completed_session,
                completed_items=completed_items,
                focus_label=completion_summary.focus_area,
            )
            return user_message, assistant_message, correction, completion_summary

        assistant_message = await _build_next_translation_message(
            session=session,
            practice_session=refreshed_session,
            excluded_source_sentences=[source_sentence],
        )
    else:
        active_item = await record_translation_item_retry(
            session=session,
            translation_item=active_item,
            learner_answer=content,
        )
        assistant_message = await create_practice_message(
            session=session,
            practice_session=loaded_session,
            role="assistant",
            content=_format_translation_prompt_message(
                source_sentence=source_sentence,
                intro="Let's try that again. Translate the same Hindi sentence into English.",
            ),
            metadata_json=build_translation_message_metadata(
                translation_item=active_item,
                is_starter=False,
                is_retry_prompt=True,
            ),
        )

    return user_message, assistant_message, correction, None
