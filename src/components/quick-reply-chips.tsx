import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radii, spacing, typography } from '@/src/theme';

export function QuickReplyChips({
  replies,
  onPress,
  disabled = false,
}: {
  replies: string[];
  onPress: (reply: string) => void;
  disabled?: boolean;
}) {
  if (!replies.length) {
    return null;
  }

  return (
    <View style={styles.container}>
      {replies.map((reply) => (
        <Pressable
          key={reply}
          disabled={disabled}
          onPress={() => onPress(reply)}
          style={({ pressed }) => [
            styles.chip,
            disabled && styles.chipDisabled,
            pressed && !disabled && styles.chipPressed,
          ]}>
          <Text style={styles.chipText}>{reply}</Text>
        </Pressable>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    marginTop: spacing.sm,
  },
  chip: {
    backgroundColor: colors.primary[50],
    borderColor: colors.primary[100],
    borderRadius: radii.full,
    borderWidth: 1,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  chipPressed: {
    opacity: 0.8,
    transform: [{ scale: 0.98 }],
  },
  chipDisabled: {
    opacity: 0.5,
  },
  chipText: {
    ...typography.body,
    color: colors.primary[700],
  },
});
