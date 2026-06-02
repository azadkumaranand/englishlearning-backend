import { Pressable, StyleSheet, Text, View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';

import type { MessageReplyContext, PracticeMessage } from '@/src/lib/api/types';
import { colors, radii, shadows, spacing, typography } from '@/src/theme';

function readTranslationSourceSentence(message: PracticeMessage): string | null {
  const metadata = message.metadata_json;
  if (!metadata || metadata.practice_kind !== 'translation_prompt') {
    return null;
  }

  const sourceSentence = metadata.translation_source_sentence;
  return typeof sourceSentence === 'string' && sourceSentence.trim().length > 0
    ? sourceSentence.trim()
    : null;
}

export function ChatBubble({
  message,
  onReply,
  onPlayAudio,
  onContinueLearning,
  isSpeaking = false,
}: {
  message: PracticeMessage;
  onReply?: (replyContext: MessageReplyContext) => void;
  onPlayAudio?: (message: PracticeMessage) => void;
  onContinueLearning?: (message: PracticeMessage) => void;
  isSpeaking?: boolean;
}) {
  const isUser = message.role === 'user';
  const metadata = message.metadata_json;
  const translationSourceSentence = !isUser ? readTranslationSourceSentence(message) : null;
  const replyContext =
    metadata?.reply_context && typeof metadata.reply_context === 'object'
      ? (metadata.reply_context as Record<string, unknown>)
      : null;
  const metadataReplyPreview =
    replyContext &&
    typeof replyContext.preview_text === 'string' &&
    replyContext.preview_text.trim().length > 0
      ? replyContext.preview_text.trim()
      : null;
  const continueActionLabel =
    !isUser &&
    metadata?.practice_kind === 'translation_clarification' &&
    typeof metadata.continue_action_label === 'string' &&
    metadata.continue_action_label.trim().length > 0
      ? metadata.continue_action_label.trim()
      : null;

  // Parse for "Regarding: [Quote]"
  const hasQuote = message.content.startsWith('Regarding:');
  let quoteContent = '';
  let actualMessage = message.content;

  if (hasQuote) {
    const quoteEnd = message.content.indexOf('\n\n');
    if (quoteEnd !== -1) {
      quoteContent = message.content.substring(0, quoteEnd).replace('Regarding: ', '').replace(/"/g, '');
      actualMessage = message.content.substring(quoteEnd + 2);
    }
  }

  const renderedQuote = metadataReplyPreview ?? quoteContent;
  const showQuote = renderedQuote.length > 0;

  return (
    <Animated.View
      entering={FadeInDown.duration(350).springify()}
      style={[styles.row, isUser ? styles.userRow : styles.assistantRow]}>

      {/* Top-aligned Avatar for Coach */}
      {!isUser && (
        <View style={styles.avatarColumn}>
          <View style={[styles.avatar, styles.assistantAvatar]}>
            <Text style={styles.avatarEmoji}>🤖</Text>
          </View>
        </View>
      )}

      <View style={[styles.bubbleWrapper, isUser ? styles.userBubbleWrapper : styles.assistantBubbleWrapper]}>
        <View style={[styles.bubble, isUser ? styles.userBubble : styles.assistantBubble]}>
          <View style={styles.bubbleHeader}>
            <Text style={[styles.role, isUser ? styles.userRole : styles.assistantRole]}>
              {isUser ? 'YOU' : 'COACH'}
            </Text>
            <View style={styles.headerActions}>
              {!isUser && onPlayAudio ? (
                <Pressable
                  onPress={() => onPlayAudio(message)}
                  style={({ pressed }) => [styles.replyBtn, pressed && styles.btnPressed]}>
                  <Text style={styles.replyIcon}>{isSpeaking ? '⏹️' : '🔊'}</Text>
                </Pressable>
              ) : null}
              {onReply ? (
                <Pressable
                  onPress={() =>
                    onReply({
                      kind: 'message',
                      preview_text: actualMessage,
                      source_message_id: message.id,
                    })
                  }
                  style={({ pressed }) => [styles.replyBtn, pressed && styles.btnPressed]}>
                  <Text style={styles.replyIcon}>⤴️</Text>
                </Pressable>
              ) : null}
            </View>
          </View>

          {showQuote && (
            <View style={styles.quoteBlock}>
              <View style={styles.quoteBar} />
              <Text style={styles.quoteText} numberOfLines={2}>{renderedQuote}</Text>
            </View>
          )}

          <Text style={[styles.content, isUser ? styles.userContent : styles.assistantContent]}>
            {actualMessage}
          </Text>

          {translationSourceSentence ? (
            <View style={styles.translationPromptCard}>
              <Text style={styles.translationPromptLabel}>Hindi sentence</Text>
              <Text style={styles.translationPromptSentence}>{translationSourceSentence}</Text>
              <Text style={styles.translationPromptHint}>Write your answer in English.</Text>
            </View>
          ) : null}

          {continueActionLabel && onContinueLearning ? (
            <Pressable
              onPress={() => onContinueLearning(message)}
              style={({ pressed }) => [
                styles.continueButton,
                pressed && styles.btnPressed,
              ]}>
              <Text style={styles.continueButtonText}>{continueActionLabel}</Text>
            </Pressable>
          ) : null}
        </View>
      </View>

      {/* Top-aligned Avatar for User */}
      {isUser && (
        <View style={styles.avatarColumn}>
          <View style={[styles.avatar, styles.userAvatar]}>
            <Text style={styles.avatarEmoji}>🧑‍🎓</Text>
          </View>
        </View>
      )}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  row: {
    width: '100%',
    flexDirection: 'row',
    alignItems: 'flex-start', // Top aligned
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  userRow: {
    justifyContent: 'flex-end',
  },
  assistantRow: {
    justifyContent: 'flex-start',
  },
  avatarColumn: {
    paddingTop: 4, // Align with bubble top
  },
  avatar: {
    width: 34,
    height: 34,
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
    ...shadows.sm,
  },
  userAvatar: {
    backgroundColor: colors.primary[100],
    borderWidth: 1,
    borderColor: '#FFF',
  },
  assistantAvatar: {
    backgroundColor: colors.accent[50],
    borderWidth: 1,
    borderColor: '#FFF',
  },
  avatarEmoji: {
    fontSize: 16,
  },
  bubbleWrapper: {
    maxWidth: '82%',
  },
  userBubbleWrapper: {
    alignItems: 'flex-end',
  },
  assistantBubbleWrapper: {
    alignItems: 'flex-start',
  },
  bubble: {
    borderRadius: radii.xl,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    gap: spacing.xs,
  },
  userBubble: {
    backgroundColor: colors.primary[600],
    borderTopRightRadius: 4, // More modern chat shape
    ...shadows.md,
  },
  assistantBubble: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 4,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    ...shadows.sm,
  },
  bubbleHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 2,
  },
  headerActions: {
    flexDirection: 'row',
    gap: spacing.xs,
  },
  role: {
    ...typography.captionBold,
    fontSize: 9,
    letterSpacing: 1,
  },
  userRole: {
    color: 'rgba(255,255,255,0.6)',
  },
  assistantRole: {
    color: colors.primary[500],
  },
  replyBtn: {
    padding: 2,
  },
  btnPressed: {
    opacity: 0.6,
    transform: [{ scale: 0.9 }],
  },
  replyIcon: {
    fontSize: 10,
    opacity: 0.6,
  },

  // Quoted Reply in History
  quoteBlock: {
    flexDirection: 'row',
    backgroundColor: 'rgba(0,0,0,0.05)',
    borderRadius: radii.md,
    padding: spacing.sm,
    marginBottom: spacing.xs,
    gap: spacing.sm,
  },
  quoteBar: {
    width: 3,
    backgroundColor: colors.primary[400],
    borderRadius: 2,
  },
  quoteText: {
    ...typography.caption,
    color: '#64748B',
    fontSize: 11,
    fontStyle: 'italic',
  },

  content: {
    ...typography.bodyLg,
    lineHeight: 24, // More readable line height
  },
  userContent: {
    color: '#FFFFFF',
    fontWeight: '500',
  },
  assistantContent: {
    color: '#1E293B',
  },
  translationPromptCard: {
    marginTop: spacing.sm,
    borderRadius: radii.lg,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    backgroundColor: colors.accent[50],
    borderWidth: 1,
    borderColor: colors.accent[100],
    gap: spacing.xs,
  },
  translationPromptLabel: {
    ...typography.captionBold,
    color: colors.primary[700],
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
  translationPromptSentence: {
    ...typography.bodyLgBold,
    color: colors.text.primary,
    lineHeight: 28,
  },
  translationPromptHint: {
    ...typography.caption,
    color: colors.text.secondary,
  },
  continueButton: {
    alignSelf: 'flex-start',
    backgroundColor: colors.primary[50],
    borderColor: colors.primary[100],
    borderRadius: radii.full,
    borderWidth: 1,
    marginTop: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  continueButtonText: {
    ...typography.body,
    color: colors.primary[700],
  },
});
