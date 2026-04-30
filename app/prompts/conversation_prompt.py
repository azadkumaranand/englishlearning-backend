from __future__ import annotations

from collections.abc import Sequence

from app.models.learning_profile import LearningProfile
from app.models.practice_message import PracticeMessage
from app.models.practice_session import PracticeSession
from app.models.user_learning_summary import UserLearningSummary
from app.models.user import User
from app.services.recommendation_service import build_personalization_prompt_hints


def build_conversation_system_prompt(
    *,
    user: User,
    learning_profile: LearningProfile | None,
    practice_session: PracticeSession,
    history: Sequence[PracticeMessage],
    learning_summary: UserLearningSummary | None = None,
) -> str:
    level = user.english_level or "unknown"
    goal = learning_profile.goal if learning_profile else None
    focus_areas = learning_profile.focus_areas if learning_profile else None
    topic = practice_session.topic
    top_weak_areas = learning_summary.top_weak_areas if learning_summary else []
    recommended_focus = learning_summary.last_recommended_focus if learning_summary else None
    latest_user_message = next((message for message in reversed(history) if message.role == "user"), None)
    latest_user_metadata = (
        latest_user_message.metadata_json
        if latest_user_message is not None and isinstance(latest_user_message.metadata_json, dict)
        else {}
    )
    latest_input_mode = latest_user_metadata.get("input_mode")
    latest_voice_language = latest_user_metadata.get("language")

    level_guidance = {
        "beginner": "When replying in English, use simple vocabulary, short sentences, and gentle follow-up questions.",
        "intermediate": "When replying in English, use natural everyday English with moderate vocabulary and clear follow-up questions.",
        "advanced": "When replying in English, use richer, more natural vocabulary and explore ideas in more depth without sounding formal.",
    }.get(level.lower(), "When replying in English, match the learner's level with clear, natural, supportive wording.")

    mode_guidance = {
        "free_chat": "Keep the exchange open-ended and conversational. The learner may write or speak in any language.",
        "guided_topic": "Keep the conversation centered on the selected topic.",
        "roleplay": "Stay in character only when the user's message suggests a scenario, and keep the roleplay realistic.",
        "speaking_practice": "Prefer spoken-style replies that are concise and easy to say out loud.",
    }.get(practice_session.mode, "Keep the conversation natural and useful for English practice.")

    prompt_sections = [
        "You are a friendly conversation partner for a mobile learning app.",
        "Keep the conversation flowing with supportive, natural, short-to-medium replies.",
        "Do not give grammar corrections, lesson breakdowns, or teaching analysis unless the user clearly asks for them.",
        "Answer the user first, then ask at most one relevant follow-up question when it helps continue the conversation.",
        "Avoid sounding robotic, overly enthusiastic, or like a textbook.",
        level_guidance,
        mode_guidance,
        f"Learner English level: {level}.",
    ]

    if goal:
        prompt_sections.append(f"Learner goal: {goal}.")
    if focus_areas:
        prompt_sections.append(f"Learner focus areas: {', '.join(focus_areas)}.")
    if topic is not None:
        prompt_sections.append(f"Session topic: {topic.title}.")
        if topic.description:
            prompt_sections.append(f"Topic description: {topic.description}.")
    if practice_session.mode == "free_chat":
        prompt_sections.extend(
            [
                "For free chat, reply in the same language as the learner's latest message unless the learner clearly asks you to switch languages.",
                "Match the learner's tone, formality, and energy. If the learner sounds casual, be casual. If the learner sounds serious, be serious.",
                "If the learner asks a direct question, answer it clearly before adding a follow-up question.",
                "If the learner used speech, make the wording easy to listen to and easy to say aloud.",
            ]
        )
        if isinstance(latest_voice_language, str) and latest_voice_language.strip():
            prompt_sections.append(
                f"The latest spoken input was transcribed as language code: {latest_voice_language.strip()}."
            )
        if latest_input_mode == "voice":
            prompt_sections.append("The latest learner message came from voice input.")
    if top_weak_areas:
        prompt_sections.append(
            f"Current weak areas to practice naturally: {', '.join(top_weak_areas)}."
        )
        prompt_sections.append(
            "Use these weak areas only as light guidance. Do not mention them directly unless the learner asks."
        )
        for hint in build_personalization_prompt_hints(top_weak_areas):
            prompt_sections.append(hint)
    if recommended_focus:
        prompt_sections.append(f"Current recommended focus: {recommended_focus}.")

    if history:
        prompt_sections.append(
            "Use the recent conversation context to stay coherent and avoid repeating yourself."
        )

    return "\n".join(prompt_sections)
