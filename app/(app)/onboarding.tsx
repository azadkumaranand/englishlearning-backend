import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import Animated, { FadeIn, FadeInDown } from 'react-native-reanimated';

import { LoadingScreen } from '@/src/components/loading-screen';
import { PrimaryButton } from '@/src/components/primary-button';
import { ScreenContainer } from '@/src/components/screen-container';
import { useAuth } from '@/src/hooks/use-auth';
import { practiceApi } from '@/src/lib/api/practice';
import type {
  EnglishLevel,
  FirstPlan,
  LearningGoal,
  OnboardingPayload,
  PracticeMode,
  PracticePreference,
} from '@/src/lib/api/types';
import { colors, radii, shadows, spacing, typography } from '@/src/theme';

const NATIVE_LANGUAGE_OPTIONS = [
  { value: 'Hindi', label: 'Hindi', description: 'Learn from familiar daily examples.' },
  { value: 'Bengali', label: 'Bengali', description: 'Start with simple practical phrases.' },
  { value: 'Marathi', label: 'Marathi', description: 'Build confidence from everyday usage.' },
  { value: 'Tamil', label: 'Tamil', description: 'Practice with clear beginner-friendly prompts.' },
  { value: 'Telugu', label: 'Telugu', description: 'Move from translation to natural replies.' },
  { value: 'Other', label: 'Other', description: 'We will still personalize the practice for you.' },
] as const;

const ENGLISH_LEVEL_OPTIONS: {
  value: EnglishLevel;
  label: string;
  description: string;
  emoji: string;
}[] = [
  { value: 'beginner', label: 'Beginner', description: 'I need simple words and short sentences.', emoji: '🌱' },
  { value: 'intermediate', label: 'Intermediate', description: 'I can speak some English but need practice.', emoji: '🌿' },
  { value: 'advanced', label: 'Advanced', description: 'I want natural, polished English.', emoji: '🌳' },
  { value: 'not_sure', label: 'Not sure', description: 'Help me start first. We can test later.', emoji: '🧭' },
] as const;

const LEARNING_GOAL_OPTIONS: {
  value: LearningGoal;
  label: string;
  description: string;
  emoji: string;
}[] = [
  { value: 'daily_conversation', label: 'Daily conversation', description: 'Talk more naturally in everyday life.', emoji: '💬' },
  { value: 'job_interview', label: 'Job interview', description: 'Practice common interview answers.', emoji: '💼' },
  { value: 'business_english', label: 'Business English', description: 'Improve meetings, email, and work talk.', emoji: '📈' },
  { value: 'travel_english', label: 'Travel English', description: 'Use useful English while traveling.', emoji: '✈️' },
  { value: 'exam_preparation', label: 'Exam preparation', description: 'Train for structured English tasks.', emoji: '📘' },
  { value: 'confidence_building', label: 'Confidence building', description: 'Speak without freezing or overthinking.', emoji: '⚡' },
] as const;

const PRACTICE_PREFERENCE_OPTIONS: {
  value: PracticePreference;
  label: string;
  description: string;
  emoji: string;
}[] = [
  { value: 'speaking', label: 'Speaking first', description: 'I want to talk and hear replies.', emoji: '🎙️' },
  { value: 'writing', label: 'Writing first', description: 'I want to type and improve sentence building.', emoji: '✍️' },
  { value: 'both', label: 'Both', description: 'I want a balanced mix of speaking and writing.', emoji: '🔄' },
] as const;

type OnboardingStep =
  | 'welcome'
  | 'native_language'
  | 'english_level'
  | 'learning_goal'
  | 'practice_preference'
  | 'first_plan';

type OnboardingState = {
  native_language: string;
  english_level: EnglishLevel | null;
  learning_goal: LearningGoal | null;
  practice_preference: PracticePreference | null;
};

const STEP_ORDER: OnboardingStep[] = [
  'welcome',
  'native_language',
  'english_level',
  'learning_goal',
  'practice_preference',
];

const TOTAL_PROGRESS_STEPS = STEP_ORDER.length;

function StepProgress({ current }: { current: number }) {
  return (
    <View style={styles.progressBlock}>
      <Text style={styles.progressLabel}>Step {current} of {TOTAL_PROGRESS_STEPS}</Text>
      <View style={styles.progressTrack}>
        <View style={[styles.progressFill, { width: `${(current / TOTAL_PROGRESS_STEPS) * 100}%` }]} />
      </View>
    </View>
  );
}

