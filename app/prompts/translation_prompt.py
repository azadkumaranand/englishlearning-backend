from __future__ import annotations

from app.services.recommendation_service import build_focus_recommendation


def build_translation_starter_prompt(
    *,
    english_level: str | None,
    goal: str | None,
    topic_title: str | None,
    topic_description: str | None,
    top_weak_areas: list[str] | None = None,
    recommended_focus_area: str | None = None,
    repeated_mistakes: list[dict] | None = None,
    recent_source_sentences: list[str] | None = None,
    total_completed_translations: int = 0,
) -> str:
    level = (english_level or "unknown").lower()
    recommendation = build_focus_recommendation(
        [recommended_focus_area, *(top_weak_areas or [])] if recommended_focus_area else (top_weak_areas or [])
    )

    level_guidance = {
        "beginner": "Keep the source sentence short and easy. Target simple everyday English.",
        "intermediate": "Use a practical sentence with one small grammar challenge.",
        "advanced": "Use natural everyday language with a slightly richer sentence.",
    }.get(level, "Match the sentence difficulty to the learner's level.")

    sections = [
        "You create one translation-practice prompt for an English learning app.",
        "The learner will translate a short sentence into English.",
        "Return JSON only with keys: source_sentence, reference_translation, assistant_prompt.",
        "source_sentence should be a simple Hindi sentence written in natural everyday Hindi using Devanagari script.",
        "Do not use Roman Hindi, transliteration, or Hinglish for source_sentence.",
        "reference_translation should be natural English.",
        "assistant_prompt should be one short English instruction that asks the learner to translate the sentence.",
        "assistant_prompt must not include the Hindi sentence itself.",
        "Keep the task focused on one likely weak area without naming the weak area directly.",
        level_guidance,
        f"Learner level: {english_level or 'unknown'}.",
        f"Completed translation count so far: {total_completed_translations}.",
        f"Current practice focus: {recommendation.focus_title}.",
        f"Suggested action: {recommendation.suggested_action}.",
    ]
    if recommended_focus_area:
        sections.append(f"Recommended focus area tag: {recommended_focus_area}.")
    if repeated_mistakes:
        formatted_examples = []
        for item in repeated_mistakes[:2]:
            wrong = str(item.get("wrong", "")).strip()
            correct = str(item.get("correct", "")).strip()
            area = str(item.get("type", "")).strip()
            if wrong and correct:
                formatted_examples.append(f"{area}: '{wrong}' -> '{correct}'")
        if formatted_examples:
            sections.append(
                "Avoid repeating these recent mistake patterns: " + " | ".join(formatted_examples) + "."
            )
    if total_completed_translations >= 6:
        sections.append(
            "Avoid very basic self-introduction prompts unless they are specifically needed for the learner."
        )
    if total_completed_translations >= 12:
        sections.append(
            "Prefer more natural multi-part daily-life sentences over beginner one-clause prompts."
        )

    if goal:
        sections.append(f"Learner goal: {goal}.")
    if topic_title:
        sections.append(f"Topic: {topic_title}.")
        if topic_description:
            sections.append(f"Topic description: {topic_description}.")
    if recent_source_sentences:
        sections.append(
            "Do not reuse these recent source sentences: "
            + " | ".join(recent_source_sentences[:5])
            + "."
        )

    return "\n".join(sections)


