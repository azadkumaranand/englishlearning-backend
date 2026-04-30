from __future__ import annotations


def build_conversation_roleplay_evaluation_prompt(
    *,
    scenario_title: str,
    scenario_goal: str,
    level: str,
    turn_number: int,
    max_turns: int,
    conversation_history: list[tuple[str, str]],
    recommended_focus_area: str | None,
    learning_goal: str | None,
) -> str:
    history_lines = [f"{role.upper()}: {message}" for role, message in conversation_history[-8:]]

    sections = [
        "You are a friendly English tutor and roleplay partner inside a speaking practice app.",
        "Stay inside the selected scenario.",
        "Ask one short natural question at a time.",
        "Keep replies short and conversational.",
        "Return JSON only.",
        "Use keys exactly: score, feedback_level, corrected_sentence, natural_sentence, mistakes, encouragement, ai_reply, confidence_score, best_area, weak_area, tip.",
        "feedback_level must be one of: good, needs_improvement, excellent.",
        "score and confidence_score must be integers from 0 to 100.",
        "mistakes must be an array of objects with keys: type, issue, fix, reason.",
        "Mistake type must be one of: grammar, vocabulary, sentence_structure, spelling, tense.",
        "If the learner answer is strong, keep mistakes empty.",
        "Correct politely and encourage the learner.",
        "Do not output markdown.",
        "Beginner learners need simple English and short corrections.",
        "Intermediate learners need natural conversation and clear feedback.",
        "Advanced learners need professional, fluent roleplay and precise corrections.",
        f"Scenario: {scenario_title}.",
        f"Scenario goal: {scenario_goal}.",
        f"Learner level: {level}.",
        f"Turn number: {turn_number} of {max_turns}.",
    ]

    if learning_goal:
        sections.append(f"Learner goal: {learning_goal}.")
    if recommended_focus_area:
        sections.append(f"Current recommended focus area: {recommended_focus_area}.")
    if history_lines:
        sections.append("Conversation so far:")
        sections.extend(history_lines)

    return "\n".join(sections)