function HeroHeader({
  eyebrow,
  title,
  description,
  emoji,
}: {
  eyebrow: string;
  title: string;
  description: string;
  emoji: string;
}) {
  return (
    <Animated.View entering={FadeIn.duration(280)} style={styles.heroCard}>
      <View style={styles.heroGlowPrimary} />
      <View style={styles.heroGlowAccent} />
      <Text style={styles.heroEyebrow}>{eyebrow}</Text>
      <View style={styles.heroTitleRow}>
        <Text style={styles.heroEmoji}>{emoji}</Text>
        <Text style={styles.heroTitle}>{title}</Text>
      </View>
      <Text style={styles.heroDescription}>{description}</Text>
    </Animated.View>
  );
}

function ChoiceCard({
  title,
  description,
  emoji,
  selected,
  onPress,
}: {
  title: string;
  description: string;
  emoji?: string;
  selected: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.choiceCard,
        shadows.sm,
        selected && styles.choiceCardSelected,
        pressed && styles.choiceCardPressed,
      ]}>
      <View style={styles.choiceRow}>
        <View style={styles.choiceCopy}>
          <View style={styles.choiceTitleRow}>
            {emoji ? <Text style={styles.choiceEmoji}>{emoji}</Text> : null}
            <Text style={[styles.choiceTitle, selected && styles.choiceTitleSelected]}>{title}</Text>
          </View>
          <Text style={styles.choiceDescription}>{description}</Text>
        </View>
        <View style={[styles.choiceIndicator, selected && styles.choiceIndicatorSelected]}>
          {selected ? <View style={styles.choiceIndicatorInner} /> : null}
        </View>
      </View>
    </Pressable>
  );
}

function WelcomeScreen() {
  return (
    <View style={styles.stepBody}>
      <HeroHeader
        eyebrow="Phase 1"
        title="Meet your AI English tutor"
        description="We’ll personalize your first practice so it feels easy to start and useful from minute one."
        emoji="👋"
      />
      <View style={styles.infoStack}>
        <InfoRow title="Short setup" description="Just a few quick choices before your first session." emoji="⏱️" />
        <InfoRow title="Personalized first plan" description="We’ll match your level, goal, and practice style." emoji="🎯" />
        <InfoRow title="Start learning immediately" description="You’ll jump into your first practice right after setup." emoji="🚀" />
      </View>
    </View>
  );
}

function NativeLanguageScreen({
  value,
  onSelect,
}: {
  value: string;
  onSelect: (next: string) => void;
}) {
  return (
    <View style={styles.stepBody}>
      <HeroHeader
        eyebrow="Personalize"
        title="What is your native language?"
        description="This helps us explain things more naturally and choose better first examples."
        emoji="🌍"
      />
      <View style={styles.choiceStack}>
        {NATIVE_LANGUAGE_OPTIONS.map((option) => (
          <ChoiceCard
            key={option.value}
            title={option.label}
            description={option.description}
            selected={value === option.value}
            onPress={() => onSelect(option.value)}
          />
        ))}
      </View>
    </View>
  );
}

function EnglishLevelScreen({
  value,
  onSelect,
}: {
  value: EnglishLevel | null;
  onSelect: (next: EnglishLevel) => void;
}) {
  return (
    <View style={styles.stepBody}>
      <HeroHeader
        eyebrow="Level"
        title="Choose your English level"
        description="We’ll adjust vocabulary, sentence length, and practice difficulty based on this."
        emoji="📶"
      />
      <View style={styles.choiceStack}>
        {ENGLISH_LEVEL_OPTIONS.map((option) => (
          <ChoiceCard
            key={option.value}
            title={option.label}
            description={option.description}
            emoji={option.emoji}
            selected={value === option.value}
            onPress={() => onSelect(option.value)}
          />
        ))}
      </View>
    </View>
  );
}

function LearningGoalScreen({
  value,
  onSelect,
}: {
  value: LearningGoal | null;
  onSelect: (next: LearningGoal) => void;
}) {
  return (
    <View style={styles.stepBody}>
      <HeroHeader
        eyebrow="Goal"
        title="Why are you learning English?"
        description="Your first plan should fit the kind of English you actually want to use."
        emoji="🎯"
      />
      <View style={styles.choiceStack}>
        {LEARNING_GOAL_OPTIONS.map((option) => (
          <ChoiceCard
            key={option.value}
            title={option.label}
            description={option.description}
            emoji={option.emoji}
            selected={value === option.value}
            onPress={() => onSelect(option.value)}
          />
        ))}
      </View>
    </View>
  );
}

