export function formatLearningAreaLabel(area: string | null | undefined) {
  if (!area) {
    return 'General fluency';
  }

  const normalized = area.trim().toLowerCase();
  const mapping: Record<string, string> = {
    tense: 'Tense',
    grammar: 'Grammar',
    vocabulary: 'Vocabulary',
    sentence_structure: 'Sentence structure',
    word_order: 'Word order',
    meaning: 'Meaning',
    word_by_word_translation: 'Word-by-word translation',
    spelling: 'Spelling',
    confidence: 'Confidence',
    general_fluency: 'General fluency',
  };

  return mapping[normalized] ?? normalized.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}
