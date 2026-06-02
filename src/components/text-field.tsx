import { useCallback, useState } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  interpolateColor,
} from 'react-native-reanimated';

import { colors, radii, shadows, spacing, typography } from '@/src/theme';

const AnimatedView = Animated.createAnimatedComponent(View);

type TextFieldProps = {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  placeholder?: string;
  secureTextEntry?: boolean;
  multiline?: boolean;
  keyboardType?: 'default' | 'email-address' | 'numeric';
  autoCapitalize?: 'none' | 'sentences' | 'words';
};

export function TextField({
  label,
  value,
  onChangeText,
  placeholder,
  secureTextEntry = false,
  multiline = false,
  keyboardType = 'default',
  autoCapitalize = 'sentences',
}: TextFieldProps) {
  const focusProgress = useSharedValue(0);
  const [isFocused, setIsFocused] = useState(false);

  const handleFocus = useCallback(() => {
    setIsFocused(true);
    focusProgress.value = withTiming(1, { duration: 200 });
  }, [focusProgress]);

  const handleBlur = useCallback(() => {
    setIsFocused(false);
    focusProgress.value = withTiming(0, { duration: 200 });
  }, [focusProgress]);

  const animatedBorderStyle = useAnimatedStyle(() => ({
    borderColor: interpolateColor(
      focusProgress.value,
      [0, 1],
      [colors.border.light, colors.primary[500]]
    ),
    borderWidth: 1.5 + focusProgress.value * 0.5,
  }));

  return (
    <View style={styles.container}>
      <Text style={[styles.label, isFocused && styles.labelFocused]}>{label}</Text>
      <AnimatedView style={[styles.inputWrapper, animatedBorderStyle, isFocused && shadows.sm]}>
        <TextInput
          autoCapitalize={autoCapitalize}
          keyboardType={keyboardType}
          multiline={multiline}
          onChangeText={onChangeText}
          onFocus={handleFocus}
          onBlur={handleBlur}
          placeholder={placeholder}
          placeholderTextColor={colors.text.tertiary}
          secureTextEntry={secureTextEntry}
          style={[styles.input, multiline && styles.multiline]}
          value={value}
        />
      </AnimatedView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: spacing.sm,
  },
  label: {
    ...typography.bodySemibold,
    color: colors.text.secondary,
  },
  labelFocused: {
    color: colors.primary[600],
  },
  inputWrapper: {
    backgroundColor: colors.bg.card,
    borderRadius: radii.md,
    borderWidth: 1.5,
    borderColor: colors.border.light,
    overflow: 'hidden',
  },
  input: {
    color: colors.text.primary,
    fontSize: 16,
    minHeight: 52,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  multiline: {
    minHeight: 110,
    textAlignVertical: 'top',
  },
});
