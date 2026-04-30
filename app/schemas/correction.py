from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CorrectionSeverity = Literal["none", "low", "medium", "high"]
FeedbackLevel = Literal["excellent", "good", "needs_practice"]
DetailedMistakeType = Literal[
    "grammar",
    "vocabulary",
    "tense",
    "sentence_structure",
    "word_order",
    "meaning",
    "word_by_word_translation",
    "spelling",
]
_DETAILED_MISTAKE_TYPES = {
    "grammar",
    "vocabulary",
    "tense",
    "sentence_structure",
    "word_order",
    "meaning",
    "word_by_word_translation",
    "spelling",
}


class CorrectionAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    original: str = Field(min_length=1)
    corrected: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    natural_version: str = Field(min_length=1)
    retry_prompt: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    severity: CorrectionSeverity


class TranslationEvaluationAnalysis(CorrectionAnalysis):
    is_correct: bool
    assistant_reply: str = Field(min_length=1)
    score: int = Field(ge=0, le=100)
    status: Literal["correct", "almost", "needs_practice"]
    native_sentence: str = Field(min_length=1)
    best_answer: str = Field(min_length=1)
    feedback_level: FeedbackLevel
    correct_answer: str = Field(min_length=1)
    quick_feedback: str = Field(min_length=1)
    tense_explanation: "TutorTenseExplanation"
    user_mistake: "TutorUserMistake"
    retry: "TutorRetryInstruction"
    what_is_wrong: "TutorFeedbackSection"
    why_it_is_wrong: "TutorFeedbackSection"
    think_like_this: "TutorThinkingPattern"
    grammar_breakdown: "TutorGrammarBreakdown"
    translation_tip: str = Field(min_length=1)
    practice_examples: list["TutorSimilarExample"] = Field(default_factory=list)
    key_learning: str = Field(min_length=1)
    natural_variations: list[str] = Field(default_factory=list)
    mistakes: list["TutorDetailedMistake"] = Field(default_factory=list)
    retry_strategy: "TutorRetryStrategy"
    encouragement: str = Field(min_length=1)
    should_move_next: bool


class TranslationTutorEvaluationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    score: int = Field(ge=0, le=100)
    status: Literal["correct", "almost", "needs_practice"]
    best_answer: str = Field(min_length=1)
    mistake: "TutorCompactMistake"
    pattern: "TutorCompactPattern"
    meaning_mapping: list["TutorMeaningMappingItem"] = Field(default_factory=list)
    natural_variations: list[str] = Field(default_factory=list)


class TutorNativeMappingItem(BaseModel):
    native_part: str = Field(min_length=1)
    english_part: str = Field(min_length=1)
    role: str = Field(min_length=1)


class TutorSimilarExample(BaseModel):
    native: str = Field(default="")
    english: str = Field(min_length=1)


class TutorTenseExplanation(BaseModel):
    tense_or_pattern: str = Field(min_length=1)
    why_this_pattern: str = Field(min_length=1)
    structure: str = Field(min_length=1)
    native_to_english_mapping: list["TutorNativeMappingItem"] = Field(default_factory=list)
    correct_translation_using_structure: str = Field(min_length=1)
    similar_example: "TutorSimilarExample"


class TutorUserMistake(BaseModel):
    is_wrong: bool
    wrong_part: str = Field(default="")
    replace_with: str = Field(default="")
    reason: str = Field(default="")


class TutorRetryInstruction(BaseModel):
    needed: bool
    prompt: str = Field(min_length=1)
    hint: str | None = None


class TutorCompactMistake(BaseModel):
    has_error: bool
    wrong_part: str = Field(default="")
    correction: str = Field(default="")
    explanation: str = Field(default="")


class TutorCompactPattern(BaseModel):
    name: str = Field(min_length=1)
    structure: str = Field(min_length=1)
    usage_note: str = Field(min_length=1)
    translation_tip: str = Field(min_length=1)
    examples: list["TutorSimilarExample"] = Field(default_factory=list)


class TutorMeaningMappingItem(BaseModel):
    native: str = Field(min_length=1)
    english: str = Field(min_length=1)
    note: str | None = None


class TutorFeedbackSection(BaseModel):
    title: str = Field(min_length=1)
    explanation: str = Field(min_length=1)


class TutorThinkingPattern(BaseModel):
    wrong_thinking: str = Field(min_length=1)
    correct_thinking: str = Field(min_length=1)


