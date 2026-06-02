import { useMutation, useQuery } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import Animated, { FadeInUp } from 'react-native-reanimated';
import { Feather, Ionicons } from '@expo/vector-icons';

import { LoadingScreen } from '@/src/components/loading-screen';
import { ScreenContainer } from '@/src/components/screen-container';
import { useAuth } from '@/src/hooks/use-auth';
import { learningProfileApi } from '@/src/lib/api/learning-profile';
import { mistakesApi } from '@/src/lib/api/mistakes';
import { practiceApi } from '@/src/lib/api/practice';
import { queryClient } from '@/src/lib/query-client';
import { formatLearningAreaLabel } from '@/src/lib/learning-profile';
import { colors, radii, shadows, spacing, typography } from '@/src/theme';

function ModeCard({
  title,
  description,
  icon,
  active = false,
  onPress,
  badge,
}: {
  title: string;
  description: string;
  icon: React.ReactNode;
  active?: boolean;
  onPress?: () => void;
  badge?: string;
}) {
  return (
    <Pressable
      disabled={!active || !onPress}
      onPress={onPress}
      style={({ pressed }) => [
        styles.modeCard,
        shadows.sm,
        active ? styles.modeCardActive : styles.modeCardDisabled,
        pressed && active && styles.modeCardPressed,
      ]}>
      <View style={styles.modeMainRow}>
        <View style={[styles.iconContainer, active ? styles.iconContainerActive : styles.iconContainerDisabled]}>
          {icon}
        </View>
        <View style={styles.modeContent}>
          <View style={styles.modeHeaderRow}>
            <Text style={styles.modeTitle}>{title}</Text>
            {badge || !active ? (
              <View style={[styles.badge, active ? styles.badgeActive : styles.badgeDisabled]}>
                <Text style={[styles.badgeText, active ? styles.badgeTextActive : styles.badgeTextDisabled]}>
                  {badge ?? 'Coming soon'}
                </Text>
              </View>
            ) : null}
          </View>
          <Text style={styles.modeDescription}>{description}</Text>
          {active && (
            <View style={styles.actionRow}>
              <Text style={styles.modeAction}>Start practice</Text>
              <Feather name="arrow-right" size={14} color={colors.primary[600]} />
            </View>
          )}
        </View>
      </View>
    </Pressable>
  );
}

