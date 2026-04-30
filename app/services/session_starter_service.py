from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.practice_message import PracticeMessage
from app.models.practice_session import PracticeSession
from app.models.user_learning_summary import UserLearningSummary
from app.prompts.opener_prompt import build_opener_system_prompt
from app.services.ai_provider import (
    AIConversationTurn,
    AIProviderConfigurationError,
    AIProviderParseError,
    AIProviderResponseError,
    AIProviderStructuredResult,
    generate_structured_json,
)
from app.services.recommendation_service import build_focus_recommendation


@dataclass(slots=True)
class SessionStarterDraft:
    opener: str
    quick_replies: list[str]
    metadata_json: dict | None = None
    provider: str | None = None
    model: str | None = None
    response_id: str | None = None
    source: str = "fallback"


def _sanitize_quick_replies(values: list[str] | None) -> list[str]:
    if not values:
        return []
    replies: list[str] = []
    for value in values:
        cleaned = " ".join(value.split()).strip()
        if not cleaned:
            continue
        if len(cleaned) > 80:
            cleaned = cleaned[:80].rstrip(" ,.;:!?")
        if cleaned not in replies:
            replies.append(cleaned)
        if len(replies) == 4:
            break
    return replies


def _topic_key(practice_session: PracticeSession) -> str | None:
    topic = practice_session.topic
    if topic is None:
        return None
    slug = (topic.slug or "").lower()
    if slug:
        return slug
    return (topic.title or "").strip().lower().replace(" ", "-") or None


def _build_fallback_quick_replies(
    *,
    practice_session: PracticeSession,
    learning_summary: UserLearningSummary | None,
) -> list[str]:
    topic_key = _topic_key(practice_session)
    recommendation = build_focus_recommendation(
        learning_summary.top_weak_areas if learning_summary is not None else []
    )

    if practice_session.mode == "roleplay":
        return ["Hello.", "Can you help me?", "I need some information."]
    if practice_session.mode == "speaking_practice":
        if recommendation.focus_title == "Past tense practice":
            return ["Yesterday I stayed home.", "I went to work.", "I visited my friend."]
        return ["In the morning I...", "Usually I...", "Today I want to..."]
    if topic_key in {"travel", "introduce-yourself", "daily-life", "job-interview", "office-conversation", "ordering-food", "storytelling", "debate"}:
        mapping = {
            "travel": ["Yes, I have.", "No, not yet.", "I visited another city."],
            "introduce-yourself": ["My name is Rahul.", "I live in India.", "I want to improve my English."],
            "daily-life": ["I wake up early.", "I make breakfast.", "I go to work."],
            "job-interview": ["My name is Rahul.", "I am a software developer.", "I enjoy solving problems."],
            "office-conversation": ["I work with my team.", "I have a meeting today.", "I am finishing a task."],
            "ordering-food": ["I would like tea.", "Can I have a sandwich?", "I want something spicy."],
            "storytelling": ["One day, I...", "It happened last week.", "I felt very happy."],
            "debate": ["I agree.", "I think both sides matter.", "In my opinion, it depends."],
        }
        return mapping[topic_key]

    if recommendation.focus_title == "Longer answers":
        return ["I usually start with...", "One thing I do is...", "I also like to..."]
    return ["Yes, a little.", "Not yet.", "I want to practice more."]


def build_fallback_session_starter(
    *,
    practice_session: PracticeSession,
    learning_summary: UserLearningSummary | None,
) -> SessionStarterDraft:
    topic = practice_session.topic
    topic_title = topic.title if topic is not None else None
    recommendation = build_focus_recommendation(
        learning_summary.top_weak_areas if learning_summary is not None else []
    )

    if practice_session.mode == "roleplay":
        opener = (
            f"Hello! Let's do a simple {topic_title.lower()} roleplay. How can I help you today?"
            if topic_title
            else "Hello! Let's do a simple roleplay. How can I help you today?"
        )
    elif practice_session.mode == "speaking_practice":
        if recommendation.focus_title == "Past tense practice":
            opener = "Hi! Let's practice speaking in English. What did you do yesterday?"
        else:
            opener = "Hi! Let's practice speaking English. What do you usually do in the morning?"
    elif topic_title:
        opener = f"Hi! Let's practice {topic_title.lower()} English today. What would you like to say first?"
    else:
        opener = "Hi! I'm ready to practice English with you. Tell me a little about yourself."

    return SessionStarterDraft(
        opener=opener,
        quick_replies=_build_fallback_quick_replies(
            practice_session=practice_session,
            learning_summary=learning_summary,
        ),
        source="fallback",
    )


def _schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "opener": {"type": "string"},
            "quick_replies": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 2,
                "maxItems": 4,
            },
        },
        "required": ["opener", "quick_replies"],
    }


def _parse_starter_result(result: AIProviderStructuredResult) -> SessionStarterDraft | None:
    opener = " ".join(str(result.data.get("opener", "")).split()).strip()
    if not opener:
        return None
    quick_replies = _sanitize_quick_replies(result.data.get("quick_replies"))
    if len(quick_replies) < 2:
        return None
    return SessionStarterDraft(
        opener=opener,
        quick_replies=quick_replies,
        provider=result.provider,
        model=result.model,
        response_id=result.response_id,
        source="ai",
    )


async def generate_session_starter(
    session: AsyncSession,
    *,
    practice_session: PracticeSession,
    learning_summary: UserLearningSummary | None,
) -> SessionStarterDraft:
    system_prompt = build_opener_system_prompt(
        user=practice_session.user,
        learning_profile=practice_session.user.learning_profile,
        practice_session=practice_session,
        learning_summary=learning_summary,
    )

    try:
        provider_result = await generate_structured_json(
            system_prompt=system_prompt,
            conversation=[],
            schema_name="practice_session_starter",
            json_schema=_schema(),
        )
        starter = _parse_starter_result(provider_result)
        if starter is not None:
            return starter
    except (AIProviderConfigurationError, AIProviderParseError, AIProviderResponseError):
        pass

    return build_fallback_session_starter(
        practice_session=practice_session,
        learning_summary=learning_summary,
    )