class TutorGrammarBreakdown(BaseModel):
    topic: str = Field(min_length=1)
    user_sentence_analysis: str = Field(min_length=1)
    correct_sentence_analysis: str = Field(min_length=1)
    structure: str = Field(min_length=1)
    example_pattern: str = Field(default="")
    tense_used: str = Field(default="")
    why_this_tense: str = Field(default="")
    native_language_note: str = Field(default="")


class TutorDetailedMistake(BaseModel):
    type: DetailedMistakeType
    wrong: str = Field(min_length=1)
    correct: str = Field(min_length=1)
    explanation: str = Field(min_length=1)


class TutorRetryStrategy(BaseModel):
    should_retry: bool
    retry_type: Literal["same_sentence", "hint", "fill_blank", "next_question"]
    retry_prompt: str = Field(min_length=1)
    hint: str | None = None


class MessageCorrectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    message_id: uuid.UUID
    attempt_id: str
    is_correct: bool
    score: int
    status: Literal["correct", "almost", "needs_practice"]
    native_sentence: str
    feedback_level: FeedbackLevel
    user_answer: str
    best_answer: str
    correct_answer: str
    natural_answer: str
    quick_feedback: str
    tense_explanation: TutorTenseExplanation
    user_mistake: TutorUserMistake
    retry: TutorRetryInstruction
    what_is_wrong: TutorFeedbackSection
    why_it_is_wrong: TutorFeedbackSection
    think_like_this: TutorThinkingPattern
    grammar_breakdown: TutorGrammarBreakdown
    translation_tip: str
    practice_examples: list[TutorSimilarExample]
    key_learning: str
    natural_variations: list[str]
    mistakes: list[TutorDetailedMistake]
    retry_strategy: TutorRetryStrategy
    encouragement: str
    should_move_next: bool
    original_text: str
    corrected_text: str
    explanation: str
    natural_version: str
    retry_prompt: str
    tags: list[str] | None
    severity: str
    feedback_json: dict[str, Any] | None = None
    created_at: datetime


def _score_from_severity(severity: str) -> int:
    return {
        "none": 96,
        "low": 82,
        "medium": 68,
        "high": 45,
    }.get(severity, 60)


def _feedback_level_from_score(score: int) -> FeedbackLevel:
    if score >= 85:
        return "excellent"
    if score >= 60:
        return "good"
    return "needs_practice"


def _status_from_score(score: int, *, is_correct: bool) -> Literal["correct", "almost", "needs_practice"]:
    if is_correct or score >= 85:
        return "correct"
    if score >= 60:
        return "almost"
    return "needs_practice"


def _section(title: str, explanation: str) -> TutorFeedbackSection:
    return TutorFeedbackSection(title=title, explanation=explanation.strip())


def _safe_section(value: Any, *, title: str, explanation: str) -> TutorFeedbackSection:
    try:
        if isinstance(value, dict):
            return TutorFeedbackSection.model_validate(value)
    except Exception:
        pass
    return _section(title, explanation)


def _safe_thinking_pattern(value: Any, *, wrong_thinking: str, correct_thinking: str) -> TutorThinkingPattern:
    try:
        if isinstance(value, dict):
            return TutorThinkingPattern.model_validate(value)
    except Exception:
        pass
    return TutorThinkingPattern(
        wrong_thinking=wrong_thinking,
        correct_thinking=correct_thinking,
    )


def _safe_retry_strategy(
    value: Any,
    *,
    should_retry: bool,
    retry_type: str,
    retry_prompt: str,
    hint: str | None,
) -> TutorRetryStrategy:
    try:
        if isinstance(value, dict):
            return TutorRetryStrategy.model_validate(value)
    except Exception:
        pass
    return TutorRetryStrategy(
        should_retry=should_retry,
        retry_type=retry_type,  # type: ignore[arg-type]
        retry_prompt=retry_prompt,
        hint=hint,
    )


def _safe_grammar_breakdown(value: Any) -> TutorGrammarBreakdown:
    try:
        if isinstance(value, dict):
            return TutorGrammarBreakdown.model_validate(value)
    except Exception:
        pass
    return TutorGrammarBreakdown(
        topic="Sentence correction",
        user_sentence_analysis="Your sentence does not express the meaning naturally.",
        correct_sentence_analysis="The corrected sentence expresses the meaning clearly.",
        structure="Subject + verb + object/details",
        example_pattern="",
        tense_used="",
        why_this_tense="",
        native_language_note="",
    )


def _safe_tense_explanation(value: Any, *, corrected_text: str) -> TutorTenseExplanation:
    try:
        if isinstance(value, dict):
            return TutorTenseExplanation.model_validate(value)
    except Exception:
        pass
    return TutorTenseExplanation(
        tense_or_pattern="Sentence correction",
        why_this_pattern="This structure expresses the meaning more naturally in English.",
        structure="Subject + verb + object/details",
        native_to_english_mapping=[],
        correct_translation_using_structure=corrected_text,
        similar_example=TutorSimilarExample(native="", english=corrected_text),
    )