def build_translation_evaluation_prompt(
    *,
    english_level: str | None,
    goal: str | None,
    source_sentence: str,
    reference_translation: str,
) -> str:
    level = english_level or "unknown"

    prompt_sections = [
        "You are an expert English tutor for Hindi or native-language learners.",
        "Your job is not just to correct the sentence. Your job is to teach clearly and simply.",
        "You must identify the exact grammar pattern used, explain the mistake precisely, show the correct structure, and map the native sentence to English meaning.",
        "Keep explanations short and high value.",
        "Avoid unnecessary sections, repetition, textbook explanations, and generic phrases like 'does not match meaning', 'sentence correction', or 'express meaning clearly'.",
        "Return strict JSON only.",
        "Use exact pattern names such as Simple Present, Present Continuous, Present Perfect, Present Perfect Continuous, Simple Past, Past Continuous, Past Perfect, Future Simple, Modal structure, Be verb + adjective, There is / There are, Have to / Need to, Used to, Going to future.",
        "Pattern names must be specific, for example 'Past Simple (state using was/were)' or 'Modal structure (have to + base verb)'.",
        "Structure must be usable, for example 'Subject + was/were + adjective + to + place + time'.",
        "If the structure has alternatives like was/were, is/am/are, has/have, do/does, or had, explain clearly which option is used with which subject or situation.",
        "Meaning mapping must reflect Hindi thinking, for example 'देर हो गई' maps to 'was late' and it is a state, not an action.",
        "If the learner answer is correct, do not force an error. Set mistake.has_error to false and only suggest natural variations.",
        "If the learner answer is wrong, identify the exact wrong word or phrase and the replacement.",
        "Keep the output compact. No long paragraphs.",
        "Set status to one of: correct, almost, needs_practice.",
        "Use only these top-level keys: score, status, best_answer, mistake, pattern, meaning_mapping, natural_variations.",
        "The 'mistake' object must contain: has_error, wrong_part, correction, explanation.",
        "The 'pattern' object must contain: name, structure, usage_note, translation_tip, examples.",
        "pattern.usage_note must explain how to choose the right form inside the structure when there are multiple choices.",
        "pattern.translation_tip must tell the learner how to translate this kind of sentence next time.",
        "pattern.examples must contain exactly 2 new Hindi sentences with their English translations. Do not repeat the original sentence or the best_answer there.",
        "Each meaning_mapping item must contain: native, english, note. The note can be a short explanation or null.",
        "Example of a good explanation: 'went' shows action, but here you need to describe your condition: being late.",
        f"Learner level: {level}.",
        f"Native sentence: {source_sentence}",
        "User answer: compare against the learner message.",
        f"Expected answer: {reference_translation}",
    ]

    if goal:
        prompt_sections.append(f"Learner goal: {goal}.")

    return "\n".join(prompt_sections)


def build_translation_clarification_prompt(
    *,
    english_level: str | None,
    source_sentence: str,
    reference_translation: str,
    learner_question: str,
    reply_preview_text: str | None = None,
    replied_message_text: str | None = None,
    original_answer: str | None = None,
    corrected_answer: str | None = None,
    correction_explanation: str | None = None,
    correction_natural_version: str | None = None,
    correction_retry_prompt: str | None = None,
) -> str:
    level = english_level or "unknown"

    prompt_sections = [
        "You are a helpful English tutor inside a translation practice session.",
        "The learner asked a follow-up question about the current sentence or the correction.",
        "Answer the learner's question directly in simple English.",
        "Do not translate a different sentence.",
        "Do not evaluate the learner again unless the question clearly asks for that.",
        "Do not output JSON.",
        "Keep the answer short, clear, and specific.",
        "Use 2 to 3 short sentences.",
        "Use very simple words.",
        "Explain exactly what the learner is asking about.",
        "Do not add a practice reminder at the end. The app will show a separate continue button.",
        "If the learner asks about word order, explain the English word order using the current reference translation.",
        f"Learner level: {level}.",
        f"Current Hindi sentence: {source_sentence}",
        f"Reference translation: {reference_translation}",
    ]

    if reply_preview_text:
        prompt_sections.append(f"Reply context preview: {reply_preview_text}")
    if replied_message_text:
        prompt_sections.append(f"Full replied message text: {replied_message_text}")
    if original_answer:
        prompt_sections.append(f"Learner's earlier answer: {original_answer}")
    if corrected_answer:
        prompt_sections.append(f"Correction shown to learner: {corrected_answer}")
    if correction_explanation:
        prompt_sections.append(f"Correction explanation shown earlier: {correction_explanation}")
    if correction_natural_version:
        prompt_sections.append(f"More natural version shown earlier: {correction_natural_version}")
    if correction_retry_prompt:
        prompt_sections.append(f"Retry guidance shown earlier: {correction_retry_prompt}")

    prompt_sections.append(f"Learner question: {learner_question}")
    return "\n".join(prompt_sections)
