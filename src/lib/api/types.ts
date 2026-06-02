export type User = {
  id: string;
  email: string;
  full_name: string | null;
  native_language: string | null;
  english_level: string | null;
  learning_goal: string | null;
  practice_preference: string | null;
  onboarding_completed: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export type EnglishLevel = 'beginner' | 'intermediate' | 'advanced' | 'not_sure';

export type LearningGoal =
  | 'daily_conversation'
  | 'job_interview'
  | 'business_english'
  | 'travel_english'
  | 'exam_preparation'
  | 'confidence_building';

export type PracticePreference = 'speaking' | 'writing' | 'both';

export type Onboarding = {
  user_id: string;
  native_language: string | null;
  english_level: EnglishLevel | null;
  learning_goal: LearningGoal | null;
  practice_preference: PracticePreference | null;
  onboarding_completed: boolean;
};

export type Topic = {
  id: string;
  slug: string;
  title: string;
  description: string | null;
  category: string | null;
  difficulty_level: string | null;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
};

export type PracticeMode =
  | 'free_chat'
  | 'guided_topic'
  | 'roleplay'
  | 'speaking_practice'
  | 'translation_practice';

export type PracticeMessage = {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  message_order: number;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type MessageReplyContext = {
  kind: 'message' | 'correction';
  preview_text: string;
  source_message_id?: string | null;
  original_text?: string | null;
  corrected_text?: string | null;
};

export type ChatRequestMetadata = {
  reply_context?: MessageReplyContext | null;
};

export type PracticeSession = {
  id: string;
  user_id: string;
  topic_id: string | null;
  mode: PracticeMode | string;
  title: string | null;
  status: string;
  started_at: string;
  ended_at: string | null;
  created_at: string;
  updated_at: string;
  topic: Topic | null;
};

export type PracticeSessionStarter = {
  assistant_message: PracticeMessage;
  quick_replies: string[];
  is_fresh: boolean;
};

export type PracticeSessionCompletionSummary = {
  title: string;
  message: string;
  completed_items: number;
  average_score: number | null;
  strongest_area: string | null;
  focus_area: string | null;
  recommended_next_practice: ProgressRecommendedPractice;
  auto_completed: boolean;
};

export type PracticeSessionDetail = PracticeSession & {
  messages: PracticeMessage[];
  starter: PracticeSessionStarter | null;
  completion_summary?: PracticeSessionCompletionSummary | null;
};

export type MessageCorrection = {
  id: string;
  message_id: string;
  attempt_id: string;
  is_correct: boolean;
  score: number;
  status: 'correct' | 'almost' | 'needs_practice';
  native_sentence: string;
  feedback_level: 'excellent' | 'good' | 'needs_practice';
  user_answer: string;
  best_answer: string;
  correct_answer: string;
  natural_answer: string;
  quick_feedback: string;
  tense_explanation: {
    tense_or_pattern: string;
    why_this_pattern: string;
    structure: string;
    native_to_english_mapping: {
      native_part: string;
      english_part: string;
      role: string;
    }[];
    correct_translation_using_structure: string;
    similar_example: {
      native: string;
      english: string;
    };
  };
  user_mistake: {
    is_wrong: boolean;
    wrong_part: string;
    replace_with: string;
    reason: string;
  };
  retry: {
    needed: boolean;
    prompt: string;
    hint: string | null;
  };
  what_is_wrong: {
    title: string;
    explanation: string;
  };
  why_it_is_wrong: {
    title: string;
    explanation: string;
  };
  think_like_this: {
    wrong_thinking: string;
    correct_thinking: string;
  };
  grammar_breakdown: {
    topic: string;
    user_sentence_analysis: string;
    correct_sentence_analysis: string;
    structure: string;
    example_pattern: string;
    tense_used: string;
    why_this_tense: string;
    native_language_note: string;
  };
  translation_tip: string;
  practice_examples: {
    native: string;
    english: string;
  }[];
  key_learning: string;
  natural_variations: string[];
  mistakes: {
    type:
      | 'grammar'
      | 'vocabulary'
      | 'tense'
      | 'sentence_structure'
      | 'word_order'
      | 'meaning'
      | 'word_by_word_translation'
      | 'spelling';
    wrong: string;
    correct: string;
    explanation: string;
  }[];
  retry_strategy: {
    should_retry: boolean;
    retry_type: 'same_sentence' | 'hint' | 'fill_blank' | 'next_question';
    retry_prompt: string;
    hint: string | null;
  };
  encouragement: string;
  should_move_next: boolean;
  original_text: string;
  corrected_text: string;
  explanation: string;
  natural_version: string;
  retry_prompt: string;
  tags: string[] | null;
  severity: 'none' | 'low' | 'medium' | 'high' | string;
  feedback_json?: Record<string, unknown> | null;
  created_at: string;
};

export type PersonalizationSummary = {
  top_weak_areas: string[];
  total_corrections_count: number;
  average_message_length: number | null;
  last_recommended_focus: string | null;
  detected_translation_level: string | null;
  total_translation_items_completed: number;
  average_translation_attempts: number | null;
  translation_first_try_rate: number | null;
};

export type PersonalizationRecommendation = {
  focus_title: string;
  short_reason: string;
  suggested_action: string;
};

export type MistakePattern = {
  id: string;
  tag: string;
  frequency: number;
  first_seen_at: string;
  last_seen_at: string;
  last_example_original: string | null;
  last_example_corrected: string | null;
  severity_score: number | null;
  created_at: string;
  updated_at: string;
};

export type ChatResponse = {
  session_id: string;
  user_message: PracticeMessage;
  assistant_message: PracticeMessage;
  correction: MessageCorrection | null;
  completion_summary?: PracticeSessionCompletionSummary | null;
};

export type VoiceTranscriptionMetadata = {
  provider: string;
  model: string;
  mime_type: string | null;
  duration_ms: number | null;
  source: string | null;
  language: string | null;
  file_name: string | null;
};

export type VoiceChatResponse = {
  session_id: string;
  transcript: string;
  user_message: PracticeMessage;
  assistant_message: PracticeMessage;
  correction: MessageCorrection | null;
  transcription: VoiceTranscriptionMetadata;
};

export type SignupPayload = {
  email: string;
  password: string;
  full_name?: string;
};

export type LoginPayload = {
  email: string;
  password: string;
};

export type OnboardingPayload = {
  native_language: string;
  english_level: EnglishLevel;
  learning_goal: LearningGoal;
  practice_preference: PracticePreference;
};

export type FirstPlanTask = {
  type: 'translation' | 'speaking' | 'conversation';
  title: string;
  estimated_minutes: number;
};

export type FirstPlan = {
  title: string;
  description: string;
  tasks: FirstPlanTask[];
};

export type OnboardingCompleteResponse = {
  success: boolean;
  onboarding: Onboarding;
  first_plan: FirstPlan;
};

export type DailyPlanTask = {
  id: string;
  type: 'translation' | 'review' | 'speaking' | 'conversation';
  title: string;
  description: string;
  estimated_minutes: number;
  status: 'pending' | 'completed';
};

export type DailyPlan = {
  date: string;
  title: string;
  estimated_minutes: number;
  tasks: DailyPlanTask[];
};

export type LearningProfileArea = {
  type: string;
  count: number;
  label: string;
};

export type LearningProfileMistake = {
  type: string;
  label: string;
  wrong: string;
  correct: string;
  count: number;
  last_seen_at: string;
};

export type LearningProfile = {
  average_score: number;
  average_conversation_score?: number;
  speaking_confidence_score?: number;
  total_conversation_turns?: number;
  total_practice_sessions: number;
  total_attempts: number;
  total_correct_attempts: number;
  weak_areas: LearningProfileArea[];
  strong_areas: LearningProfileArea[];
  repeated_mistakes: LearningProfileMistake[];
  recent_mistakes: LearningProfileMistake[];
  recommended_focus_area: string | null;
  current_difficulty: string;
  summary: string;
};

export type ProgressRecommendedPractice = {
  type: 'mistake_review' | 'translation_practice' | 'roleplay_speaking';
  title: string;
};

export type ProgressDashboard = {
  overall_score: number;
  average_translation_score: number;
  average_conversation_score: number;
  total_practice_sessions: number;
  total_questions_answered: number;
  total_conversations: number;
  streak_days: number;
  top_weak_areas: LearningProfileArea[];
  recent_improvements: string[];
  recommended_next_practice: ProgressRecommendedPractice;
};

export type MistakeReviewItem = {
  id: string;
  type:
    | 'tense'
    | 'grammar'
    | 'vocabulary'
    | 'sentence_structure'
    | 'word_order'
    | 'meaning'
    | 'word_by_word_translation'
    | 'spelling';
  wrong_sentence: string;
  correct_sentence: string;
  explanation: string;
  retry_question: string;
  focus_area:
    | 'tense'
    | 'grammar'
    | 'vocabulary'
    | 'sentence_structure'
    | 'word_order'
    | 'meaning'
    | 'word_by_word_translation'
    | 'spelling';
  seen_count: number;
  status: 'needs_practice' | 'improved' | 'resolved';
};

export type MistakeReviewListResponse = {
  mistakes: MistakeReviewItem[];
};

export type MistakeRetryRequest = {
  mistake_id: string;
  retry_answer: string;
  input_mode: 'text' | 'speech';
};

export type MistakeRetryResponse = {
  is_improved: boolean;
  score: number;
  correct_answer: string;
  natural_answer: string;
  feedback: string;
  remaining_issue: string | null;
  status: 'improved' | 'needs_more_practice';
};

export type MistakeRetryVoiceResponse = {
  transcript: string;
  result: MistakeRetryResponse;
  transcription: VoiceTranscriptionMetadata;
};

export type CreatePracticeSessionPayload = {
  mode: PracticeMode;
  topic_id?: string | null;
  title?: string | null;
};

export type ConversationScenario =
  | 'job_interview'
  | 'client_meeting'
  | 'daily_conversation'
  | 'ordering_food'
  | 'travel_airport'
  | 'introduce_yourself'
  | 'confidence_practice';

export type ConversationStartRequest = {
  scenario: ConversationScenario;
};

export type ConversationStartResponse = {
  session_id: string;
  scenario: ConversationScenario;
  level: 'beginner' | 'intermediate' | 'advanced';
  title: string;
  ai_message: string;
  goal: string;
  max_turns: number;
};

export type ConversationSessionStateResponse = {
  session_id: string;
  status: string;
  completed_at?: string | null;
};

export type ConversationMistake = {
  type: 'grammar' | 'vocabulary' | 'sentence_structure' | 'spelling' | 'tense';
  issue: string;
  fix: string;
  reason: string;
};

export type ConversationSummary = {
  average_score: number;
  best_area: string;
  weak_area: string;
  tip: string;
};

export type ConversationReplyRequest = {
  session_id: string;
  user_message: string;
};

export type ConversationReplyResponse = {
  turn_number: number;
  score: number;
  feedback_level: 'good' | 'needs_improvement' | 'excellent';
  corrected_sentence: string;
  natural_sentence: string;
  mistakes: ConversationMistake[];
  encouragement: string;
  ai_reply: string;
  session_completed: boolean;
  remaining_turns: number;
  summary?: ConversationSummary | null;
};

export type ConversationVoiceReplyResponse = {
  transcript: string;
  result: ConversationReplyResponse;
  transcription: VoiceTranscriptionMetadata;
};