def _safe_user_mistake(value: Any) -> TutorUserMistake:
    try:
        if isinstance(value, dict):
            return TutorUserMistake.model_validate(value)
    except Exception:
        pass
    return TutorUserMistake(is_wrong=False, wrong_part="", replace_with="", reason="")


def _safe_retry_instruction(value: Any, *, needed: bool, prompt: str, hint: str | None) -> TutorRetryInstruction:
    try:
        if isinstance(value, dict):
            return TutorRetryInstruction.model_validate(value)
    except Exception:
        pass
    return TutorRetryInstruction(needed=needed, prompt=prompt, hint=hint)


def _fallback_mistake_items(tags: list[str] | None, corrected_text: str) -> list[TutorDetailedMistake]:
    normalized_tags = tags or ["sentence_structure"]
    items: list[TutorDetailedMistake] = []
    for tag in normalized_tags[:3]:
        items.append(
            TutorDetailedMistake(
                type=tag if tag in _DETAILED_MISTAKE_TYPES else "sentence_structure",
                wrong="Part of your sentence needs to change.",
                correct=corrected_text,
                explanation="Try to match the full meaning with a natural English sentence.",
            )
        )
    return items


def build_message_correction_response(correction: Any) -> MessageCorrectionResponse:
    feedback_json = correction.feedback_json if isinstance(getattr(correction, "feedback_json", None), dict) else {}
    original_text = str(correction.original_text)
    corrected_text = str(correction.corrected_text)
    natural_version = str(correction.natural_version)
    retry_prompt = str(correction.retry_prompt)
    severity = str(correction.severity)
    score = int(feedback_json.get("score") or _score_from_severity(severity))
    feedback_level_value = str(feedback_json.get("feedback_level") or _feedback_level_from_score(score)).strip()
    feedback_level: FeedbackLevel = (
        feedback_level_value if feedback_level_value in {"excellent", "good", "needs_practice"} else _feedback_level_from_score(score)
    )
    fallback_is_correct = severity == "none" or score >= 85
    status_value = str(feedback_json.get("status") or _status_from_score(score, is_correct=fallback_is_correct)).strip()
    status: Literal["correct", "almost", "needs_practice"] = (
        status_value if status_value in {"correct", "almost", "needs_practice"} else _status_from_score(score, is_correct=fallback_is_correct)
    )
    mistakes_payload = feedback_json.get("mistakes")
    parsed_mistakes = (
        [
            TutorDetailedMistake.model_validate(item)
            for item in mistakes_payload
            if isinstance(item, dict)
        ]
        if isinstance(mistakes_payload, list)
        else _fallback_mistake_items(correction.tags, corrected_text)
    )
    if not parsed_mistakes:
        parsed_mistakes = _fallback_mistake_items(correction.tags, corrected_text)
    variations = feedback_json.get("natural_variations")
    natural_variations = (
        [str(item).strip() for item in variations if str(item).strip()]
        if isinstance(variations, list)
        else [natural_version]
    )
    if not natural_variations:
        natural_variations = [natural_version]

    retry_strategy_payload = feedback_json.get("retry_strategy")
    retry_strategy = _safe_retry_strategy(
        retry_strategy_payload,
        should_retry=not fallback_is_correct,
        retry_type="next_question" if fallback_is_correct else "same_sentence",
        retry_prompt=retry_prompt,
        hint=None if fallback_is_correct else "Focus on the main meaning first.",
    )
    tense_explanation = _safe_tense_explanation(
        feedback_json.get("tense_explanation"),
        corrected_text=corrected_text,
    )
    user_mistake = _safe_user_mistake(feedback_json.get("user_mistake"))
    retry = _safe_retry_instruction(
        feedback_json.get("retry"),
        needed=not fallback_is_correct,
        prompt=retry_prompt,
        hint=None if fallback_is_correct else "Focus on the main meaning first.",
    )

    return MessageCorrectionResponse(
        id=correction.id,
        message_id=correction.message_id,
        attempt_id=str(correction.id),
        is_correct=bool(feedback_json.get("is_correct", fallback_is_correct)),
        score=score,
        status=status,
        native_sentence=str(feedback_json.get("native_sentence") or original_text),
        feedback_level=feedback_level,
        user_answer=str(feedback_json.get("user_answer") or original_text),
        best_answer=str(feedback_json.get("best_answer") or corrected_text),
        correct_answer=str(feedback_json.get("correct_answer") or corrected_text),
        natural_answer=str(feedback_json.get("natural_answer") or natural_version or corrected_text),
        quick_feedback=str(
            feedback_json.get("quick_feedback")
            or ("Clear answer. You can move on." if fallback_is_correct else "Good try. Fix the main mistake and try again.")
        ),
        tense_explanation=tense_explanation,
        user_mistake=user_mistake,
        retry=retry,
        what_is_wrong=_safe_section(
            feedback_json.get("what_is_wrong"),
            title="What to fix",
            explanation=(
                "Your sentence needs a clearer English pattern."
                if not fallback_is_correct
                else "Nothing important to fix here."
            ),
        ),
        why_it_is_wrong=_safe_section(
            feedback_json.get("why_it_is_wrong"),
            title="Why",
            explanation=(
                "Try to express the meaning in natural English instead of translating word by word."
                if not fallback_is_correct
                else "Your meaning and grammar are already clear."
            ),
        ),
        think_like_this=_safe_thinking_pattern(
            feedback_json.get("think_like_this"),
            wrong_thinking=(
                "I translated each word directly." if not fallback_is_correct else "I stayed close to the idea."
            ),
            correct_thinking=(
                "First say the meaning in simple English."
                if not fallback_is_correct
                else "I expressed the whole meaning naturally."
            ),
        ),
        grammar_breakdown=_safe_grammar_breakdown(feedback_json.get("grammar_breakdown")),
        translation_tip=str(
            feedback_json.get("translation_tip")
            or feedback_json.get("key_learning")
            or "Follow the sentence pattern first, then add place or time."
        ),
        practice_examples=[
            TutorSimilarExample.model_validate(item)
            for item in feedback_json.get("practice_examples", [])
            if isinstance(item, dict)
        ][:2]
        or [tense_explanation.similar_example],
        key_learning=str(
            feedback_json.get("key_learning")
            or ("Say the idea in natural English, not word by word." if not fallback_is_correct else "Keep using clear natural sentence patterns.")
        ),
        natural_variations=natural_variations[:3],
        mistakes=parsed_mistakes,
        retry_strategy=retry_strategy,
        encouragement=str(
            feedback_json.get("encouragement")
            or ("Nice work. Go to the next sentence." if fallback_is_correct else "You are close. Try one cleaner English sentence.")
        ),
        should_move_next=bool(feedback_json.get("should_move_next", fallback_is_correct)),
        original_text=original_text,
        corrected_text=corrected_text,
        explanation=str(correction.explanation),
        natural_version=natural_version,
        retry_prompt=retry_prompt,
        tags=correction.tags,
        severity=severity,
        feedback_json=feedback_json or None,
        created_at=correction.created_at,
    )


