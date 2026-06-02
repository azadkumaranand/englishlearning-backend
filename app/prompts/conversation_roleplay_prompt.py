from __future__ import annotations

_SCENARIO_TOPIC_SEQUENCES: dict[str, list[str]] = {
    "job_interview": [
        "introduction",
        "background",
        "recent experience",
        "strengths",
        "challenge or example",
    ],
    "client_meeting": [
        "client goal",
        "requirements",
        "constraints or timeline",
        "proposal or solution",
        "next steps",
    ],
    "daily_conversation": [
        "day summary",
        "specific activity",
        "feeling or opinion",
        "detail or reason",
        "tomorrow or next plan",
    ],
    "ordering_food": [
        "main order",
        "drink or side",
        "preference or customization",
        "follow-up question",
        "closing the order",
    ],
    "travel_airport": [
        "destination",
        "flight details",
        "bags or documents",
        "travel need or issue",
        "next airport step",
    ],
    "introduce_yourself": [
        "basic introduction",
        "work or study",
        "interests",
        "personal detail",
        "future goal",
    ],
    "confidence_practice": [
        "recent win",
        "what made it work",
        "challenge handled",
        "lesson learned",
        "next confidence step",
    ],
}


def scenario_topic_sequence(scenario_key: str) -> list[str]:
    return list(_SCENARIO_TOPIC_SEQUENCES.get(scenario_key, ["introduction", "detail", "example", "follow-up"]))


def build_conversation_roleplay_evaluation_prompt(
    *,
    scenario_key: str,
    scenario_title: str,
    scenario_goal: str,
    level: str,
    turn_number: int,
    max_turns: int,
    conversation_history: list[tuple[str, str]],
    topic_sequence: list[str],
    completed_goals: list[str],
    covered_topics: list[str],
    recent_ai_questions: list[str],
    recommended_focus_area: str | None,
    learning_goal: str | None,
) -> str:
    history_lines = [f"{role.upper()}: {message}" for role, message in conversation_history[-8:]]

    sections = [
        "You are a friendly English tutor and roleplay partner inside a speaking practice app.",
        "Stay inside the selected scenario.",
        "Ask one short natural question at a time.",
        "Keep replies short and conversational.",
        "Drive the conversation forward. Do not stay on the same idea for multiple turns unless the learner did not answer it.",
        "Do not repeat the same question intent, wording, or information request from recent turns.",
        "Each new ai_reply should either deepen the learner answer once or move to the next topic in the scenario flow.",
        "If the learner gave a short answer, ask for one useful extra detail. After that, move forward.",
        "If the learner gave a strong answer, acknowledge it briefly and move to the next topic.",
        "On the final turn, wrap up naturally instead of opening a brand-new topic.",
        "Return JSON only.",
        "Use keys exactly: score, feedback_level, corrected_sentence, natural_sentence, mistakes, encouragement, ai_reply, confidence_score, best_area, weak_area, tip, conversation_stage, next_question_goal, covered_topics, should_wrap_up.",
        "feedback_level must be one of: good, needs_improvement, excellent.",
        "score and confidence_score must be integers from 0 to 100.",
        "mistakes must be an array of objects with keys: type, issue, fix, reason.",
        "Mistake type must be one of: grammar, vocabulary, sentence_structure, spelling, tense.",
        "If the learner answer is strong, keep mistakes empty.",
        "Correct politely and encourage the learner.",
        "Do not output markdown.",
        "conversation_stage must be one of: opener, warmup, deepening, situational, wrap_up.",
        "next_question_goal must be a short phrase that describes the exact next topic or intent.",
        "covered_topics must be a short list of topic phrases already covered so far, including the current turn if appropriate.",
        "should_wrap_up must be true only when you are naturally closing the final turn.",
        "Beginner learners need simple English and short corrections.",
        "Intermediate learners need natural conversation and clear feedback.",
        "Advanced learners need professional, fluent roleplay and precise corrections.",
        f"Scenario key: {scenario_key}.",
        f"Scenario: {scenario_title}.",
        f"Scenario goal: {scenario_goal}.",
        f"Learner level: {level}.",
        f"Turn number: {turn_number} of {max_turns}.",
        f"Recommended scenario flow: {', '.join(topic_sequence)}.",
    ]

    if learning_goal:
        sections.append(f"Learner goal: {learning_goal}.")
    if recommended_focus_area:
        sections.append(f"Current recommended focus area: {recommended_focus_area}.")
    if completed_goals:
        sections.append(f"Goals already covered: {', '.join(completed_goals[-5:])}.")
    if covered_topics:
        sections.append(f"Topics already discussed: {', '.join(covered_topics[-6:])}.")
    if recent_ai_questions:
        sections.append("Avoid repeating these recent coach prompts:")
        sections.extend(f"- {question}" for question in recent_ai_questions[-3:])
    if history_lines:
        sections.append("Conversation so far:")
        sections.extend(history_lines)

    return "\n".join(sections)
