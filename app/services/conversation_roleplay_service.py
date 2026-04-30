from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation_message import ConversationMessage
from app.models.conversation_session import ConversationSession
from app.models.user import User
from app.prompts.conversation_roleplay_prompt import build_conversation_roleplay_evaluation_prompt
from app.schemas.conversation import (
    ConversationFeedbackLevel,
    ConversationReplyRequest,
    ConversationReplyResponse,
    ConversationScenario,
    ConversationStartResponse,
    ConversationSummaryResponse,
)
from app.services.ai_provider import (
    AIConversationTurn,
    AIProviderConfigurationError,
    AIProviderParseError,
    AIProviderResponseError,
    generate_structured_json,
)
from app.services.user_learning_profile_service import (
    get_or_create_user_learning_profile,
    learning_area_label,
    normalize_learning_area,
    update_user_learning_profile_after_conversation_turn,
)

_DEFAULT_MAX_TURNS = 5
_ALLOWED_LEVELS = {"beginner", "intermediate", "advanced"}


class ConversationReplyAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    score: int = Field(ge=0, le=100)
    feedback_level: ConversationFeedbackLevel
    corrected_sentence: str = Field(min_length=1)
    natural_sentence: str = Field(min_length=1)
    mistakes: list[dict[str, str]] = Field(default_factory=list)
    encouragement: str = Field(min_length=1)
    ai_reply: str = Field(min_length=1)
    confidence_score: int = Field(ge=0, le=100)
    best_area: str = Field(min_length=1)
    weak_area: str = Field(min_length=1)
    tip: str = Field(min_length=1)


class ScenarioConfig(BaseModel):
    title: str
    description: str
    goal: str
    opener_beginner: str
    opener_intermediate: str
    opener_advanced: str


_SCENARIOS: dict[str, ScenarioConfig] = {
    "job_interview": ScenarioConfig(
        title="Job Interview Practice",
        description="Practice clear and confident interview answers.",
        goal="Practice clear and confident interview answers.",
        opener_beginner="Hello, welcome to the interview. Please tell me about yourself.",
        opener_intermediate="Hello, thanks for joining today. Could you introduce yourself and tell me a little about your background?",
        opener_advanced="Welcome. To begin, could you give me a concise introduction and highlight the experience most relevant to this role?",
    ),
    "client_meeting": ScenarioConfig(
        title="Client Meeting Practice",
        description="Practice professional English for client conversations.",
        goal="Practice professional English for client conversations.",
        opener_beginner="Hello. Thank you for meeting with us. Can you tell me what you need from this project?",
        opener_intermediate="Hi, thanks for meeting today. Could you walk me through what the client needs most from this project?",
        opener_advanced="Good to meet you. Could you outline the client priorities and the outcome you want from this meeting?",
    ),
    "daily_conversation": ScenarioConfig(
        title="Daily Conversation Practice",
        description="Practice simple natural English for everyday life.",
        goal="Practice simple natural English for everyday life.",
        opener_beginner="Hi. How was your day today?",
        opener_intermediate="Hi there. How has your day been so far?",
        opener_advanced="Hi. What has your day been like, and what stood out most?",
    ),
    "ordering_food": ScenarioConfig(
        title="Ordering Food Practice",
        description="Practice ordering food politely and clearly.",
        goal="Practice ordering food politely and clearly.",
        opener_beginner="Hello. What would you like to order today?",
        opener_intermediate="Hi, welcome. What would you like to order, and would you like anything to drink?",
        opener_advanced="Good evening. What would you like to order today, and do you have any preferences or changes for the meal?",
    ),
    "travel_airport": ScenarioConfig(
        title="Travel / Airport Practice",
        description="Practice useful airport and travel conversations.",
        goal="Practice useful airport and travel conversations.",
        opener_beginner="Hello. Where are you traveling today?",
        opener_intermediate="Hello. Where are you flying today, and do you have any bags to check in?",
        opener_advanced="Good morning. Could you tell me where you're traveling today and whether you need any help with check-in?",
    ),
    "introduce_yourself": ScenarioConfig(
        title="Introduce Yourself Practice",
        description="Practice introducing yourself naturally and clearly.",
        goal="Practice introducing yourself naturally and clearly.",
        opener_beginner="Hi. Please introduce yourself in a few simple sentences.",
        opener_intermediate="Hi. Could you introduce yourself and tell me a little about what you do?",
        opener_advanced="Hi. Please introduce yourself naturally and include the parts you would want someone new to remember.",
    ),
    "confidence_practice": ScenarioConfig(
        title="Confidence Practice",
        description="Practice speaking with more confidence and complete sentences.",
        goal="Practice speaking with more confidence and complete sentences.",
        opener_beginner="Hi. Tell me one thing you did well this week.",
        opener_intermediate="Hi. Tell me about one recent situation where you handled something well.",
        opener_advanced="Hi. Tell me about a recent moment that made you feel confident, and explain why it mattered to you.",
    ),
}