def get_correction_json_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "original": {"type": "string"},
            "corrected": {"type": "string"},
            "explanation": {"type": "string"},
            "natural_version": {"type": "string"},
            "retry_prompt": {"type": "string"},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
            },
            "severity": {
                "type": "string",
                "enum": ["none", "low", "medium", "high"],
            },
        },
        "required": [
            "original",
            "corrected",
            "explanation",
            "natural_version",
            "retry_prompt",
            "tags",
            "severity",
        ],
        "additionalProperties": False,
    }


def get_translation_evaluation_json_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "score": {"type": "integer", "minimum": 0, "maximum": 100},
            "status": {"type": "string", "enum": ["correct", "almost", "needs_practice"]},
            "best_answer": {"type": "string"},
            "mistake": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "has_error": {"type": "boolean"},
                    "wrong_part": {"type": "string"},
                    "correction": {"type": "string"},
                    "explanation": {"type": "string"},
                },
                "required": ["has_error", "wrong_part", "correction", "explanation"],
            },
            "pattern": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "structure": {"type": "string"},
                    "usage_note": {"type": "string"},
                    "translation_tip": {"type": "string"},
                    "examples": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "native": {"type": "string"},
                                "english": {"type": "string"},
                            },
                            "required": ["native", "english"],
                        },
                    },
                },
                "required": ["name", "structure", "usage_note", "translation_tip", "examples"],
            },
            "meaning_mapping": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "native": {"type": "string"},
                        "english": {"type": "string"},
                        "note": {"type": ["string", "null"]},
                    },
                    "required": ["native", "english", "note"],
                },
            },
            "natural_variations": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": [
            "score",
            "status",
            "best_answer",
            "mistake",
            "pattern",
            "meaning_mapping",
            "natural_variations",
        ],
    }