function PracticePreferenceScreen({
  value,
  onSelect,
}: {
  value: PracticePreference | null;
  onSelect: (next: PracticePreference) => void;
}) {
  return (
    <View style={styles.stepBody}>
      <HeroHeader
        eyebrow="Style"
        title="How do you want to practice first?"
        description="We’ll shape your first session around the way you feel most comfortable starting."
        emoji="🧠"
      />
      <View style={styles.choiceStack}>
        {PRACTICE_PREFERENCE_OPTIONS.map((option) => (
          <ChoiceCard
            key={option.value}
            title={option.label}
            description={option.description}
            emoji={option.emoji}
            selected={value === option.value}
            onPress={() => onSelect(option.value)}
          />
        ))}
      </View>
    </View>
  );
}

function FirstPlanScreen({
  firstPlan,
  nativeLanguage,
  englishLevel,
}: {
  firstPlan: FirstPlan;
  nativeLanguage: string;
  englishLevel: EnglishLevel | null;
}) {
  return (
    <View style={styles.stepBody}>
      <HeroHeader
        eyebrow="Your plan"
        title={firstPlan.title}
        description={firstPlan.description}
        emoji="🗺️"
      />
      <View style={[styles.planCard, shadows.sm]}>
        <Text style={styles.planMeta}>
          Native language: {nativeLanguage} • Level: {englishLevel ? englishLevel.replace('_', ' ') : 'not set'}
        </Text>
        <View style={styles.planTaskStack}>
          {firstPlan.tasks.map((task, index) => (
            <Animated.View key={`${task.type}-${task.title}`} entering={FadeInDown.delay(index * 80).duration(240)}>
              <View style={styles.planTask}>
                <View style={styles.planTaskBadge}>
                  <Text style={styles.planTaskBadgeText}>{index + 1}</Text>
                </View>
                <View style={styles.planTaskCopy}>
                  <Text style={styles.planTaskTitle}>{task.title}</Text>
                  <Text style={styles.planTaskMeta}>
                    {task.type.replace('_', ' ')} • {task.estimated_minutes} min
                  </Text>
                </View>
              </View>
            </Animated.View>
          ))}
        </View>
      </View>
    </View>
  );
}

function InfoRow({
  title,
  description,
  emoji,
}: {
  title: string;
  description: string;
  emoji: string;
}) {
  return (
    <View style={styles.infoRow}>
      <View style={styles.infoIconWrap}>
        <Text style={styles.infoEmoji}>{emoji}</Text>
      </View>
      <View style={styles.infoCopy}>
        <Text style={styles.infoTitle}>{title}</Text>
        <Text style={styles.infoDescription}>{description}</Text>
      </View>
    </View>
  );
}

function getSessionModeFromPlan(plan: FirstPlan): PracticeMode {
  const firstTaskType = plan.tasks[0]?.type;
  if (firstTaskType === 'speaking' || firstTaskType === 'conversation') {
    return 'free_chat';
  }
  return 'translation_practice';
}

