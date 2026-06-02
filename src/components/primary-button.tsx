import { useCallback } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
} from 'react-native-reanimated';

import { colors, radii, shadows, spacing, typography } from '@/src/theme';

type PrimaryButtonProps = {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  loading?: boolean;
  variant?: 'primary' | 'secondary' | 'danger';
  icon?: string | React.ReactNode;
};

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

export function PrimaryButton({
  label,
  onPress,
  disabled = false,
  loading = false,
  variant = 'primary',
  icon,
}: PrimaryButtonProps) {
  const scale = useSharedValue(1);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  const handlePressIn = useCallback(() => {
    scale.value = withSpring(0.96, { damping: 15, stiffness: 400 });
  }, [scale]);

  const handlePressOut = useCallback(() => {
    scale.value = withSpring(1, { damping: 12, stiffness: 300 });
  }, [scale]);

  const isPrimary = variant === 'primary';
  const isDanger = variant === 'danger';
  const isInteractive = !disabled && !loading;

  return (
    <AnimatedPressable
      accessibilityRole="button"
      disabled={!isInteractive}
      onPress={onPress}
      onPressIn={handlePressIn}
      onPressOut={handlePressOut}
      style={[
        animatedStyle,
        styles.button,
        isPrimary && styles.primaryButton,
        isDanger && styles.dangerButton,
        !isPrimary && !isDanger && styles.secondaryButton,
        !isInteractive && styles.disabledButton,
      ]}>
      {loading ? (
        <ActivityIndicator color={isPrimary || isDanger ? colors.text.inverse : colors.text.primary} />
      ) : (
        <View style={styles.inner}>
          {icon ? (
            typeof icon === 'string' ? (
              <Text style={styles.icon}>{icon}</Text>
            ) : (
              icon
            )
          ) : null}
          <Text
            style={[
              styles.label,
              isPrimary && styles.primaryLabel,
              isDanger && styles.dangerLabel,
              !isPrimary && !isDanger && styles.secondaryLabel,
            ]}>
            {label}
          </Text>
        </View>
      )}
    </AnimatedPressable>
  );
}

const styles = StyleSheet.create({
  button: {
    minHeight: 54,
    borderRadius: radii.lg,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing['2xl'],
    ...shadows.sm,
  },
  primaryButton: {
    backgroundColor: colors.primary[500],
    shadowColor: colors.primary[500],
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  secondaryButton: {
    backgroundColor: colors.primary[50],
    borderWidth: 1.5,
    borderColor: colors.primary[200],
    shadowOpacity: 0,
    elevation: 0,
  },
  dangerButton: {
    backgroundColor: colors.error,
  },
  disabledButton: {
    opacity: 0.5,
    shadowOpacity: 0,
    elevation: 0,
  },
  inner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  icon: {
    fontSize: 18,
  },
  label: {
    ...typography.bodyLgBold,
  },
  primaryLabel: {
    color: colors.text.inverse,
  },
  secondaryLabel: {
    color: colors.primary[700],
  },
  dangerLabel: {
    color: colors.text.inverse,
  },
});
