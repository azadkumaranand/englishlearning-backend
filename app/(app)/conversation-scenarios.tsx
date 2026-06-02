import { useMutation } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import Animated, { FadeInUp } from 'react-native-reanimated';
import { Feather } from '@expo/vector-icons';

import { EmptyState } from '@/src/components/empty-state';
import { LoadingScreen } from '@/src/components/loading-screen';
import { ScreenContainer } from '@/src/components/screen-container';
import { useAuth } from '@/src/hooks/use-auth';
import { conversationApi } from '@/src/lib/api/conversation';
import type { ConversationScenario } from '@/src/lib/api/types';
import { conversationScenarios } from '@/src/lib/conversation';
import { colors, radii, shadows, spacing, typography } from '@/src/theme';

const SCENARIO_DETAILS: Record<string, { iconName: any; color: string; tag: string }> = {
  job_interview: { iconName: 'briefcase', color: colors.primary[500], tag: 'Professional' },
  client_meeting: { iconName: 'users', color: colors.accent[500], tag: 'Workplace' },
  daily_conversation: { iconName: 'message-circle', color: colors.gold[500], tag: 'Everyday' },
  ordering_food: { iconName: 'coffee', color: '#f97316', tag: 'Social' },
  travel_airport: { iconName: 'globe', color: '#3b82f6', tag: 'Travel' },
  introduce_yourself: { iconName: 'user', color: '#ec4899', tag: 'Basics' },
  confidence_practice: { iconName: 'zap', color: '#8b5cf6', tag: 'Fluency' },
};

export default function ConversationScenarioScreen() {
  const auth = useAuth();
  const router = useRouter();

  const startConversationMutation = useMutation({
    mutationFn: (scenario: ConversationScenario) =>
      auth.authorizedRequest((token) => conversationApi.start(token, { scenario })),
    onSuccess: (response) => {
      router.push({
        pathname: '/(app)/conversation/[id]',
        params: {
          id: response.session_id,
          scenario: response.scenario,
          title: response.title,
          aiMessage: response.ai_message,
          goal: response.goal,
          level: response.level,
          maxTurns: String(response.max_turns),
        },
      });
    },
  });

  if (startConversationMutation.isPending) {
    return <LoadingScreen message="Starting your roleplay practice…" />;
  }

  return (
    <ScreenContainer scroll edges={['right', 'left', 'bottom']}>

      {startConversationMutation.error ? (
        <EmptyState
          icon={<Feather name="alert-triangle" size={44} color={colors.error} />}
          title="Could not start practice"
          description={
            startConversationMutation.error instanceof Error
              ? startConversationMutation.error.message
              : 'Please try again.'
          }
        />
      ) : null}

      <View style={styles.cardList}>
        {conversationScenarios.map((scenario, index) => {
          const details = SCENARIO_DETAILS[scenario.id] || {
            iconName: 'message-square',
            color: colors.primary[500],
            tag: 'Practice',
          };
          
          return (
            <Animated.View
              key={scenario.id}
              entering={FadeInUp.delay(150 + index * 50).springify()}
            >
              <Pressable
                onPress={() => startConversationMutation.mutate(scenario.id)}
                style={({ pressed }) => [
                  styles.card,
                  shadows.sm,
                  pressed && styles.cardPressed,
                ]}
              >
                <View style={styles.cardLayout}>
                  {/* Styled Icon Container */}
                  <View style={[styles.iconContainer, { backgroundColor: details.color + '15' }]}>
                    <Feather name={details.iconName} size={22} color={details.color} />
                  </View>

                  {/* Text Details */}
                  <View style={styles.textContainer}>
                    <View style={styles.cardHeaderRow}>
                      <Text style={styles.cardTitle}>{scenario.title}</Text>
                      <View style={[styles.tagPill, { backgroundColor: details.color + '10' }]}>
                        <Text style={[styles.tagText, { color: details.color }]}>
                          {details.tag}
                        </Text>
                      </View>
                    </View>
                    <Text style={styles.cardDescription}>{scenario.description}</Text>
                  </View>

                  {/* Interactive Chevron Arrow */}
                  <View style={styles.chevronContainer}>
                    <Feather name="chevron-right" size={20} color={colors.text.tertiary} />
                  </View>
                </View>
              </Pressable>
            </Animated.View>
          );
        })}
      </View>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  cardList: {
    gap: spacing.md,
    marginBottom: spacing.xl,
  },
  card: {
    backgroundColor: colors.bg.card,
    borderRadius: radii.xl,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  cardPressed: {
    transform: [{ scale: 0.98 }],
    borderColor: colors.primary[200],
    backgroundColor: colors.primary[50] + '10',
  },
  cardLayout: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  iconContainer: {
    width: 48,
    height: 48,
    borderRadius: radii.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  textContainer: {
    flex: 1,
    gap: spacing.xxs,
  },
  cardHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.xs,
  },
  cardTitle: {
    ...typography.bodyLgBold,
    color: colors.text.primary,
  },
  tagPill: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: radii.full,
  },
  tagText: {
    fontSize: 10,
    fontWeight: '700',
    textTransform: 'uppercase',
  },
  cardDescription: {
    ...typography.body,
    color: colors.text.secondary,
    lineHeight: 18,
  },
  chevronContainer: {
    justifyContent: 'center',
    alignItems: 'center',
    paddingLeft: spacing.xs,
  },
});
