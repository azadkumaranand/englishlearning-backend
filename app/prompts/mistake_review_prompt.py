from __future__ import annotations


def build_mistake_retry_evaluation_prompt(
    *,
    focus_area: str,
    wrong_sentence: str,
    correct_sentence: str,
    explanation: str,
    retry_question: str,
) -> str:
    return "\n".join(
        [
            "You evaluate one mistake-review retry for an English learning app.",
            "The learner is retrying a sentence they got wrong before.",
            "Return JSON only.",
            "Use keys exactly: is_improved, score, correct_answer, natural_answer, feedback, remaining_issue, status.",
            "score must be an integer from 0 to 100.",
            "status must be either 'improved' or 'needs_more_practice'.",
            "Set is_improved to true only if the learner answer is good enough to mark as improved.",
            "Use simple English.",
            "Keep feedback short, supportive, and specific.",
            "remaining_issue should be null if the learner answer is improved enough.",
            "If the learner is still wrong, explain the main remaining issue in one short sentence.",
            "Accept natural wording variation when the meaning is correct and grammar is good.",
            "Focus area: " + focus_area,
            "Earlier wrong sentence: " + wrong_sentence,
            "Reference correct sentence: " + correct_sentence,
            "Earlier explanation: " + explanation,
            "Retry question: " + retry_question,
        ]
    )
