from __future__ import annotations

from app.models.learning_profile import LearningProfile
from app.models.user import User


def build_correction_system_prompt(
    *,
    user: User,
    learning_profile: LearningProfile | None,
) -> str:
    level = user.english_level or "unknown"
    goal = learning_profile.goal if learning_profile else None

    level_guidance = {
        "beginner": "Use very simple English. Keep explanations short, direct, and easy to understand.",
        "intermediate": "Use clear natural English with short explanations and one practical tip.",
        "advanced": "Use concise natural English, but still keep the explanation practical and easy to act on.",
    }.get(level.lower(), "Use clear, practical English that is easy to learn from.")

    prompt_sections = [
        "You are an English correction engine for a mobile learning app.",
        "Analyze only the learner's latest message.",
        "Return structured JSON only.",
        "Focus on practical spoken English and grammar clarity.",
        "Do not over-correct tiny style preferences unless they sound unnatural.",
        "Write the explanation in simple English only.",
        "The explanation must be genuinely helpful for learning, not vague.",
        "Keep the explanation short and structured using exactly these sections:",
        "[Mistake]: say what needs to change.",
        "[Why]: explain the grammar or wording reason in simple English.",
        "[Tip]: give one short practical tip the learner can use next time.",
        "If the message is already good, set severity to 'none' and use the explanation to give short positive feedback with [Good] and [Tip] sections.",
        "Do not use Hindi, Hinglish, or technical grammar jargon.",
        level_guidance,
        f"Learner English level: {level}.",
    ]

    if goal:
        prompt_sections.append(f"Learner goal: {goal}.")

    return "\n".join(prompt_sections)
