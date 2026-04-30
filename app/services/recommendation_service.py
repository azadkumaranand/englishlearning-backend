from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(slots=True)
class FocusRecommendation:
    focus_title: str
    short_reason: str
    suggested_action: str
    prompt_hint: str


_TAG_RECOMMENDATIONS: dict[str, FocusRecommendation] = {
    "tense": FocusRecommendation(
        focus_title="Tense practice",
        short_reason="You often need more control over verb tense and time references.",
        suggested_action="Practice describing yesterday, today, and tomorrow using clear verbs.",
        prompt_hint="Use everyday situations that make the learner switch between past, present, and future naturally.",
    ),
    "past_tense": FocusRecommendation(
        focus_title="Past tense practice",
        short_reason="You often make mistakes with past tense verbs.",
        suggested_action="Try describing what you did yesterday in 3 short sentences.",
        prompt_hint="Gently guide the learner toward talking about past events and recent experiences.",
    ),
    "articles": FocusRecommendation(
        focus_title="Article usage",
        short_reason="You often miss articles like a, an, and the.",
        suggested_action="Practice describing everyday objects and places using complete noun phrases.",
        prompt_hint="Use everyday nouns and places naturally so the learner practices articles in context.",
    ),
    "prepositions": FocusRecommendation(
        focus_title="Preposition practice",
        short_reason="You often make mistakes with prepositions.",
        suggested_action="Practice talking about locations, movement, and time expressions.",
        prompt_hint="Ask about places, plans, and movement so the learner uses common prepositions.",
    ),
    "grammar": FocusRecommendation(
        focus_title="Grammar practice",
        short_reason="You need a bit more consistency with common grammar patterns.",
        suggested_action="Practice short sentences with clear verbs, articles, and prepositions.",
        prompt_hint="Keep the prompt simple but make the learner use one small grammar choice correctly.",
    ),
    "sentence_structure": FocusRecommendation(
        focus_title="Sentence structure",
        short_reason="Your sentence structure needs more practice.",
        suggested_action="Answer with 2 clear sentences instead of one short phrase.",
        prompt_hint="Encourage clear complete sentences with simple follow-up questions.",
    ),
    "word_order": FocusRecommendation(
        focus_title="Word order practice",
        short_reason="Your ideas are often clear, but the English word order needs adjustment.",
        suggested_action="Practice short sentences with the subject, verb, and time phrase in natural English order.",
        prompt_hint="Use simple daily-life prompts where the learner must place time and action naturally.",
    ),
    "meaning": FocusRecommendation(
        focus_title="Meaning practice",
        short_reason="You often need more practice carrying the full meaning into English.",
        suggested_action="Pause and say the whole idea in simple English before writing the sentence.",
        prompt_hint="Use clear situations that test whether the learner expresses the full meaning, not just separate words.",
    ),
    "word_by_word_translation": FocusRecommendation(
        focus_title="Think in English practice",
        short_reason="You often translate word by word instead of expressing the full idea naturally.",
        suggested_action="First ask what the sentence means, then say that meaning in simple English.",
        prompt_hint="Use prompts that expose direct translation mistakes and reward natural English phrasing.",
    ),
    "vocabulary": FocusRecommendation(
        focus_title="Vocabulary building",
        short_reason="You could benefit from using a wider range of words.",
        suggested_action="Describe one topic with a few extra details and more precise words.",
        prompt_hint="Invite more descriptive answers and gently encourage richer wording.",
    ),
    "spelling": FocusRecommendation(
        focus_title="Spelling practice",
        short_reason="You need a little more attention to word spelling.",
        suggested_action="Slow down and rewrite short sentences carefully before sending them.",
        prompt_hint="Use short familiar words so the learner can focus on accurate spelling and clean sentence form.",
    ),
    "short_answers": FocusRecommendation(
        focus_title="Longer answers",
        short_reason="You often answer too briefly to practice fully.",
        suggested_action="Try responding in 2 or 3 connected sentences.",
        prompt_hint="Ask open-ended questions that encourage longer answers.",
    ),
}

_DEFAULT_RECOMMENDATION = FocusRecommendation(
    focus_title="General fluency practice",
    short_reason="Keep practicing clear, natural English responses.",
    suggested_action="Answer the next question in 2 complete sentences.",
    prompt_hint="Keep the learner talking with clear, open-ended questions.",
)


def build_focus_recommendation(top_weak_areas: Sequence[str] | None) -> FocusRecommendation:
    if not top_weak_areas:
        return _DEFAULT_RECOMMENDATION
    for tag in top_weak_areas:
        recommendation = _TAG_RECOMMENDATIONS.get(tag)
        if recommendation is not None:
            return recommendation
    return _DEFAULT_RECOMMENDATION


def build_personalization_prompt_hints(top_weak_areas: Sequence[str] | None) -> list[str]:
    if not top_weak_areas:
        return []
    hints: list[str] = []
    for tag in top_weak_areas[:2]:
        recommendation = _TAG_RECOMMENDATIONS.get(tag)
        if recommendation is not None:
            hints.append(recommendation.prompt_hint)
    return hints