export default function PracticeScreen() {
  const auth = useAuth();
  const router = useRouter();

  const learningProfileQuery = useQuery({
    queryKey: ['learning-profile'],
    queryFn: () => auth.authorizedRequest((token) => learningProfileApi.getMine(token)),
  });

  const reviewMistakesQuery = useQuery({
    queryKey: ['mistakes-review', 'practice'],
    queryFn: () => auth.authorizedRequest((token) => mistakesApi.getReview(token)),
  });

  const createTranslationSessionMutation = useMutation({
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

  if (createTranslationSessionMutation.isPending || learningProfileQuery.isLoading || reviewMistakesQuery.isLoading) {
    return <LoadingScreen message="Preparing practice options…" />;
  }

  const recommendedFocus = learningProfileQuery.data?.recommended_focus_area
    ? formatLearningAreaLabel(learningProfileQuery.data.recommended_focus_area)
    : 'Translation';
  const reviewCount = reviewMistakesQuery.data?.mistakes.length ?? 0;

  return (
    <ScreenContainer scroll>
      <Animated.View entering={FadeInUp.delay(100).springify()} style={styles.hero}>
        <Text style={styles.heroEyebrow}>Daily training</Text>
        <Text style={styles.heroTitle}>Practice Modes</Text>
      </Animated.View>

      <Animated.View entering={FadeInUp.delay(150).springify()}>
        <LinearGradient
          colors={colors.gradients.primary}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={[styles.recommendationCard, shadows.md]}
        >
          <View style={styles.recommendationHeader}>
            <Ionicons name="sparkles" size={16} color={colors.text.inverse} />
            <Text style={styles.recommendationEyebrow}>RECOMMENDED WORKOUT</Text>
          </View>
          <Text style={styles.recommendationTitle}>{recommendedFocus} Practice</Text>
          <Text style={styles.recommendationBody}>
            {learningProfileQuery.data?.summary ??
              'Complete a translation practice session to get a personalized daily focus.'}
          </Text>
          {learningProfileQuery.error ? (
            <Pressable onPress={() => void learningProfileQuery.refetch()}>
              <Text style={styles.recommendationRetry}>Retry loading profile</Text>
            </Pressable>
          ) : null}
        </LinearGradient>
      </Animated.View>

      <View style={styles.modeList}>
        <Animated.View entering={FadeInUp.delay(200).springify()}>
          <ModeCard
            title="Translation Practice"
            description="Strengthen English sentence structures through writing and instant AI fixes."
            icon={<Feather name="edit-3" size={22} color={colors.primary[600]} />}
            active
            onPress={() => createTranslationSessionMutation.mutate()}
          />
        </Animated.View>

        <Animated.View entering={FadeInUp.delay(250).springify()}>
          <ModeCard
            title="Mistake Review"
            description={
              reviewCount > 0
                ? `Redo your ${reviewCount} recent mistake${reviewCount > 1 ? 's' : ''} to build complete grammar confidence.`
                : 'No mistakes to review yet. Finish a translation activity first.'
            }
            icon={<Feather name="refresh-cw" size={20} color={reviewCount > 0 ? colors.accent[500] : colors.neutral[400]} />}
            active={reviewCount > 0}
            badge={reviewCount > 0 ? `${reviewCount} pending` : undefined}
            onPress={() => router.push('/(app)/mistake-review')}
          />
        </Animated.View>

        <Animated.View entering={FadeInUp.delay(300).springify()}>
          <ModeCard
            title="Roleplay Speaking"
            description="Have real-life conversational dialogues with an adaptive AI tutor."
            icon={<Ionicons name="chatbubble-ellipses-outline" size={22} color={colors.primary[600]} />}
            active
            badge="Voice enabled"
            onPress={() => router.push('/(app)/conversation-scenarios')}
          />
        </Animated.View>

        <Animated.View entering={FadeInUp.delay(350).springify()}>
          <ModeCard
            title="Pronunciation Practice"
            description="Improve your spoken accent and listening clarity with pronunciation training."
            icon={<Feather name="mic" size={22} color={colors.neutral[400]} />}
          />
        </Animated.View>
      </View>

      {createTranslationSessionMutation.error ? (
        <Text style={styles.errorText}>
          ⚠️ {createTranslationSessionMutation.error instanceof Error
            ? createTranslationSessionMutation.error.message
            : 'Unable to start translation practice'}
        </Text>
      ) : null}
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
  recommendationCard: {
    borderRadius: radii['2xl'],
    padding: spacing.xl,
    gap: spacing.sm,
    marginBottom: spacing.lg,
  },
  recommendationHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  recommendationEyebrow: {
    ...typography.eyebrow,
    color: colors.text.inverse,
    opacity: 0.85,
    letterSpacing: 1.5,
  },
  recommendationTitle: {
    ...typography.subheading,
    color: colors.text.inverse,
  },
  recommendationBody: {
    ...typography.body,
    color: colors.primary[50],
    lineHeight: 20,
  },
  recommendationRetry: {
    ...typography.captionBold,
    color: colors.text.inverse,
    textDecorationLine: 'underline',
    marginTop: spacing.xs,
  },
  modeList: {
    gap: spacing.md,
    marginBottom: spacing.xl,
  },
  modeCard: {
    borderRadius: radii.xl,
    padding: spacing.lg,
    backgroundColor: colors.bg.card,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  modeCardActive: {
    borderColor: colors.border.light,
  },
  modeCardDisabled: {
    opacity: 0.65,
    backgroundColor: colors.neutral[50],
  },
  modeCardPressed: {
    backgroundColor: colors.neutral[50],
    transform: [{ scale: 0.99 }],
  },
  modeMainRow: {
    flexDirection: 'row',
    gap: spacing.md,
    alignItems: 'flex-start',
  },
  iconContainer: {
    width: 44,
    height: 44,
    borderRadius: radii.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconContainerActive: {
    backgroundColor: colors.primary[50],
  },
  iconContainerDisabled: {
    backgroundColor: colors.neutral[150],
  },
  modeContent: {
    flex: 1,
    gap: spacing.xxs,
  },
  modeHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: spacing.xs,
  },
  modeTitle: {
    ...typography.bodyLgSemibold,
    color: colors.text.primary,
  },
  badge: {
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xxs,
    borderRadius: radii.full,
  },
  badgeActive: {
    backgroundColor: colors.accent[50],
  },
  badgeDisabled: {
    backgroundColor: colors.neutral[200],
  },
  badgeText: {
    ...typography.captionBold,
    fontSize: 10,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  badgeTextActive: {
    color: colors.accent[600],
  },
  badgeTextDisabled: {
    color: colors.text.secondary,
  },
  modeDescription: {
    ...typography.body,
    color: colors.text.secondary,
    lineHeight: 18,
  },
  actionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xxs,
    marginTop: spacing.xs,
  },
  modeAction: {
    ...typography.captionBold,
    color: colors.primary[600],
  },
  errorText: {
    ...typography.bodyMedium,
    color: colors.error,
    textAlign: 'center',
    marginTop: spacing.md,
  },
});