def _personalized_goal(base_goal: str, learning_goal: str | None) -> str:
    normalized_goal = (learning_goal or "").strip().lower()
    if not normalized_goal:
        return base_goal
    readable_goal = normalized_goal.replace("_", " ")
    return f"{base_goal} This session also supports your {readable_goal} goal."


def _normalize_level(level: str | None) -> str:
    normalized = (level or "").strip().lower()
    if normalized == "not_sure":
        return "beginner"
    return normalized if normalized in _ALLOWED_LEVELS else "beginner"


def _get_scenario(scenario: str) -> ScenarioConfig:
    config = _SCENARIOS.get(scenario)
    if config is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported conversation scenario")
    return config


def _scenario_opener(config: ScenarioConfig, level: str) -> str:
    return {
        "beginner": config.opener_beginner,
        "intermediate": config.opener_intermediate,
        "advanced": config.opener_advanced,
    }.get(level, config.opener_beginner)


def _feedback_level(score: int) -> str:
    if score >= 88:
        return "excellent"
    if score >= 70:
        return "good"
    return "needs_improvement"


def _fallback_analysis(*, opener: str, level: str) -> ConversationReplyAnalysis:
    return ConversationReplyAnalysis(
        score=68,
        feedback_level="needs_improvement",
        corrected_sentence=opener,
        natural_sentence=opener,
        mistakes=[
            {
                "type": "grammar",
                "issue": "The reply needs clearer grammar.",
                "fix": "Use one complete sentence with a clear subject and verb.",
                "reason": "Complete sentences make your English easier to understand.",
            }
        ],
        encouragement="Good start. Try to answer in one full sentence.",
        ai_reply="Thanks. Can you answer again with one complete sentence?",
        confidence_score=62,
        best_area="confidence",
        weak_area="grammar",
        tip="Focus on complete sentences with a clear verb.",
    )


def _conversation_json_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "score": {"type": "integer", "minimum": 0, "maximum": 100},
            "feedback_level": {
                "type": "string",
                "enum": ["good", "needs_improvement", "excellent"],
            },
            "corrected_sentence": {"type": "string"},
            "natural_sentence": {"type": "string"},
            "mistakes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["grammar", "vocabulary", "sentence_structure", "spelling", "tense"],
                        },
                        "issue": {"type": "string"},
                        "fix": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["type", "issue", "fix", "reason"],
                },
            },
            "encouragement": {"type": "string"},
            "ai_reply": {"type": "string"},
            "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "best_area": {"type": "string"},
            "weak_area": {"type": "string"},
            "tip": {"type": "string"},
        },
        "required": [
            "score",
            "feedback_level",
            "corrected_sentence",
            "natural_sentence",
            "mistakes",
            "encouragement",
            "ai_reply",
            "confidence_score",
            "best_area",
            "weak_area",
            "tip",
        ],
    }


async def _create_conversation_message(
    session: AsyncSession,
    *,
    conversation_session: ConversationSession,
    role: str,
    message: str,
    score: int | None = None,
    corrected_sentence: str | None = None,
    natural_sentence: str | None = None,
    feedback_json: dict | None = None,
) -> ConversationMessage:
    item = ConversationMessage(
        session_id=conversation_session.id,
        role=role,
        message=message,
        score=score,
        corrected_sentence=corrected_sentence,
        natural_sentence=natural_sentence,
        feedback_json=feedback_json,
    )
    session.add(item)
    await session.flush()
    return item


async def _get_user_conversation_session(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    include_messages: bool = False,
) -> ConversationSession:
    options = [selectinload(ConversationSession.user)]
    if include_messages:
        options.append(selectinload(ConversationSession.messages))
    result = await session.execute(
        select(ConversationSession)
        .options(*options)
        .where(ConversationSession.id == session_id, ConversationSession.user_id == user_id)
    )
    conversation_session = result.scalar_one_or_none()
    if conversation_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found")
    return conversation_session


async def start_conversation_session(
    session: AsyncSession,
    *,
    user: User,
    scenario: ConversationScenario,
) -> ConversationStartResponse:
    config = _get_scenario(scenario)
    learning_profile = await get_or_create_user_learning_profile(
        session,
        user_id=user.id,
        preferred_level=user.english_level,
    )
    level = _normalize_level(learning_profile.current_difficulty or user.english_level)
    opener = _scenario_opener(config, level)

    conversation_session = ConversationSession(
        user_id=user.id,
        scenario=scenario,
        level=level,
        status="active",
        max_turns=_DEFAULT_MAX_TURNS,
        current_turn=0,
        started_at=datetime.now(timezone.utc),
    )
    session.add(conversation_session)
    await session.flush()
    await _create_conversation_message(
        session,
        conversation_session=conversation_session,
        role="ai",
        message=opener,
    )
    await session.commit()

    return ConversationStartResponse(
        session_id=conversation_session.id,
        scenario=scenario,
        level=level,
        title=config.title,
        ai_message=opener,
        goal=_personalized_goal(config.goal, user.learning_goal),
        max_turns=conversation_session.max_turns,
    )


