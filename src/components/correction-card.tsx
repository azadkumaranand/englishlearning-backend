import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';

import type { MessageCorrection } from '@/src/lib/api/types';
import { colors, radii, shadows, spacing, typography } from '@/src/theme';

const statusConfig = {
  correct: {
    label: 'Perfect',
    accent: colors.success,
    background: '#ECFDF5',
  },
  almost: {
    label: 'Imperfect',
    accent: colors.primary[700],
    background: colors.primary[50],
  },
  needs_practice: {
    label: 'Needs Practice',
    accent: colors.error,
    background: '#FEF2F2',
  },
} as const;

function getStatusConfig(status: MessageCorrection['status']) {
  return statusConfig[status] ?? statusConfig.almost;
}

export function CorrectionCard({
  correction,
}: {
  correction: MessageCorrection;
  onReply?: unknown;
  onTryAgain?: unknown;
  onGoNext?: unknown;
}) {
  const [expanded, setExpanded] = useState(false);
  const status = getStatusConfig(correction.status);
  const bestAnswer = correction.best_answer || correction.correct_answer || correction.natural_answer;
  const examples = correction.practice_examples.slice(0, 2);

  return (
    <Animated.View entering={FadeInDown.delay(100).duration(250)} style={[styles.card, shadows.sm]}>
      <View style={styles.headerRow}>
        <Text style={styles.scoreValue}>{correction.score}</Text>
        <View style={[styles.statusPill, { backgroundColor: status.background }]}>
          <Text style={[styles.statusText, { color: status.accent }]}>{status.label}</Text>
        </View>
      </View>

      <View style={[styles.panel, styles.answerPanel]}>
        <Text style={styles.sectionLabel}>Correct Answer</Text>
        <Text style={styles.answerText}>{bestAnswer}</Text>
      </View>

      {examples.length > 0 ? (
        <View style={[styles.panel, styles.examplesPanel]}>
          <Text style={styles.sectionLabel}>Two More Examples</Text>
          {examples.map((example, index) => (
            <View key={`${example.native}-${example.english}-${index}`} style={styles.exampleCard}>
              <Text style={styles.exampleNative}>{example.native}</Text>
              <Text style={styles.exampleEnglish}>{example.english}</Text>
            </View>
          ))}
        </View>
      ) : null}

      <Pressable onPress={() => setExpanded((value) => !value)} style={styles.showMoreButton}>
        <Text style={styles.showMoreText}>{expanded ? 'Show less' : 'Show more'}</Text>
      </Pressable>

      {expanded ? (
        <View style={styles.breakdownPanel}>
          <View style={styles.breakdownHeader}>
            <Text style={styles.breakdownTitle}>Grammar Breakdown</Text>
          </View>

          <View style={[styles.breakdownBlock, styles.breakdownCard]}>
            <Text style={styles.blockLabel}>Tense / Pattern</Text>
            <Text style={styles.blockValue}>{correction.tense_explanation.tense_or_pattern}</Text>
          </View>

          <View style={[styles.breakdownBlock, styles.breakdownCard]}>
            <Text style={styles.blockLabel}>Structure</Text>
            <Text style={[styles.blockValue, styles.monoValue]}>{correction.tense_explanation.structure}</Text>
          </View>

          <View style={[styles.breakdownBlock, styles.breakdownCard]}>
            <Text style={styles.blockLabel}>When To Use This Form</Text>
            <Text style={[styles.blockValue, styles.relaxedLineHeight]}>{correction.tense_explanation.why_this_pattern}</Text>
          </View>

          {correction.tense_explanation.native_to_english_mapping.length > 0 ? (
            <View style={[styles.breakdownBlock, styles.breakdownCard, styles.mappingCard]}>
              <Text style={styles.blockLabel}>Hindi To English</Text>
              {correction.tense_explanation.native_to_english_mapping.map((item, index) => (
                <View
                  key={`${item.native_part}-${item.english_part}-${index}`}
                  style={[
                    styles.mappingRow,
                    index > 0 && styles.mappingRowSeparator,
                  ]}
                >
                  <View style={styles.mappingMainRow}>
                    <Text style={styles.mappingNative}>{item.native_part}</Text>
                    <View style={styles.mappingArrowContainer}>
                      <Text style={styles.mappingArrow}>→</Text>
                    </View>
                    <Text style={styles.mappingEnglish}>{item.english_part}</Text>
                  </View>
                  <Text style={styles.mappingRole}>{item.role}</Text>
                </View>
              ))}
            </View>
          ) : null}

          {correction.user_mistake.is_wrong ? (
            <View style={[styles.breakdownBlock, styles.breakdownCard, styles.mistakeCard]}>
              <Text style={styles.blockLabel}>What Changed</Text>
              <View style={styles.mistakeRow}>
                <View style={[styles.mistakeBadge, styles.wrongBadge]}>
                  <Text style={styles.mistakeBadgeText}>Wrong</Text>
                </View>
                <Text style={styles.mistakeText}>{correction.user_mistake.wrong_part}</Text>
              </View>
              <View style={styles.mistakeArrow}>
                <Text style={styles.mistakeArrowText}>↓</Text>
              </View>
              <View style={styles.mistakeRow}>
                <View style={[styles.mistakeBadge, styles.correctBadge]}>
                  <Text style={styles.mistakeBadgeText}>Correct</Text>
                </View>
                <Text style={[styles.mistakeText, styles.correctText]}>{correction.user_mistake.replace_with}</Text>
              </View>
              <View style={styles.reasonContainer}>
                <Text style={styles.helpText}>{correction.user_mistake.reason}</Text>
              </View>
            </View>
          ) : null}

          <View style={[styles.breakdownBlock, styles.breakdownCard, styles.tipCard]}>
            <Text style={styles.blockLabel}>Next Time Remember</Text>
            <Text style={[styles.blockValue, styles.tipText]}>{correction.translation_tip || correction.key_learning}</Text>
          </View>
        </View>
      ) : null}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.bg.card,
    borderRadius: radii.xl,
    borderWidth: 1,
    borderColor: colors.border.light,
    padding: spacing.lg,
    gap: spacing.md,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.sm,
  },
  scoreValue: {
    ...typography.display,
    color: colors.text.primary,
  },
  statusPill: {
    borderRadius: radii.full,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
  },
  statusText: {
    ...typography.captionBold,
  },
  panel: {
    borderRadius: radii.lg,
    padding: spacing.md,
    gap: spacing.sm,
  },
  answerPanel: {
    backgroundColor: '#ECFDF5',
  },
  breakdownPanel: {
    backgroundColor: '#F1F5F9',
    borderRadius: radii.lg,
    padding: spacing.md,
    gap: spacing.sm,
  },
  breakdownHeader: {
    paddingBottom: spacing.xs,
    marginBottom: spacing.xxs,
    borderBottomWidth: 1,
    borderBottomColor: colors.border.light,
  },
  breakdownTitle: {
    ...typography.captionBold,
    color: colors.text.tertiary,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  breakdownBlock: {
    gap: spacing.xs,
  },
  breakdownCard: {
    backgroundColor: colors.bg.card,
    borderRadius: radii.md,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  mappingCard: {
    backgroundColor: '#FAFBFC',
  },
  mistakeCard: {
    backgroundColor: '#FFFBEB',
    borderColor: '#FDE68A',
  },
  tipCard: {
    backgroundColor: '#ECFDF5',
    borderColor: '#A7F3D0',
  },
  monoValue: {
    fontFamily: 'monospace',
    fontSize: 14,
  },
  relaxedLineHeight: {
    lineHeight: 22,
  },
  examplesPanel: {
    backgroundColor: '#FFF7ED',
  },
  sectionLabel: {
    ...typography.captionBold,
    color: colors.text.tertiary,
    textTransform: 'uppercase',
  },
  answerText: {
    ...typography.bodyLgBold,
    color: colors.success,
  },
  blockLabel: {
    ...typography.captionBold,
    color: colors.primary[700],
    marginBottom: spacing.xxs,
  },
  blockValue: {
    ...typography.body,
    color: colors.text.primary,
    lineHeight: 20,
  },
  helpText: {
    ...typography.body,
    color: colors.text.secondary,
    lineHeight: 20,
  },
  mistakeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    paddingVertical: spacing.xxs,
  },
  mistakeBadge: {
    borderRadius: radii.full,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xxs,
  },
  wrongBadge: {
    backgroundColor: '#FEE2E2',
  },
  correctBadge: {
    backgroundColor: '#D1FAE5',
  },
  mistakeBadgeText: {
    ...typography.captionBold,
    fontSize: 11,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  mistakeText: {
    ...typography.body,
    color: '#DC2626',
    flex: 1,
  },
  correctText: {
    color: '#059669',
  },
  mistakeArrow: {
    paddingLeft: spacing.lg,
    paddingVertical: spacing.xxs,
  },
  mistakeArrowText: {
    ...typography.body,
    color: colors.text.tertiary,
  },
  reasonContainer: {
    marginTop: spacing.xs,
    paddingTop: spacing.xs,
    borderTopWidth: 1,
    borderTopColor: '#FDE68A',
  },
  tipText: {
    ...typography.bodySemibold,
  },
  mappingRow: {
    gap: spacing.xxs,
    paddingVertical: spacing.xs,
  },
  mappingRowSeparator: {
    borderTopWidth: 1,
    borderTopColor: colors.border.light,
    marginTop: spacing.xs,
    paddingTop: spacing.sm,
  },
  mappingMainRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  mappingNative: {
    ...typography.bodySemibold,
    color: colors.text.primary,
    flex: 1,
  },
  mappingArrowContainer: {
    paddingHorizontal: spacing.xxs,
  },
  mappingArrow: {
    ...typography.captionBold,
    color: colors.primary[600],
    fontSize: 16,
  },
  mappingEnglish: {
    ...typography.bodySemibold,
    color: colors.success,
    flex: 1,
  },
  mappingRole: {
    ...typography.caption,
    color: colors.text.secondary,
    fontStyle: 'italic',
    paddingLeft: spacing.xs,
  },
  exampleCard: {
    backgroundColor: colors.bg.card,
    borderRadius: radii.lg,
    padding: spacing.md,
    gap: spacing.xs,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  exampleNative: {
    ...typography.bodySemibold,
    color: colors.text.primary,
  },
  exampleEnglish: {
    ...typography.body,
    color: colors.text.secondary,
  },
  showMoreButton: {
    alignSelf: 'flex-start',
  },
  showMoreText: {
    ...typography.captionBold,
    color: colors.primary[700],
  },
});
