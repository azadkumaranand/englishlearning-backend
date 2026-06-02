import { useMutation, useQuery } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import Animated, { FadeInUp } from 'react-native-reanimated';
import { Feather, Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';

import { EmptyState } from '@/src/components/empty-state';
import { LoadingScreen } from '@/src/components/loading-screen';
import { PrimaryButton } from '@/src/components/primary-button';
import { ScreenContainer } from '@/src/components/screen-container';
import { useAuth } from '@/src/hooks/use-auth';
import { practiceApi } from '@/src/lib/api/practice';
import { progressApi } from '@/src/lib/api/progress';
import { queryClient } from '@/src/lib/query-client';
import { colors, radii, shadows, spacing, typography, fontWeights } from '@/src/theme';

export default function ProgressScreen() {
  const auth = useAuth();
  const router = useRouter();

  const progressQuery = useQuery({
    queryKey: ['progress-dashboard'],
    queryFn: () => auth.authorizedRequest((token) => progressApi.getMine(token)),
  });

  const startTranslationMutation = useMutation({
    mutationFn: () =>
      auth.authorizedRequest((token) =>
        practiceApi.createSession(token, {
          mode: 'translation_practice',
          title: 'Translation Practice',
        })
      ),
    onSuccess: (session) => {
      queryClient.setQueryData(['practice-session', session.id], session);
      router.push(`/(app)/session/${session.id}`);
    },
  });

  const handleRecommendedPractice = () => {
    const type = progressQuery.data?.recommended_next_practice.type;
    if (type === 'mistake_review') {
      router.push('/(app)/mistake-review');
      return;
    }
    if (type === 'roleplay_speaking') {
      router.push('/(app)/conversation-scenarios');
      return;
    }
    startTranslationMutation.mutate();
  };

  if (progressQuery.isLoading || startTranslationMutation.isPending) {
    return <LoadingScreen message="Loading your progress dashboard…" />;
  }

  if (progressQuery.error) {
    return (
      <ScreenContainer>
        <EmptyState
          icon={<Feather name="alert-circle" size={48} color={colors.error} />}
          title="Progress unavailable"
          description="We could not load your progress right now."
        />
        <Pressable style={styles.retryButton} onPress={() => void progressQuery.refetch()}>
          <Text style={styles.retryText}>Retry</Text>
        </Pressable>
      </ScreenContainer>
    );
  }

  const progress = progressQuery.data;
  if (!progress || progress.total_practice_sessions === 0) {
    return (
      <ScreenContainer>
        <EmptyState
          icon={<Feather name="bar-chart-2" size={48} color={colors.primary[500]} />}
          title="Start your first practice to see progress here"
          description="Your scores, streak, and weak-area trends will appear after a few practice activities."
        />
        <View style={styles.emptyStateAction}>
          <PrimaryButton label="Start Translation Practice" onPress={() => startTranslationMutation.mutate()} />
        </View>
      </ScreenContainer>
    );
  }

  return (
    <ScreenContainer scroll>
      {/* Header section */}
      <Animated.View entering={FadeInUp.delay(100).springify()} style={styles.hero}>
        <Text style={styles.heroEyebrow}>Performance</Text>
        <Text style={styles.heroTitle}>Your Progress</Text>
      </Animated.View>

      {/* Main Score featured Card */}
      <Animated.View entering={FadeInUp.delay(150).springify()}>
        <LinearGradient
          colors={colors.gradients.hero}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={[styles.featuredScoreCard, shadows.md]}
        >
          <View style={styles.featuredScoreInfo}>
            <Text style={styles.featuredLabel}>Overall English Proficiency</Text>
            <View style={styles.featuredBadgeRow}>
              <View style={styles.glassBadge}>
                <Text style={styles.glassBadgeText}>Level A2</Text>
              </View>
            </View>
          </View>
          <View style={styles.featuredCircularRing}>
            <View style={styles.ringBackground}>
              <Text style={styles.ringValue}>{progress.overall_score}</Text>
              <Text style={styles.ringLabel}>PTS</Text>
            </View>
          </View>
        </LinearGradient>
      </Animated.View>

      {/* Core Bento Grid */}
      <View style={styles.bentoGrid}>
        {/* Streak Card */}
        <Animated.View style={[styles.bentoCard, styles.streakBentoCard, shadows.sm]} entering={FadeInUp.delay(200).springify()}>
          <View style={styles.streakHeader}>
            <MaterialCommunityIcons name="fire" size={26} color={colors.gold[500]} />
            <Text style={styles.bentoCardTitle}>Learning Streak</Text>
          </View>
          <View style={styles.bentoValueContainer}>
            <Text style={styles.bentoValue}>{progress.streak_days}</Text>
            <Text style={styles.bentoLabel}>days active</Text>
          </View>
        </Animated.View>

        {/* Sessions Completed Card */}
        <Animated.View style={[styles.bentoCard, shadows.sm]} entering={FadeInUp.delay(250).springify()}>
          <View style={styles.bentoHeaderWithIcon}>
            <Feather name="award" size={20} color={colors.primary[600]} />
            <Text style={styles.bentoCardTitle}>Sessions</Text>
          </View>
          <View style={styles.bentoValueContainer}>
            <Text style={styles.bentoValue}>{progress.total_practice_sessions}</Text>
            <Text style={styles.bentoLabel}>completed</Text>
          </View>
          <Text style={styles.bentoHint}>{progress.total_questions_answered} total questions answered</Text>
        </Animated.View>
      </View>

      {/* Skills Proficiency breakdown card */}
      <Animated.View entering={FadeInUp.delay(300).springify()}>
        <View style={[styles.skillsCard, shadows.sm]}>
          <View style={styles.sectionHeader}>
            <Feather name="bar-chart-2" size={20} color={colors.primary[600]} />
            <Text style={styles.sectionTitle}>Skills proficiency</Text>
          </View>

          <View style={styles.progressContainer}>
            {/* Translation Score */}
            <View style={styles.progressItem}>
              <View style={styles.progressLabelRow}>
                <Text style={styles.progressName}>Translation Practice</Text>
                <Text style={styles.progressValue}>{progress.average_translation_score}%</Text>
              </View>
              <View style={styles.progressBarBg}>
                <View style={[styles.progressBarFill, { width: `${progress.average_translation_score}%` }]} />
              </View>
            </View>

            {/* Conversation Score */}
            <View style={styles.progressItem}>
              <View style={styles.progressLabelRow}>
                <Text style={styles.progressName}>Speaking & Dialogue</Text>
                <Text style={styles.progressValue}>{progress.average_conversation_score}%</Text>
              </View>
              <View style={styles.progressBarBg}>
                <View style={[styles.progressBarFill, { width: `${progress.average_conversation_score}%`, backgroundColor: colors.accent[400] }]} />
              </View>
            </View>
          </View>
        </View>
      </Animated.View>

      {/* Weak Areas and Improvements */}
      <View style={styles.insightsSection}>
        <Animated.View style={[styles.detailCard, shadows.sm]} entering={FadeInUp.delay(350).springify()}>
          <View style={styles.sectionHeader}>
            <Feather name="target" size={18} color={colors.error} />
            <Text style={styles.sectionTitle}>Areas to improve</Text>
          </View>
          
          {progress.top_weak_areas.length > 0 ? (
            <View style={styles.weakList}>
              {progress.top_weak_areas.map((area) => (
                <View key={area.type} style={styles.listRow}>
                  <Text style={styles.listLabel}>{area.label}</Text>
                  <View style={styles.countBadge}>
                    <Text style={styles.countBadgeText}>{area.count} mistakes</Text>
                  </View>
                </View>
              ))}
            </View>
          ) : (
            <Text style={styles.cardHint}>No weak areas recorded yet. Excellent job!</Text>
          )}
        </Animated.View>

        <Animated.View style={[styles.detailCard, shadows.sm]} entering={FadeInUp.delay(400).springify()}>
          <View style={styles.sectionHeader}>
            <Feather name="trending-up" size={18} color={colors.success} />
            <Text style={styles.sectionTitle}>Recent improvements</Text>
          </View>
          
          {progress.recent_improvements.length > 0 ? (
            <View style={styles.improvementsList}>
              {progress.recent_improvements.map((item, index) => (
                <View key={`improvement-${index}`} style={styles.improvementRow}>
                  <View style={styles.checkCircle}>
                    <Ionicons name="checkmark" size={12} color={colors.success} />
                  </View>
                  <Text style={styles.improvementText}>{item}</Text>
                </View>
              ))}
            </View>
          ) : (
            <Text style={styles.cardHint}>Complete a few more activities to unlock improvement insights.</Text>
          )}
        </Animated.View>
      </View>

      {/* Recommended CTA Banner */}
      <Animated.View entering={FadeInUp.delay(450).springify()}>
        <LinearGradient
          colors={colors.gradients.accent}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={[styles.recommendedCard, shadows.md]}
        >
          <View style={styles.recommendedHeader}>
            <Ionicons name="sparkles" size={18} color={colors.text.inverse} />
            <Text style={styles.recommendedEyebrow}>RECOMMENDED FOR YOU</Text>
          </View>

          <Text style={styles.recommendedTitle}>{progress.recommended_next_practice.title}</Text>
          <Text style={styles.recommendedStats}>
            Completed roleplays: {progress.total_conversations}
          </Text>

          <View style={styles.recommendedButtonWrapper}>
            <Pressable style={styles.whiteCTAButton} onPress={handleRecommendedPractice}>
              <Text style={styles.whiteCTAText}>Start Practice</Text>
              <Feather name="chevron-right" size={18} color={colors.accent[600]} />
            </Pressable>
          </View>

          {startTranslationMutation.error ? (
            <Text style={styles.errorText}>
              {startTranslationMutation.error instanceof Error
                ? startTranslationMutation.error.message
                : 'Could not start the recommended practice right now.'}
            </Text>
          ) : null}
        </LinearGradient>
      </Animated.View>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  hero: {
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  heroEyebrow: {
    ...typography.eyebrow,
    color: colors.primary[600],
    letterSpacing: 1.5,
  },
  heroTitle: {
    ...typography.title,
    color: colors.text.primary,
  },
  heroDescription: {
    ...typography.bodyLg,
    color: colors.text.secondary,
  },
  retryButton: {
    alignSelf: 'center',
    marginTop: spacing.md,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    borderRadius: radii.full,
    backgroundColor: colors.primary[50],
  },
  retryText: {
    ...typography.bodySemibold,
    color: colors.primary[700],
  },
  emptyStateAction: {
    marginTop: spacing.lg,
    paddingHorizontal: spacing.xl,
  },
  featuredScoreCard: {
    borderRadius: radii['2xl'],
    padding: spacing.xl,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: spacing.lg,
    overflow: 'hidden',
  },
  featuredScoreInfo: {
    flex: 1,
    gap: spacing.xxs,
  },
  featuredLabel: {
    ...typography.bodyLgBold,
    color: colors.text.inverse,
  },
  featuredHint: {
    ...typography.caption,
    color: colors.primary[100],
    marginBottom: spacing.xs,
  },
  featuredBadgeRow: {
    flexDirection: 'row',
  },
  glassBadge: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xxs,
    borderRadius: radii.full,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.3)',
  },
  glassBadgeText: {
    ...typography.captionBold,
    color: colors.text.inverse,
  },
  featuredCircularRing: {
    width: 90,
    height: 90,
    borderRadius: 45,
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 4,
    borderColor: 'rgba(255, 255, 255, 0.3)',
  },
  ringBackground: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  ringValue: {
    fontSize: 28,
    fontWeight: '800',
    color: colors.text.inverse,
    lineHeight: 32,
  },
  ringLabel: {
    fontSize: 10,
    fontWeight: '700',
    color: colors.primary[100],
    letterSpacing: 1,
  },
  bentoGrid: {
    flexDirection: 'row',
    gap: spacing.md,
    marginBottom: spacing.lg,
  },
  bentoCard: {
    flex: 1,
    backgroundColor: colors.bg.card,
    borderRadius: radii.xl,
    padding: spacing.lg,
    gap: spacing.sm,
    justifyContent: 'space-between',
    minHeight: 140,
  },
  streakBentoCard: {
    backgroundColor: colors.bg.card,
    borderLeftWidth: 4,
    borderLeftColor: colors.gold[400],
  },
  bentoHeaderWithIcon: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  streakHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  bentoCardTitle: {
    ...typography.bodySemibold,
    color: colors.text.secondary,
  },
  bentoValueContainer: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: spacing.xxs,
  },
  bentoValue: {
    fontSize: 34,
    fontWeight: '800',
    color: colors.text.primary,
  },
  bentoLabel: {
    ...typography.captionBold,
    color: colors.text.tertiary,
  },
  bentoHint: {
    ...typography.caption,
    color: colors.text.tertiary,
    lineHeight: 14,
  },
  skillsCard: {
    backgroundColor: colors.bg.card,
    borderRadius: radii.xl,
    padding: spacing.xl,
    gap: spacing.lg,
    marginBottom: spacing.lg,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginBottom: spacing.xs,
  },
  sectionTitle: {
    ...typography.subheading,
    color: colors.text.primary,
  },
  progressContainer: {
    gap: spacing.md,
  },
  progressItem: {
    gap: spacing.xs,
  },
  progressLabelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  progressName: {
    ...typography.bodyMedium,
    color: colors.text.primary,
  },
  progressValue: {
    ...typography.bodyMedium,
    fontWeight: fontWeights.bold,
    color: colors.primary[700],
  },
  progressBarBg: {
    height: 8,
    borderRadius: radii.full,
    backgroundColor: colors.neutral[100],
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    borderRadius: radii.full,
    backgroundColor: colors.primary[500],
  },
  insightsSection: {
    gap: spacing.lg,
    marginBottom: spacing.lg,
  },
  detailCard: {
    backgroundColor: colors.bg.card,
    borderRadius: radii.xl,
    padding: spacing.xl,
    gap: spacing.md,
  },
  cardHint: {
    ...typography.body,
    color: colors.text.secondary,
    fontStyle: 'italic',
  },
  weakList: {
    gap: spacing.sm,
  },
  listRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.xxs,
  },
  listLabel: {
    ...typography.bodyMedium,
    color: colors.text.primary,
    flex: 1,
  },
  countBadge: {
    backgroundColor: colors.error + '15',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xxs,
    borderRadius: radii.full,
  },
  countBadgeText: {
    ...typography.captionBold,
    color: colors.error,
  },
  improvementsList: {
    gap: spacing.sm,
  },
  improvementRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    alignItems: 'center',
  },
  checkCircle: {
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: colors.success + '15',
    alignItems: 'center',
    justifyContent: 'center',
  },
  improvementText: {
    ...typography.body,
    color: colors.text.primary,
    flex: 1,
  },
  recommendedCard: {
    borderRadius: radii['2xl'],
    padding: spacing.xl,
    gap: spacing.md,
    marginBottom: spacing.xl,
  },
  recommendedHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  recommendedEyebrow: {
    ...typography.eyebrow,
    color: colors.text.inverse,
    opacity: 0.85,
    letterSpacing: 2,
  },
  recommendedTitle: {
    ...typography.subheading,
    color: colors.text.inverse,
  },
  recommendedStats: {
    ...typography.captionBold,
    color: colors.accent[100],
    marginBottom: spacing.xs,
  },
  recommendedButtonWrapper: {
    flexDirection: 'row',
  },
  whiteCTAButton: {
    backgroundColor: colors.neutral[0],
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md,
    borderRadius: radii.lg,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  whiteCTAText: {
    ...typography.bodyMedium,
    fontWeight: fontWeights.bold,
    color: colors.accent[600],
  },
  errorText: {
    ...typography.body,
    color: colors.text.inverse,
    marginTop: spacing.xs,
  },
});