export default function OnboardingScreen() {
  const auth = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [step, setStep] = useState<OnboardingStep>('welcome');
  const [state, setState] = useState<OnboardingState>({
    native_language: auth.onboarding?.native_language ?? 'Hindi',
    english_level: auth.onboarding?.english_level ?? null,
    learning_goal: auth.onboarding?.learning_goal ?? null,
    practice_preference: auth.onboarding?.practice_preference ?? null,
  });
  const [firstPlan, setFirstPlan] = useState<FirstPlan | null>(null);
  const [error, setError] = useState<string | null>(null);

  const stepIndex = useMemo(() => STEP_ORDER.indexOf(step), [step]);
  const canContinue = useMemo(() => {
    switch (step) {
      case 'welcome':
        return true;
      case 'native_language':
        return Boolean(state.native_language.trim());
      case 'english_level':
        return Boolean(state.english_level);
      case 'learning_goal':
        return Boolean(state.learning_goal);
      case 'practice_preference':
        return Boolean(state.practice_preference);
      case 'first_plan':
        return Boolean(firstPlan);
      default:
        return false;
    }
  }, [firstPlan, state.english_level, state.learning_goal, state.native_language, state.practice_preference, step]);

  const completeOnboardingMutation = useMutation({
    mutationFn: async () => {
      if (!state.english_level || !state.learning_goal || !state.practice_preference) {
        throw new Error('Please complete each step before continuing.');
      }

      const payload: OnboardingPayload = {
        native_language: state.native_language,
        english_level: state.english_level,
        learning_goal: state.learning_goal,
        practice_preference: state.practice_preference,
      };
      return auth.completeOnboarding(payload);
    },
    onSuccess: (response) => {
      setError(null);
      setFirstPlan(response.first_plan);
      setStep('first_plan');
    },
    onError: (nextError) => {
      setError(nextError instanceof Error ? nextError.message : 'Unable to save onboarding');
    },
  });

  const startPracticeMutation = useMutation({
    mutationFn: async () => {
      if (!firstPlan) {
        throw new Error('Your first plan is not ready yet.');
      }

      const mode = getSessionModeFromPlan(firstPlan);
      return auth.authorizedRequest((token) =>
        practiceApi.createSession(token, {
          mode,
          title: firstPlan.title,
        })
      );
    },
    onSuccess: (session) => {
      queryClient.setQueryData(['practice-session', session.id], session);
      void queryClient.invalidateQueries({ queryKey: ['practice-sessions'] });
      router.replace({
        pathname: '/(app)/session/[id]',
        params: { id: session.id, fromOnboarding: '1' },
      });
    },
    onError: (nextError) => {
      setError(nextError instanceof Error ? nextError.message : 'Unable to start first practice');
    },
  });

  if (completeOnboardingMutation.isPending || startPracticeMutation.isPending) {
    return (
      <LoadingScreen
        message={
          completeOnboardingMutation.isPending
            ? 'Preparing your first plan…'
            : 'Starting your first practice…'
        }
      />
    );
  }

  const footer = (
    <View style={styles.footerRow}>
      {step !== 'welcome' && step !== 'first_plan' ? (
        <PrimaryButton
          label="Back"
          onPress={() => {
            setError(null);
            setStep(STEP_ORDER[Math.max(stepIndex - 1, 0)] ?? 'welcome');
          }}
          variant="secondary"
          icon="←"
        />
      ) : (
        <View style={styles.footerSpacer} />
      )}

      <PrimaryButton
        label={step === 'first_plan' ? 'Start First Practice' : step === 'practice_preference' ? 'See My Plan' : 'Continue'}
        onPress={() => {
          setError(null);

          if (step === 'first_plan') {
            startPracticeMutation.mutate();
            return;
          }

          if (step === 'practice_preference') {
            completeOnboardingMutation.mutate();
            return;
          }

          setStep(STEP_ORDER[Math.min(stepIndex + 1, STEP_ORDER.length - 1)] ?? 'welcome');
        }}
        disabled={!canContinue}
        icon={step === 'first_plan' ? '🚀' : '→'}
      />
    </View>
  );

  return (
    <ScreenContainer
      scroll
      footer={footer}
      header={step === 'first_plan' ? undefined : <StepProgress current={Math.max(1, stepIndex + 1)} />}>
      {step === 'welcome' ? <WelcomeScreen /> : null}
      {step === 'native_language' ? (
        <NativeLanguageScreen
          value={state.native_language}
          onSelect={(nativeLanguage) => setState((current) => ({ ...current, native_language: nativeLanguage }))}
        />
      ) : null}
      {step === 'english_level' ? (
        <EnglishLevelScreen
          value={state.english_level}
          onSelect={(englishLevel) => setState((current) => ({ ...current, english_level: englishLevel }))}
        />
      ) : null}
      {step === 'learning_goal' ? (
        <LearningGoalScreen
          value={state.learning_goal}
          onSelect={(learningGoal) => setState((current) => ({ ...current, learning_goal: learningGoal }))}
        />
      ) : null}
      {step === 'practice_preference' ? (
        <PracticePreferenceScreen
          value={state.practice_preference}
          onSelect={(practicePreference) =>
            setState((current) => ({ ...current, practice_preference: practicePreference }))
          }
        />
      ) : null}
      {step === 'first_plan' && firstPlan ? (
        <FirstPlanScreen
          firstPlan={firstPlan}
          nativeLanguage={state.native_language}
          englishLevel={state.english_level}
        />
      ) : null}

      {error ? <Text style={styles.errorText}>⚠️ {error}</Text> : null}
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  progressBlock: {
    gap: spacing.xs,
    paddingTop: spacing.sm,
  },
  progressLabel: {
    ...typography.captionBold,
    color: colors.text.secondary,
    textTransform: 'uppercase',
  },
  progressTrack: {
    height: 8,
    borderRadius: 999,
    backgroundColor: colors.neutral[200],
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 999,
    backgroundColor: colors.primary[500],
  },
  stepBody: {
    gap: spacing.xl,
  },
  heroCard: {
    borderRadius: radii.xl,
    padding: spacing.xl,
    backgroundColor: colors.bg.card,
    borderWidth: 1,
    borderColor: colors.border.light,
    overflow: 'hidden',
    ...shadows.sm,
  },
  heroGlowPrimary: {
    position: 'absolute',
    top: -28,
    right: -16,
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: colors.primary[100],
  },
  heroGlowAccent: {
    position: 'absolute',
    bottom: -34,
    left: -18,
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: colors.accent[50],
  },
  heroEyebrow: {
    ...typography.eyebrow,
    color: colors.primary[600],
    marginBottom: spacing.sm,
  },
  heroTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    marginBottom: spacing.sm,
  },
  heroEmoji: {
    fontSize: 30,
  },
  heroTitle: {
    ...typography.title,
    color: colors.text.primary,
    flex: 1,
  },
  heroDescription: {
    ...typography.bodyLg,
    color: colors.text.secondary,
  },
  infoStack: {
    gap: spacing.md,
  },
  infoRow: {
    flexDirection: 'row',
    gap: spacing.md,
    padding: spacing.lg,
    borderRadius: radii.xl,
    backgroundColor: colors.bg.card,
    borderWidth: 1,
    borderColor: colors.border.light,
    ...shadows.sm,
  },
  infoIconWrap: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.primary[50],
  },
  infoEmoji: {
    fontSize: 22,
  },
  infoCopy: {
    flex: 1,
    gap: spacing.xs,
  },
  infoTitle: {
    ...typography.bodyLgBold,
    color: colors.text.primary,
  },
  infoDescription: {
    ...typography.body,
    color: colors.text.secondary,
  },
  choiceStack: {
    gap: spacing.md,
  },
  choiceCard: {
    borderRadius: radii.xl,
    padding: spacing.lg,
    backgroundColor: colors.bg.card,
    borderWidth: 1.5,
    borderColor: colors.border.light,
  },
  choiceCardSelected: {
    borderColor: colors.primary[500],
    backgroundColor: colors.primary[50],
  },
  choiceCardPressed: {
    opacity: 0.92,
  },
  choiceRow: {
    flexDirection: 'row',
    gap: spacing.md,
    alignItems: 'center',
  },
  choiceCopy: {
    flex: 1,
    gap: spacing.xs,
  },
  choiceTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  choiceEmoji: {
    fontSize: 20,
  },
  choiceTitle: {
    ...typography.bodyLgBold,
    color: colors.text.primary,
  },
  choiceTitleSelected: {
    color: colors.primary[700],
  },
  choiceDescription: {
    ...typography.body,
    color: colors.text.secondary,
  },
  choiceIndicator: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: colors.border.medium,
    alignItems: 'center',
    justifyContent: 'center',
  },
  choiceIndicatorSelected: {
    borderColor: colors.primary[500],
  },
  choiceIndicatorInner: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.primary[500],
  },
  planCard: {
    borderRadius: radii.xl,
    padding: spacing.xl,
    backgroundColor: colors.bg.card,
    borderWidth: 1,
    borderColor: colors.border.light,
    gap: spacing.lg,
  },
  planMeta: {
    ...typography.captionBold,
    color: colors.text.secondary,
    textTransform: 'capitalize',
  },
  planTaskStack: {
    gap: spacing.md,
  },
  planTask: {
    flexDirection: 'row',
    gap: spacing.md,
    alignItems: 'center',
    padding: spacing.md,
    borderRadius: radii.lg,
    backgroundColor: colors.bg.subtle,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  planTaskBadge: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.primary[500],
  },
  planTaskBadgeText: {
    ...typography.bodySemibold,
    color: colors.text.inverse,
  },
  planTaskCopy: {
    flex: 1,
    gap: 2,
  },
  planTaskTitle: {
    ...typography.bodyLgBold,
    color: colors.text.primary,
  },
  planTaskMeta: {
    ...typography.body,
    color: colors.text.secondary,
    textTransform: 'capitalize',
  },
  footerRow: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  footerSpacer: {
    flex: 1,
  },
  errorText: {
    ...typography.bodyMedium,
    color: colors.error,
  },
});
