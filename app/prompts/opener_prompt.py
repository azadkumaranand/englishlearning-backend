from __future__ import annotations

from app.models.learning_profile import LearningProfile
from app.models.practice_session import PracticeSession
from app.models.user_learning_summary import UserLearningSummary
from app.models.user import User
from app.services.recommendation_service import build_personalization_prompt_hints


def build_opener_system_prompt(
    *,
    user: User,
    learning_profile: LearningProfile | None,
    practice_session: PracticeSession,
    learning_summary: UserLearningSummary | None = None,
) -> str:
    level = (user.english_level or "unknown").lower()
    goal = learning_profile.goal if learning_profile else None
    topic = practice_session.topic
    top_weak_areas = learning_summary.top_weak_areas if learning_summary else []
    recommended_focus = learning_summary.last_recommended_focus if learning_summary else None

    level_guidance = {
        "beginner": "Use very simple English, short sentences, and an easy first question.",
        "intermediate": "Use natural everyday English and one clear question that is easy to answer.",
        "advanced": "Use natural, engaging English with one thoughtful but low-pressure opening question.",
    }.get(level, "Use clear, encouraging English and one easy opening question.")

    mode_guidance = {
        "free_chat": "Open with a warm everyday conversation starter.",
        "guided_topic": "Open with a warm topic-focused question.",
        "roleplay": "Open in a light roleplay voice that makes the scenario obvious immediately.",
        "speaking_practice": "Open with a short prompt that encourages a spoken answer in 1 to 3 sentences.",
    }.get(practice_session.mode, "Open with a clear and friendly practice question.")

    sections = [
        "You create the first assistant message for a mobile English learning chat session.",
        "Your goal is to remove hesitation and help the learner answer immediately.",
        "Write one welcoming opener that feels natural, low-pressure, and easy to answer.",
        "Ask exactly one clear question.",
        "Keep the opener short. Avoid explanations, corrections, multiple questions, bullet lists, or teaching language.",
        "Then provide 2 to 4 short quick replies the learner can tap.",
        "Quick replies must be simple, relevant to the opener, and easy to say aloud.",
        "Do not mention grammar mistakes or correction feedback.",
        level_guidance,
        mode_guidance,
        f"Learner level: {user.english_level or 'unknown'}.",
    ]

    if goal:
        sections.append(f"Learner goal: {goal}.")
    if topic is not None:
        sections.append(f"Session topic: {topic.title}.")
        if topic.description:
            sections.append(f"Topic description: {topic.description}.")
        if topic.category:
            sections.append(f"Topic category: {topic.category}.")
    if top_weak_areas:
        sections.append(f"Top weak areas: {', '.join(top_weak_areas)}.")
        sections.append(
            "Use weak areas only as subtle guidance for the question. Do not mention them directly."
        )
        sections.extend(build_personalization_prompt_hints(top_weak_areas))
    if recommended_focus:
        sections.append(f"Current recommended focus: {recommended_focus}.")

    sections.append(
        "Return JSON with keys `opener` and `quick_replies` only. `quick_replies` must contain 2 to 4 strings."
    )
    return "\n".join(sections)
