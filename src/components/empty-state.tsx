import type { ReactNode } from 'react';
import { StyleSheet, Text } from 'react-native';
import Animated, { FadeIn, FadeInDown } from 'react-native-reanimated';

import { colors, radii, shadows, spacing, typography } from '@/src/theme';

type EmptyStateProps = {
  title: string;
  description: string;
  icon?: ReactNode;
};

export function EmptyState({ title, description, icon = '📭' }: EmptyStateProps) {
  return (
    <Animated.View entering={FadeIn.duration(500)} style={[styles.container, shadows.sm]}>
      {typeof icon === 'string' ? (
        <Animated.Text entering={FadeInDown.delay(100).duration(400)} style={styles.icon}>
          {icon}
        </Animated.Text>
      ) : (
        <Animated.View entering={FadeInDown.delay(100).duration(400)} style={styles.iconContainer}>
          {icon}
        </Animated.View>
      )}
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.description}>{description}</Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    backgroundColor: colors.bg.subtle,
    borderColor: colors.border.light,
    borderRadius: radii.xl,
    borderWidth: 1,
    gap: spacing.sm,
    paddingVertical: spacing['3xl'],
    paddingHorizontal: spacing['2xl'],
  },
  icon: {
    fontSize: 42,
    marginBottom: spacing.xs,
  },
  iconContainer: {
    marginBottom: spacing.xs,
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    ...typography.subheading,
    color: colors.text.primary,
    textAlign: 'center',
  },
  description: {
    ...typography.body,
    color: colors.text.secondary,
    textAlign: 'center',
    maxWidth: 260,
  },
});