def _serialize_conversation_history(messages: list[ConversationMessage]) -> list[tuple[str, str]]:
    return [(message.role, message.message) for message in messages]


async def _build_conversation_summary(
    session: AsyncSession,
    *,
    conversation_session: ConversationSession,
    latest_analysis: ConversationReplyAnalysis,
) -> ConversationSummaryResponse:
    result = await session.execute(
        select(func.avg(ConversationMessage.score))
        .where(
            ConversationMessage.session_id == conversation_session.id,
            ConversationMessage.role == "user",
            ConversationMessage.score.is_not(None),
        )
    )
    average_score = int(round(float(result.scalar() or latest_analysis.score)))
    return ConversationSummaryResponse(
        average_score=average_score,
        best_area=latest_analysis.best_area,
        weak_area=latest_analysis.weak_area,
        tip=latest_analysis.tip,
    )


async def reply_in_conversation_session(
    session: AsyncSession,
    *,
    user: User,
    payload: ConversationReplyRequest,
) -> ConversationReplyResponse:
    conversation_session = await _get_user_conversation_session(
        session,
        user_id=user.id,
        session_id=payload.session_id,
        include_messages=True,
    )
    if conversation_session.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conversation session is not active")

    config = _get_scenario(conversation_session.scenario)
    learning_profile = await get_or_create_user_learning_profile(
        session,
        user_id=user.id,
        preferred_level=user.english_level,
    )
    level = _normalize_level(conversation_session.level)
    next_turn_number = conversation_session.current_turn + 1

    history = _serialize_conversation_history(conversation_session.messages or [])
    system_prompt = build_conversation_roleplay_evaluation_prompt(
        scenario_title=config.title,
        scenario_goal=config.goal,
        level=level,
        turn_number=next_turn_number,
        max_turns=conversation_session.max_turns,
        conversation_history=history,
        recommended_focus_area=normalize_learning_area(learning_profile.recommended_focus_area),
        learning_goal=user.learning_goal,
    )

    try:
        provider_result = await generate_structured_json(
            system_prompt=system_prompt,
            conversation=[AIConversationTurn(role="user", content=payload.user_message)],
            schema_name="conversation_roleplay_turn",
            json_schema=_conversation_json_schema(),
        )
        analysis = ConversationReplyAnalysis.model_validate(provider_result.data)
    except (
        AIProviderConfigurationError,
        AIProviderParseError,
        AIProviderResponseError,
        ValidationError,
    ):
        analysis = _fallback_analysis(
            opener=config.opener_beginner,
            level=level,
        )

    await _create_conversation_message(
        session,
        conversation_session=conversation_session,
        role="user",
        message=payload.user_message,
        score=analysis.score,
        corrected_sentence=analysis.corrected_sentence,
        natural_sentence=analysis.natural_sentence,
        feedback_json={
            "feedback_level": analysis.feedback_level,
            "mistakes": analysis.mistakes,
            "encouragement": analysis.encouragement,
            "confidence_score": analysis.confidence_score,
            "best_area": analysis.best_area,
            "weak_area": analysis.weak_area,
            "tip": analysis.tip,
        },
    )

    remaining_turns = max(conversation_session.max_turns - next_turn_number, 0)
    session_completed = remaining_turns == 0

    await _create_conversation_message(
        session,
        conversation_session=conversation_session,
        role="ai",
        message=analysis.ai_reply,
        feedback_json={"scenario": conversation_session.scenario},
    )

    conversation_session.current_turn = next_turn_number
    if session_completed:
        conversation_session.status = "completed"
        conversation_session.completed_at = datetime.now(timezone.utc)

    await session.flush()
    await update_user_learning_profile_after_conversation_turn(
        session,
        user=user,
        conversation_session=conversation_session,
        score=analysis.score,
        confidence_score=analysis.confidence_score,
        mistakes=analysis.mistakes,
        corrected_sentence=analysis.corrected_sentence,
        natural_sentence=analysis.natural_sentence,
        learner_message=payload.user_message,
        ai_prompt=history[-1][1] if history else config.opener_beginner,
        encouragement=analysis.encouragement,
        tip=analysis.tip,
    )

    summary = (
        await _build_conversation_summary(
            session,
            conversation_session=conversation_session,
            latest_analysis=analysis,
        )
        if session_completed
        else None
    )

    return ConversationReplyResponse(
        turn_number=next_turn_number,
        score=analysis.score,
        feedback_level=analysis.feedback_level,  # type: ignore[arg-type]
        corrected_sentence=analysis.corrected_sentence,
        natural_sentence=analysis.natural_sentence,
        mistakes=analysis.mistakes,  # type: ignore[arg-type]
        encouragement=analysis.encouragement,
        ai_reply=analysis.ai_reply,
        session_completed=session_completed,
        remaining_turns=remaining_turns,
        summary=summary,
    )
