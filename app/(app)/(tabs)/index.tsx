import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import Animated, { FadeInUp } from 'react-native-reanimated';
import { Feather, Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';

import { LoadingScreen } from '@/src/components/loading-screen';
import { PrimaryButton } from '@/src/components/primary-button';
import { ScreenContainer } from '@/src/components/screen-container';
import { useAuth } from '@/src/hooks/use-auth';
import { dailyPlanApi } from '@/src/lib/api/daily-plan';
import { learningProfileApi } from '@/src/lib/api/learning-profile';
import { mistakesApi } from '@/src/lib/api/mistakes';
import { practiceApi } from '@/src/lib/api/practice';
import { progressApi } from '@/src/lib/api/progress';
import type { DailyPlan, LearningProfile, PracticeMode, ProgressDashboard } from '@/src/lib/api/types';
import { formatLearningAreaLabel } from '@/src/lib/learning-profile';
import { colors, radii, shadows, spacing, typography } from '@/src/theme';

const FALLBACK_PLAN: DailyPlan = {
  date: new Date().toISOString().slice(0, 10),
  title: 'Today’s English Practice',
  estimated_minutes: 10,
  tasks: [
    {
      id: 'task_1',
      type: 'translation',
      title: 'Practice 3 daily-life sentences',
      description: 'Improve sentence formation and confidence.',
      estimated_minutes: 5,
      status: 'pending',
    },
    {
      id: 'task_2',
      type: 'review',
      title: 'Review your recent mistakes',
      description: 'Fix repeated grammar mistakes.',
      estimated_minutes: 5,
      status: 'pending',
    },
  ],
};

const FALLBACK_PROFILE: LearningProfile = {
  average_score: 0,
  average_conversation_score: 0,
  speaking_confidence_score: 0,
  total_conversation_turns: 0,
  total_practice_sessions: 0,
  total_attempts: 0,
  total_correct_attempts: 0,
  weak_areas: [],
  strong_areas: [],
  repeated_mistakes: [],
  recent_mistakes: [],
  recommended_focus_area: null,
  current_difficulty: 'beginner',
  summary: 'Complete a few translation attempts and your weak areas will appear here.',
};

const FALLBACK_PROGRESS: ProgressDashboard = {
  overall_score: 0,
  average_translation_score: 0,
  average_conversation_score: 0,
  total_practice_sessions: 0,
  total_questions_answered: 0,
  total_conversations: 0,
  streak_days: 0,
  top_weak_areas: [],
  recent_improvements: [],
  recommended_next_practice: {
    type: 'translation_practice',
    title: 'Start your first translation practice',
  },
};

function buildHomePracticeMode(plan: DailyPlan): PracticeMode | 'roleplay_route' {
  const firstTaskType = plan.tasks[0]?.type;
  return firstTaskType === 'speaking' || firstTaskType === 'conversation'
    ? 'roleplay_route'
    : 'translation_practice';
}

function LevelBadge({ level, inverse }: { level: string | null; inverse?: boolean }) {
  return (
    <View style={[styles.levelBadge, inverse && styles.glassBadge]}>
      <Text style={[styles.levelBadgeText, inverse && { color: colors.text.inverse }]}>
        {level ? level.replace('_', ' ') : 'not set'}
      </Text>
    </View>
  );
}

export default function HomeScreen() {
  const auth = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();

  const sessionsQuery = useQuery({
    queryKey: ['practice-sessions', 'recent'],
    queryFn: () => auth.authorizedRequest((token) => practiceApi.listSessions(token)),
  });

  const dailyPlanQuery = useQuery({
    queryKey: ['daily-plan'],
    queryFn: () => auth.authorizedRequest((token) => dailyPlanApi.getMine(token)),
  });

  const learningProfileQuery = useQuery({
    queryKey: ['learning-profile'],
    queryFn: () => auth.authorizedRequest((token) => learningProfileApi.getMine(token)),
  });

  const reviewMistakesQuery = useQuery({
    queryKey: ['mistakes-review', 'home'],
    queryFn: () => auth.authorizedRequest((token) => mistakesApi.getReview(token)),
  });

  const progressQuery = useQuery({
    queryKey: ['progress-dashboard'],
    queryFn: () => auth.authorizedRequest((token) => progressApi.getMine(token)),
  });

  const startPracticeMutation = useMutation({
    mutationFn: ({ title, mode }: { title: string; mode: PracticeMode }) =>
      auth.authorizedRequest((token) =>
        practiceApi.createSession(token, {
          mode,
          title,
        })
      ),
    onSuccess: (session) => {
      queryClient.setQueryData(['practice-session', session.id], session);
      router.push(`/(app)/session/${session.id}`);
    },
  });

  if (
    sessionsQuery.isLoading ||
    dailyPlanQuery.isLoading ||
    learningProfileQuery.isLoading ||
    progressQuery.isLoading
  ) {
    return <LoadingScreen message="Getting your home ready…" />;
  }

  if (startPracticeMutation.isPending) {
    return <LoadingScreen message="Preparing your next practice…" />;
  }

  const user = auth.user;
  const firstName = user?.full_name?.split(' ')[0] ?? 'Learner';
  const recentSessions = sessionsQuery.data ?? [];
  const activeTranslationSession =
    recentSessions.find(
      (session) => session.mode === 'translation_practice' && session.status === 'active'
    ) ?? null;
  const todayPlan = dailyPlanQuery.data ?? FALLBACK_PLAN;
  const learningProfile = learningProfileQuery.data ?? FALLBACK_PROFILE;
  const progress = progressQuery.data ?? FALLBACK_PROGRESS;
  const reviewMistakes = reviewMistakesQuery.data?.mistakes ?? [];
  const topWeakArea = learningProfile.weak_areas[0] ?? null;

  const handleContinuePractice = () => {
    if (activeTranslationSession) {
      router.push(`/(app)/session/${activeTranslationSession.id}`);
      return;
    }

    const nextMode = buildHomePracticeMode(todayPlan);
    if (nextMode === 'roleplay_route') {
      router.push('/(app)/conversation-scenarios');
      return;
    }

    startPracticeMutation.mutate({
      title: todayPlan.title,
      mode: nextMode,
    });
  };

  return (
    <ScreenContainer scroll>
      {/* 1. HERO SECTION */}
      <Animated.View entering={FadeInUp.delay(100).springify()}>
        <LinearGradient
          colors={colors.gradients.hero}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={[styles.heroCard, shadows.md]}
        >
          <Text style={[styles.heroEyebrow, { color: colors.primary[200] }]}>Welcome back</Text>
          <Text style={[styles.heroTitle, { color: colors.text.inverse }]}>Hi, {firstName}</Text>

          <View style={styles.heroMetaRow}>
            <LevelBadge level={user?.english_level ?? learningProfile.current_difficulty} inverse />
            <View style={[styles.goalBadge, styles.glassBadge]}>
              <Text style={[styles.goalBadgeText, { color: colors.text.inverse }]}>
                {user?.learning_goal ? user.learning_goal.replace(/_/g, ' ') : 'goal not set'}
              </Text>
            </View>
          </View>
        </LinearGradient>
      </Animated.View>

      {/* 2. MAIN DAILY ACTIONS (Today's Plan & Review) */}
      <Animated.View entering={FadeInUp.delay(200).springify()}>
        <View style={[styles.planCard, shadows.sm]}>
          <View style={styles.planHeaderRow}>
            <View>
              <View style={styles.titleWithIcon}>
                <Ionicons name="calendar-outline" size={18} color={colors.text.tertiary} />
                <Text style={styles.planEyebrow}>Today’s plan</Text>
              </View>
              <Text style={styles.planTitle}>{todayPlan.title}</Text>
            </View>
            <View style={styles.minutesPill}>
              <MaterialCommunityIcons name="clock-outline" size={14} color={colors.gold[600]} />
              <Text style={styles.minutesPillText}>{todayPlan.estimated_minutes} min</Text>
            </View>
          </View>

          <View style={styles.taskList}>
            {todayPlan.tasks.map((task, index) => (
              <View key={task.id} style={styles.taskRow}>
                <View style={styles.taskTimeline}>
                  <View style={styles.taskMarker} />
                  {index < todayPlan.tasks.length - 1 && <View style={styles.taskLine} />}
                </View>
                <View style={styles.taskCopy}>
                  <Text style={styles.taskTitle}>{task.title}</Text>
                  <Text style={styles.taskDescription}>{task.description}</Text>
                </View>
                <Text style={styles.taskMinutes}>{task.estimated_minutes}m</Text>
              </View>
            ))}
          </View>

          <PrimaryButton
            label={activeTranslationSession ? 'Continue Practice' : 'Start Today’s Practice'}
            onPress={handleContinuePractice}
            icon={<Feather name="play" size={18} color={colors.text.inverse} />}
          />
        </View>
      </Animated.View>

      {reviewMistakes.length > 0 ? (
        <Animated.View entering={FadeInUp.delay(300).springify()}>
          <View style={[styles.reviewCard, shadows.sm]}>
            <View style={styles.titleWithIcon}>
              <Feather name="refresh-ccw" size={18} color={colors.primary[600]} />
              <Text style={styles.reviewEyebrow}>Mistake review</Text>
            </View>
            <Text style={styles.reviewTitle}>
              Review {reviewMistakes.length} recent mistake{reviewMistakes.length > 1 ? 's' : ''}
            </Text>
            <PrimaryButton
              label="Start Review"
              onPress={() => router.push('/(app)/mistake-review')}
              icon={<Ionicons name="reload" size={18} color={colors.text.inverse} />}
            />
          </View>
        </Animated.View>
      ) : null}

      {/* 3. YOUR ANALYTICS SECTION (Grouped at the bottom) */}
      <Animated.View entering={FadeInUp.delay(400).springify()} style={styles.sectionHeader}>
        <Text style={styles.sectionHeading}>Your Insights</Text>
      </Animated.View>

      <Animated.View entering={FadeInUp.delay(450).springify()}>
        <View style={styles.bentoGrid}>
          {/* Overall Score */}
          <View style={[styles.bentoCard, shadows.sm]}>
            <Feather name="trending-up" size={20} color={colors.primary[500]} />
            <Text style={styles.bentoLabel}>Overall Score</Text>
            <Text style={styles.bentoValue}>{progress.overall_score}</Text>
          </View>

          {/* Streak */}
          <View style={[styles.bentoCard, shadows.sm]}>
            <MaterialCommunityIcons name="fire" size={22} color={colors.gold[500]} />
            <Text style={styles.bentoLabel}>Active Streak</Text>
            <Text style={styles.bentoValue}>{progress.streak_days} days</Text>
          </View>
        </View>
      </Animated.View>

      <Animated.View entering={FadeInUp.delay(500).springify()}>
        <View style={styles.bentoGrid}>
          {/* Sessions Completed */}
          <View style={[styles.bentoCard, shadows.sm]}>
            <Feather name="activity" size={20} color={colors.primary[500]} />
            <Text style={styles.bentoLabel}>Sessions Run</Text>
            <Text style={styles.bentoValue}>{learningProfile.total_practice_sessions}</Text>
          </View>

          {/* Practice Rhythm (Streak Count) */}
          <View style={[styles.bentoCard, shadows.sm]}>
            <Feather name="check-circle" size={20} color={colors.primary[500]} />
            <Text style={styles.bentoLabel}>Correct Rate</Text>
            <Text style={styles.bentoValue}>{learningProfile.total_correct_attempts}</Text>
          </View>
        </View>
      </Animated.View>

      {/* Focus & Weak Areas Card (Consolidated Redirect) */}
      <Animated.View entering={FadeInUp.delay(550).springify()}>
        <View style={[styles.focusCard, shadows.sm]}>
          <View style={styles.focusHeaderRow}>
            <View style={styles.titleWithIcon}>
              <Feather name="target" size={20} color={colors.primary[600]} />
              <Text style={styles.focusTitle}>Focus Area</Text>
            </View>
          </View>

          <View style={styles.focusContent}>
            <Text style={styles.focusLead}>
              {topWeakArea ? topWeakArea.label : 'No weak area yet'}
            </Text>
            <Text style={styles.focusSummary}>
              {learningProfile.recommended_focus_area
                ? `Recommended practice target: focus on learning ${formatLearningAreaLabel(learningProfile.recommended_focus_area).toLowerCase()}.`
                : learningProfile.summary}
            </Text>
          </View>

          <View style={styles.divider} />

          <Pressable 
            style={styles.redirectButton} 
            onPress={() => router.push('/(app)/(tabs)/progress')}
          >
            <Text style={styles.redirectButtonText}>View Full Analytics</Text>
            <Feather name="arrow-right" size={16} color={colors.primary[600]} />
          </Pressable>
        </View>
      </Animated.View>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  heroCard: {
    borderRadius: radii['2xl'],
    padding: spacing.xl,
    gap: spacing.md,
    overflow: 'hidden',
  },
  heroEyebrow: {
    ...typography.eyebrow,
  },
  heroTitle: {
    ...typography.display,
  },
  heroMetaRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    flexWrap: 'wrap',
    marginTop: spacing.xs,
  },
  glassBadge: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.3)',
  },
  levelBadge: {
    backgroundColor: colors.primary[50],
    borderRadius: radii.full,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  levelBadgeText: {
    ...typography.captionBold,
    color: colors.primary[700],
    textTransform: 'capitalize',
  },
  goalBadge: {
    backgroundColor: colors.accent[50],
    borderRadius: radii.full,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  goalBadgeText: {
    ...typography.captionBold,
    color: colors.text.primary,
    textTransform: 'capitalize',
  },
  titleWithIcon: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  reviewCard: {
    backgroundColor: colors.bg.card,
    borderRadius: radii['2xl'],
    padding: spacing.xl,
    gap: spacing.md,
  },
  reviewEyebrow: {
    ...typography.captionBold,
    color: colors.primary[600],
    textTransform: 'uppercase',
  },
  reviewTitle: {
    ...typography.subheading,
    color: colors.text.primary,
    marginBottom: spacing.xs,
  },
  planCard: {
    backgroundColor: colors.bg.card,
    borderRadius: radii['2xl'],
    padding: spacing.xl,
    gap: spacing.lg,
  },
  planHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: spacing.md,
    alignItems: 'center',
  },
  planEyebrow: {
    ...typography.captionBold,
    color: colors.text.tertiary,
    textTransform: 'uppercase',
  },
  planTitle: {
    ...typography.subheading,
    color: colors.text.primary,
  },
  minutesPill: {
    backgroundColor: colors.gold[50],
    borderWidth: 1,
    borderColor: colors.gold[200],
    borderRadius: radii.full,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xxs,
  },
  minutesPillText: {
    ...typography.captionBold,
    color: colors.gold[600],
  },
  taskList: {
    gap: spacing.md,
    marginBottom: spacing.sm,
  },
  taskRow: {
    flexDirection: 'row',
    gap: spacing.md,
    alignItems: 'flex-start',
  },
  taskTimeline: {
    alignItems: 'center',
    width: 12,
  },
  taskMarker: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginTop: 4,
    backgroundColor: colors.primary[400],
    borderWidth: 2,
    borderColor: colors.primary[100],
  },
  taskLine: {
    width: 2,
    height: 40,
    backgroundColor: colors.border.light,
    marginTop: 4,
  },
  taskCopy: {
    flex: 1,
    gap: spacing.xxs,
  },
  taskTitle: {
    ...typography.bodyLgSemibold,
    color: colors.text.primary,
  },
  taskDescription: {
    ...typography.body,
    color: colors.text.secondary,
  },
  taskMinutes: {
    ...typography.captionBold,
    color: colors.text.tertiary,
  },
  sectionHeader: {
    marginTop: spacing.lg,
    marginBottom: spacing.xs,
    paddingHorizontal: spacing.xxs,
  },
  sectionHeading: {
    ...typography.subheading,
    color: colors.text.primary,
    fontWeight: '800',
  },
  bentoGrid: {
    flexDirection: 'row',
    gap: spacing.md,
    marginBottom: spacing.md,
  },
  bentoCard: {
    flex: 1,
    backgroundColor: colors.bg.card,
    borderRadius: radii.xl,
    padding: spacing.lg,
    gap: spacing.xxs,
  },
  bentoLabel: {
    ...typography.captionBold,
    color: colors.text.secondary,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  bentoValue: {
    ...typography.heading,
    color: colors.text.primary,
    fontWeight: '800',
    marginTop: spacing.xxs,
  },
  focusCard: {
    backgroundColor: colors.bg.card,
    borderRadius: radii['2xl'],
    padding: spacing.xl,
    gap: spacing.md,
    marginBottom: spacing.xl,
  },
  focusHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: spacing.md,
  },
  focusTitle: {
    ...typography.subheading,
    color: colors.text.primary,
  },
  focusContent: {
    gap: spacing.xs,
  },
  focusLead: {
    ...typography.title,
    color: colors.primary[700],
  },
  focusSummary: {
    ...typography.body,
    color: colors.text.secondary,
    lineHeight: 20,
  },
  divider: {
    height: 1,
    backgroundColor: colors.border.light,
    marginVertical: spacing.xxs,
  },
  redirectButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.xs,
    paddingVertical: spacing.xs,
  },
  redirectButtonText: {
    ...typography.bodySemibold,
    color: colors.primary[600],
  },
});
