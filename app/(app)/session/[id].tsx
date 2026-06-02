import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  withRepeat,
  withTiming,
  withSequence,
  FadeIn,
  FadeInDown,
  Layout,
} from 'react-native-reanimated';

import { ChatBubble } from '@/src/components/chat-bubble';
import { CorrectionCard } from '@/src/components/correction-card';
import { EmptyState } from '@/src/components/empty-state';
import { LoadingScreen } from '@/src/components/loading-screen';
import { PrimaryButton } from '@/src/components/primary-button';
import { QuickReplyChips } from '@/src/components/quick-reply-chips';
import { useAuth } from '@/src/hooks/use-auth';
import { useVoicePractice } from '@/src/hooks/use-voice-practice';
import { ApiError } from '@/src/lib/api/client';
import { learningProfileApi } from '@/src/lib/api/learning-profile';
import { practiceApi } from '@/src/lib/api/practice';
import type {
  ChatRequestMetadata,
  MessageCorrection,
  MessageReplyContext,
  PracticeMessage,
  PracticeSessionCompletionSummary,
  PracticeSessionDetail,
} from '@/src/lib/api/types';
import { formatLearningAreaLabel } from '@/src/lib/learning-profile';
import { colors, radii, shadows, spacing, typography } from '@/src/theme';

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

function buildAssistantSpeech(message: { content: string; metadata_json: Record<string, unknown> | null }) {
  const sourceSentence = message.metadata_json?.translation_source_sentence;
  if (
    message.metadata_json?.practice_kind !== 'translation_prompt' ||
    typeof sourceSentence !== 'string' ||
    sourceSentence.trim().length === 0
  ) {
    return message.content;
  }

  return `${message.content}\n\nHindi sentence: ${sourceSentence}\n\nWrite your answer in English.`;
}

function readAssistantSpeechLanguage(message: { metadata_json: Record<string, unknown> | null }) {
  const responseLanguageCode = message.metadata_json?.response_language_code;
  if (typeof responseLanguageCode === 'string' && responseLanguageCode.trim().length > 0) {
    return responseLanguageCode.trim();
  }

  const transcriptionLanguage = message.metadata_json?.language;
  if (typeof transcriptionLanguage === 'string' && transcriptionLanguage.trim().length > 0) {
    return transcriptionLanguage.trim();
  }

  return null;
}

function buildOptimisticUserMessage(
  {
    sessionId,
    content,
    messageOrder,
    metadataJson,
  }: {
    sessionId: string;
    content: string;
    messageOrder: number;
    metadataJson: Record<string, unknown> | null;
  }
): PracticeMessage {
  const timestamp = new Date().toISOString();
  return {
    id: `temp-user-${Date.now()}`,
    session_id: sessionId,
    role: 'user',
    content,
    message_order: messageOrder,
    metadata_json: metadataJson,
    created_at: timestamp,
    updated_at: timestamp,
  };
}

function isPersistedMessageId(messageId: string) {
  return !messageId.startsWith('temp-user-');
}

function isUuidLike(value: string) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
}

function normalizeMessageText(value: string) {
  return value.replace(/\s+/g, ' ').trim().toLowerCase();
}

function getRenderableCorrection(
  message: PracticeMessage,
  correction: MessageCorrection | null | undefined
) {
  if (!correction) {
    return null;
  }
  return normalizeMessageText(correction.original_text) === normalizeMessageText(message.content)
    ? correction
    : null;
}

function TypingIndicator({ label }: { label?: string | null }) {
  const dot1 = useSharedValue(0);
  const dot2 = useSharedValue(0);
  const dot3 = useSharedValue(0);

  useEffect(() => {
    dot1.value = withRepeat(
      withSequence(withTiming(-6, { duration: 300 }), withTiming(0, { duration: 300 })),
      -1, false
    );
    setTimeout(() => {
      dot2.value = withRepeat(
        withSequence(withTiming(-6, { duration: 300 }), withTiming(0, { duration: 300 })),
        -1, false
      );
    }, 150);
    setTimeout(() => {
      dot3.value = withRepeat(
        withSequence(withTiming(-6, { duration: 300 }), withTiming(0, { duration: 300 })),
        -1, false
      );
    }, 300);
  }, [dot1, dot2, dot3]);

  const dot1Style = useAnimatedStyle(() => ({ transform: [{ translateY: dot1.value }] }));
  const dot2Style = useAnimatedStyle(() => ({ transform: [{ translateY: dot2.value }] }));
  const dot3Style = useAnimatedStyle(() => ({ transform: [{ translateY: dot3.value }] }));

  return (
    <Animated.View entering={FadeIn.duration(300)} style={typingStyles.container}>
      <View style={typingStyles.avatar}>
        <Text style={typingStyles.avatarEmoji}>🤖</Text>
      </View>
      <View style={typingStyles.wrapper}>
        {label ? <Text style={typingStyles.label}>{label}</Text> : null}
        <View style={typingStyles.bubble}>
          <Animated.View style={[typingStyles.dot, dot1Style]} />
          <Animated.View style={[typingStyles.dot, dot2Style]} />
          <Animated.View style={[typingStyles.dot, dot3Style]} />
        </View>
      </View>
    </Animated.View>
  );
}

const typingStyles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: spacing.sm,
  },
  avatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: colors.accent[50],
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarEmoji: {
    fontSize: 16,
  },
  bubble: {
    backgroundColor: colors.bg.card,
    borderRadius: radii.xl,
    borderBottomLeftRadius: spacing.xs,
    borderWidth: 1,
    borderColor: colors.border.light,
    flexDirection: 'row',
    gap: spacing.xs,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    ...shadows.sm,
  },
  wrapper: {
    gap: spacing.xs,
  },
  label: {
    ...typography.caption,
    color: colors.text.secondary,
    marginLeft: spacing.sm,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.primary[300],
  },
});

export default function SessionScreen() {
  const { id, fromOnboarding } = useLocalSearchParams<{ id: string; fromOnboarding?: string }>();
  const insets = useSafeAreaInsets();
  const auth = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();
  const scrollViewRef = useRef<ScrollView | null>(null);
  const composerInputRef = useRef<TextInput | null>(null);
  const [draft, setDraft] = useState('');
  const [replyTo, setReplyTo] = useState<MessageReplyContext | null>(null);
  const [streamStatus, setStreamStatus] = useState<string | null>(null);
  const [streamingAssistantText, setStreamingAssistantText] = useState('');
  const [sessionCompletion, setSessionCompletion] = useState<PracticeSessionCompletionSummary | null>(null);
  const {
    voiceError,
    setVoiceError,
    isRecording,
    recordingDurationMs,
    startRecording,
    stopRecording,
    speakingMessageId,
    speakAssistantMessage,
  } = useVoicePractice();

  const sendScale = useSharedValue(1);
  const sendAnimatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: sendScale.value }],
  }));

  const sessionQuery = useQuery({
    queryKey: ['practice-session', id],
    queryFn: () => auth.authorizedRequest((token) => practiceApi.getSession(token, id)),
    enabled: Boolean(id),
  });

  const learningProfileQuery = useQuery({
    queryKey: ['learning-profile', 'session'],
    queryFn: () =>
      auth.authorizedRequest((token) => learningProfileApi.getMine(token)),
  });

  const userMessageIds = useMemo(
    () =>
      (sessionQuery.data?.messages ?? [])
        .filter((message) => message.role === 'user' && isPersistedMessageId(message.id))
        .map((message) => message.id),
    [sessionQuery.data?.messages]
  );

  const clearTempCorrectionQueries = useCallback(() => {
    queryClient.removeQueries({
      queryKey: ['message-correction', id],
      exact: false,
      predicate: (query) => {
        const [, , messageId] = query.queryKey;
        return typeof messageId === 'string' && !isPersistedMessageId(messageId);
      },
    });
  }, [id, queryClient]);

  const correctionQueries = useQueries({
    queries: userMessageIds.map((messageId) => ({
      queryKey: ['message-correction', id, messageId],
      enabled: Boolean(id) && isUuidLike(messageId),
      queryFn: async () =>
        auth.authorizedRequest((token) => practiceApi.getCorrection(token, id, messageId)).catch((error) => {
          if (error instanceof ApiError && error.status === 404) {
            return null;
          }
          throw error;
        }),
      staleTime: 5 * 60 * 1000,
    })),
  });

  const correctionMap = useMemo(() => {
    const nextMap = new Map<string, MessageCorrection | null>();
    correctionQueries.forEach((query, index) => {
      nextMap.set(userMessageIds[index], query.data ?? null);
    });
    return nextMap;
  }, [correctionQueries, userMessageIds]);

  const chatMutation = useMutation<
    Awaited<ReturnType<typeof practiceApi.chatStream>>,
    Error,
    { content: string; metadata: ChatRequestMetadata | null },
    { previousSession: PracticeSessionDetail | undefined; optimisticMessageId: string | null }
  >({
    mutationFn: ({ content, metadata }: { content: string; metadata: ChatRequestMetadata | null }) =>
      auth.authorizedRequest((token) =>
        practiceApi.chatStream(token, id, content, metadata, (event) => {
          if (event.type === 'status') {
            setStreamStatus(event.message);
          }
          if (event.type === 'assistant_delta') {
            setStreamStatus(null);
            setStreamingAssistantText(event.snapshot);
          }
          requestAnimationFrame(() => {
            scrollViewRef.current?.scrollToEnd({ animated: true });
          });
        })
      ),
    onMutate: async ({ content, metadata }) => {
      await queryClient.cancelQueries({ queryKey: ['practice-session', id] });
      clearTempCorrectionQueries();

      const previousSession = queryClient.getQueryData<PracticeSessionDetail>(['practice-session', id]);
      const optimisticMessage = previousSession
        ? buildOptimisticUserMessage({
            sessionId: previousSession.id,
            content,
            messageOrder: previousSession.messages.length + 1,
            metadataJson: metadata as Record<string, unknown> | null,
          })
        : null;

      if (previousSession && optimisticMessage) {
        queryClient.setQueryData<PracticeSessionDetail>(['practice-session', id], {
          ...previousSession,
          starter: null,
          messages: [...previousSession.messages, optimisticMessage],
        });
      }

      setDraft('');
      setReplyTo(null);
      setStreamStatus('Sending your message...');
      setStreamingAssistantText('');
      requestAnimationFrame(() => {
        scrollViewRef.current?.scrollToEnd({ animated: true });
      });

      return { previousSession, optimisticMessageId: optimisticMessage?.id ?? null };
    },
    onSuccess: (response) => {
      queryClient.setQueryData<PracticeSessionDetail | undefined>(['practice-session', id], (current) => {
        if (!current) {
          return current;
        }

        const nextMessages = current.messages.filter(
          (message) =>
            !message.id.startsWith('temp-user-') &&
            message.id !== response.user_message.id &&
            message.id !== response.assistant_message.id
        );

        return {
          ...current,
          starter: null,
          status: response.completion_summary ? 'completed' : current.status,
          ended_at: response.completion_summary ? new Date().toISOString() : current.ended_at,
          completion_summary: response.completion_summary ?? current.completion_summary ?? null,
          messages: [...nextMessages, response.user_message, response.assistant_message],
        };
      });

      if (response.correction) {
        queryClient.setQueryData(['message-correction', id, response.user_message.id], response.correction);
      }
      if (response.completion_summary) {
        setSessionCompletion(response.completion_summary);
        void queryClient.invalidateQueries({ queryKey: ['practice-sessions'] });
      }
      setStreamStatus(null);
      setStreamingAssistantText('');
      clearTempCorrectionQueries();
      requestAnimationFrame(() => {
        scrollViewRef.current?.scrollToEnd({ animated: true });
      });
    },
    onError: (_error, variables, context) => {
      if (context?.previousSession) {
        queryClient.setQueryData(['practice-session', id], context.previousSession);
      }
      setStreamStatus(null);
      setStreamingAssistantText('');
      clearTempCorrectionQueries();
      setDraft(variables.content);
    },
  });

  const sendMessage = useCallback(
    (content: string, metadata: ChatRequestMetadata | null = null) => {
      chatMutation.mutate({ content, metadata });
    },
    [chatMutation]
  );

  const voiceChatMutation = useMutation({
    mutationFn: async () => {
      const recording = await stopRecording();
      const formData = new FormData();
      formData.append(
        'audio',
        {
          uri: recording.uri,
          name: recording.fileName,
          type: recording.mimeType,
        } as any
      );
      if (recording.durationMs !== null) {
        formData.append('duration_ms', String(recording.durationMs));
      }
      formData.append('source', Platform.OS);

      return auth.authorizedRequest((token) => practiceApi.voiceChat(token, id, formData));
    },
    onSuccess: (response) => {
      queryClient.setQueryData<PracticeSessionDetail | undefined>(['practice-session', id], (current) =>
        current
          ? {
              ...current,
              starter: null,
              messages: [...current.messages, response.user_message, response.assistant_message],
            }
          : current
      );

      if (response.correction) {
        queryClient.setQueryData(['message-correction', id, response.user_message.id], response.correction);
      }
      setVoiceError(null);
      setReplyTo(null);

      if (sessionQuery.data?.mode === 'free_chat') {
        void speakAssistantMessage(response.assistant_message.id, buildAssistantSpeech(response.assistant_message), {
          language:
            readAssistantSpeechLanguage(response.assistant_message) ?? response.transcription.language,
        });
      }
    },
    onError: (error) => {
      setVoiceError(error instanceof Error ? error.message : 'Voice upload failed');
    },
  });

  const nextSessionMutation = useMutation({
    mutationFn: () =>
      auth.authorizedRequest((token) =>
        practiceApi.createSession(token, {
          mode: 'translation_practice',
          topic_id: sessionQuery.data?.topic_id ?? undefined,
          title: sessionQuery.data?.title ?? undefined,
        })
      ),
    onSuccess: (nextSession) => {
      setSessionCompletion(null);
      router.replace({
        pathname: '/(app)/session/[id]',
        params: { id: nextSession.id },
      });
    },
    onError: (error) => {
      setVoiceError(error instanceof Error ? error.message : 'Unable to start the next practice');
    },
  });

  useEffect(() => {
    if (sessionQuery.data?.messages.length) {
      requestAnimationFrame(() => {
        scrollViewRef.current?.scrollToEnd({ animated: true });
      });
    }
  }, [sessionQuery.data?.messages.length]);

  const isTranslationPractice = sessionQuery.data?.mode === 'translation_practice';
  const isFreeChat = sessionQuery.data?.mode === 'free_chat';
  const isStreamingResponse = chatMutation.isPending;
  const isWaitingForTranslationStarter =
    isTranslationPractice && (sessionQuery.data?.messages.length ?? 0) === 0;

  useEffect(() => {
    if (isWaitingForTranslationStarter && !sessionQuery.isFetching) {
      void sessionQuery.refetch();
    }
  }, [isWaitingForTranslationStarter, sessionQuery]);

  const handleSend = useCallback(() => {
    if (!draft.trim() || chatMutation.isPending) return;
    const finalContent = draft.trim();
    const metadata = replyTo ? { reply_context: replyTo } : null;

    sendScale.value = withSpring(0.85, { damping: 10 });
    setTimeout(() => {
      sendScale.value = withSpring(1, { damping: 8 });
    }, 100);

    sendMessage(finalContent, metadata);
  }, [chatMutation.isPending, draft, replyTo, sendMessage, sendScale]);

  const handleReply = useCallback((replyContext: MessageReplyContext) => {
    setReplyTo(replyContext);
  }, []);

  const handleContinueLearning = useCallback(() => {
    setReplyTo(null);
    requestAnimationFrame(() => {
      scrollViewRef.current?.scrollToEnd({ animated: true });
      composerInputRef.current?.focus();
    });
  }, []);

  const handleTryAgainFromCorrection = useCallback((correction: MessageCorrection) => {
    setReplyTo(null);
    if (correction.retry_strategy.retry_type === 'fill_blank') {
      setDraft(correction.retry_strategy.retry_prompt);
    } else {
      setDraft('');
    }
    requestAnimationFrame(() => {
      scrollViewRef.current?.scrollToEnd({ animated: true });
      composerInputRef.current?.focus();
    });
  }, []);

  const handleGoNextFromCorrection = useCallback((_correction: MessageCorrection) => {
    setReplyTo(null);
    setDraft('');
    requestAnimationFrame(() => {
      scrollViewRef.current?.scrollToEnd({ animated: true });
      composerInputRef.current?.blur();
    });
  }, []);

  const handlePlayAudio = useCallback(
    async (message: { id: string; content: string; metadata_json: Record<string, unknown> | null }) => {
      await speakAssistantMessage(message.id, buildAssistantSpeech(message), {
        language: readAssistantSpeechLanguage(message),
      });
    },
    [speakAssistantMessage]
  );

  const handleCompletionPrimaryAction = useCallback(() => {
    const nextType = sessionCompletion?.recommended_next_practice.type;
    if (!nextType) {
      return;
    }

    if (nextType === 'translation_practice') {
      nextSessionMutation.mutate();
      return;
    }

    setSessionCompletion(null);
    if (nextType === 'mistake_review') {
      router.replace('/(app)/mistake-review');
      return;
    }
    router.replace('/(app)/conversation-scenarios');
  }, [nextSessionMutation, router, sessionCompletion]);

  const handleCompletionSecondaryAction = useCallback(() => {
    setSessionCompletion(null);
    router.replace('/(app)');
  }, [router]);

  const handleVoicePress = useCallback(async () => {
    if (sessionQuery.data?.status !== 'active' || chatMutation.isPending || voiceChatMutation.isPending) {
      return;
    }

    try {
      if (!isRecording) {
        setVoiceError(null);
        await startRecording();
        return;
      }
      await voiceChatMutation.mutateAsync();
    } catch (error) {
      setVoiceError(error instanceof Error ? error.message : 'Voice recording failed');
    }
  }, [
    chatMutation.isPending,
    isRecording,
    sessionQuery.data?.status,
    setVoiceError,
    startRecording,
    voiceChatMutation,
  ]);

  const handleQuickReply = useCallback(
    (reply: string) => {
      if (
        sessionQuery.data?.status !== 'active' ||
        chatMutation.isPending ||
        voiceChatMutation.isPending ||
        isRecording
      ) {
        return;
      }
      setReplyTo(null);
      setDraft('');
      sendMessage(reply, null);
    },
    [chatMutation.isPending, isRecording, sendMessage, sessionQuery.data?.status, voiceChatMutation.isPending]
  );

  if (!id) {
    return <EmptyState description="Missing session id." title="Session not found" icon="❓" />;
  }

  if (sessionQuery.isLoading) {
    return <LoadingScreen message="Loading your practice session… 💬" />;
  }

  if (!sessionQuery.data) {
    return <EmptyState description="This session could not be loaded." title="Session unavailable" icon="😔" />;
  }

  const isActive = sessionQuery.data.status === 'active';
  const isProcessingVoice = voiceChatMutation.isPending;
  const isStartingNextSession = nextSessionMutation.isPending;
  const canSend =
    Boolean(draft.trim()) &&
    !chatMutation.isPending &&
    !isProcessingVoice &&
    !isStartingNextSession &&
    isActive &&
    !isRecording &&
    !sessionCompletion;
  const hasUserMessages = sessionQuery.data.messages.some((message) => message.role === 'user');
  const visibleStarter = !hasUserMessages ? sessionQuery.data.starter : null;
  const starterMessageId = visibleStarter?.assistant_message.id ?? null;
  const latestTranslationPrompt = [...sessionQuery.data.messages]
    .reverse()
    .find(
      (message) =>
        message.role === 'assistant' &&
        message.metadata_json?.practice_kind === 'translation_prompt'
    );
  const focusTitle =
    (typeof latestTranslationPrompt?.metadata_json?.focus_label === 'string' &&
      latestTranslationPrompt.metadata_json.focus_label) ||
    (typeof visibleStarter?.assistant_message.metadata_json?.focus_label === 'string' &&
      visibleStarter.assistant_message.metadata_json.focus_label) ||
    (learningProfileQuery.data?.recommended_focus_area
      ? formatLearningAreaLabel(learningProfileQuery.data.recommended_focus_area)
      : null);
  const sessionContextNote = isTranslationPractice
    ? focusTitle
      ? `Focused on your weak area: ${focusTitle}. Translate into English and continue when your answer is correct.`
      : 'Translate into English and continue when your answer is correct.'
    : isFreeChat
      ? 'Speak or type in any language. The assistant will answer in the same language and keep the same tone.'
    : focusTitle
      ? `${focusTitle}. Keep your replies clear and natural.`
      : null;
  const streamingAssistantMessage = streamingAssistantText
    ? {
        id: 'streaming-assistant',
        session_id: sessionQuery.data.id,
        role: 'assistant' as const,
        content: streamingAssistantText,
        message_order: sessionQuery.data.messages.length + 1,
        metadata_json: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }
    : null;

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.select({ ios: 'padding', android: 'height', default: undefined })}
        keyboardVerticalOffset={insets.top}>

        {/* ── Session Header ── */}
        <Animated.View entering={FadeIn.duration(400)} style={styles.header}>
          <View style={styles.headerContent}>
            <View style={styles.headerIcon}>
              <Text style={styles.headerEmoji}>
                {sessionQuery.data.topic ? '📖' : '💬'}
              </Text>
            </View>
            <View style={styles.headerTextArea}>
              <Text style={styles.headerTitle} numberOfLines={1}>
                {sessionQuery.data.title ?? sessionQuery.data.topic?.title ?? 'Practice Session'}
              </Text>
              <Text style={styles.headerSubtitle} numberOfLines={1}>
                {isTranslationPractice
                  ? 'Translate into English, get corrected, and continue only after a correct answer'
                  : isFreeChat
                    ? 'Speak or type freely in any language and get a reply back in the same language'
                    : sessionQuery.data.topic?.description ?? 'Chat with your AI coach and get real-time feedback'}
              </Text>
            </View>
          </View>
        </Animated.View>

        {sessionContextNote && !hasUserMessages ? (
          <View style={styles.contextStrip}>
            <Text style={styles.contextStripLabel}>Practice note</Text>
            <Text style={styles.contextStripText}>{sessionContextNote}</Text>
          </View>
        ) : null}

        {/* ── Messages ── */}
        <ScrollView
          ref={scrollViewRef}
          contentContainerStyle={styles.messages}
          keyboardDismissMode="interactive"
          keyboardShouldPersistTaps="handled"
          onContentSizeChange={() => {
            scrollViewRef.current?.scrollToEnd({ animated: true });
          }}
          showsVerticalScrollIndicator={false}>
          {isWaitingForTranslationStarter ? (
            <EmptyState
              icon="🪄"
              title="Preparing your first translation"
              description="Your practice sentence is being prepared from your common weak areas."
            />
          ) : sessionQuery.data.messages.length === 0 ? (
            <EmptyState
              icon="👋"
              title="Start the conversation"
              description={
                isFreeChat
                  ? 'Type or speak in any language. Your AI coach will answer in the same language and tone.'
                  : 'Type your first message below and your AI coach will reply with feedback!'
              }
            />
          ) : (
            sessionQuery.data.messages.map((message) => (
              <View key={message.id} style={styles.messageGroup}>
                {(() => {
                  const renderableCorrection =
                    message.role === 'user'
                      ? getRenderableCorrection(message, correctionMap.get(message.id))
                      : null;

                  return (
                    <>
                <ChatBubble
                  message={message}
                  onReply={handleReply}
                  onPlayAudio={
                    message.role === 'assistant'
                      ? (assistantMessage) => void handlePlayAudio(assistantMessage)
                      : undefined
                  }
                  onContinueLearning={
                    message.role === 'assistant' ? () => handleContinueLearning() : undefined
                  }
                  isSpeaking={speakingMessageId === message.id}
                />
                {message.id === starterMessageId && visibleStarter?.quick_replies?.length ? (
                  <View style={styles.quickRepliesWrapper}>
                    <QuickReplyChips
                      replies={visibleStarter.quick_replies}
                      onPress={handleQuickReply}
                      disabled={!isActive || chatMutation.isPending || isProcessingVoice || isRecording || Boolean(sessionCompletion)}
                    />
                  </View>
                ) : null}
                {renderableCorrection ? (
                  <View style={styles.coachNoteWrapper}>
                    <View style={styles.noteLink} />
                    <CorrectionCard
                      correction={renderableCorrection}
                      onReply={handleReply}
                      onTryAgain={handleTryAgainFromCorrection}
                      onGoNext={handleGoNextFromCorrection}
                    />
                  </View>
                ) : null}
                    </>
                  );
                })()}
              </View>
            ))
          )}
          {streamingAssistantMessage ? (
            <View style={styles.messageGroup}>
              <ChatBubble message={streamingAssistantMessage} isSpeaking={false} />
            </View>
          ) : null}
          {((isStreamingResponse && !streamingAssistantMessage) || isProcessingVoice) ? (
            <TypingIndicator label={isProcessingVoice ? 'Processing your voice practice...' : streamStatus} />
          ) : null}
        </ScrollView>

        {/* ── Reply Preview ── */}
        {replyTo && (
          <Animated.View
            entering={FadeInDown.duration(200)}
            layout={Layout.springify()}
            style={styles.replyPreview}>
            <View style={styles.replyBar} />
            <View style={styles.replyContent}>
              <Text style={styles.replyLabel}>Replying to</Text>
              <Text style={styles.replyText} numberOfLines={2}>{replyTo.preview_text}</Text>
            </View>
            <Pressable onPress={() => setReplyTo(null)} style={styles.replyClose}>
              <Text style={styles.replyCloseIcon}>✕</Text>
            </Pressable>
          </Animated.View>
        )}

        {/* ── Inactive Banner ── */}
        {!isActive ? (
          <Animated.View entering={FadeInDown.duration(300)} style={styles.banner}>
            <Text style={styles.bannerText}>📌 This session has ended.</Text>
          </Animated.View>
        ) : null}

        {isRecording ? (
          <Animated.View entering={FadeInDown.duration(250)} style={styles.voiceBanner}>
            <Text style={styles.voiceBannerTitle}>🎙️ Recording now</Text>
            <Text style={styles.voiceBannerBody}>
              {isFreeChat
                ? 'Speak naturally in any language, then tap the mic again to send.'
                : 'Speak naturally, then tap the mic again to send.'}
            </Text>
            <Text style={styles.voiceBannerMeta}>
              {Math.max(1, Math.floor(recordingDurationMs / 1000))}s
            </Text>
          </Animated.View>
        ) : null}

        {isProcessingVoice ? (
          <Animated.View entering={FadeInDown.duration(250)} style={styles.voiceBanner}>
            <Text style={styles.voiceBannerTitle}>🪄 Processing voice practice</Text>
            <Text style={styles.voiceBannerBody}>
              {isFreeChat
                ? 'Transcribing your speech and preparing a spoken reply in the same language.'
                : 'Transcribing your speech and preparing the reply.'}
            </Text>
          </Animated.View>
        ) : null}

        {/* ── Error ── */}
        {chatMutation.error ? (
          <Text style={styles.error}>
            ⚠️ {chatMutation.error instanceof Error ? chatMutation.error.message : 'Unable to send message'}
          </Text>
        ) : null}
        {voiceError ? <Text style={styles.error}>⚠️ {voiceError}</Text> : null}

        {/* ── Composer Bar ── */}
        <View style={styles.composerWrapper}>
          <View style={styles.composer}>
            <View style={styles.inputContainer}>
              <TextInput
                ref={composerInputRef}
                editable={
                  isActive &&
                  !isStreamingResponse &&
                  !isProcessingVoice &&
                  !isRecording &&
                  !isStartingNextSession &&
                  !sessionCompletion
                }
                multiline
                onChangeText={setDraft}
                placeholder={
                  isRecording
                    ? 'Recording…'
                    : isFreeChat
                      ? 'Type in any language…'
                      : 'Type your message…'
                }
                placeholderTextColor={colors.text.tertiary}
                style={styles.input}
                value={draft}
              />
            </View>
            <AnimatedPressable
              disabled={!isActive || chatMutation.isPending || isProcessingVoice || Boolean(sessionCompletion) || isStartingNextSession}
              onPress={() => void handleVoicePress()}
              style={[
                styles.voiceButton,
                isRecording && styles.voiceButtonRecording,
                (!isActive || chatMutation.isPending || isProcessingVoice || Boolean(sessionCompletion) || isStartingNextSession) &&
                  styles.voiceButtonDisabled,
              ]}>
              <Text style={styles.voiceIcon}>
                {isProcessingVoice ? '⏳' : isRecording ? '⏹️' : '🎙️'}
              </Text>
            </AnimatedPressable>
            <AnimatedPressable
              disabled={!canSend}
              onPress={handleSend}
              style={[
                sendAnimatedStyle,
                styles.sendButton,
                !canSend && styles.sendButtonDisabled,
              ]}>
              <Text style={styles.sendIcon}>{chatMutation.isPending ? '⏳' : '🚀'}</Text>
            </AnimatedPressable>
          </View>
          <View style={styles.composerHintRow}>
            <Text style={styles.composerHint}>
              {isRecording
                ? 'Tap the mic again to stop and send'
                : isTranslationPractice
                  ? 'Translate the Hindi sentence shown above into English'
                  : isFreeChat
                    ? 'Type a message or use your voice in any language'
                    : 'Type a message or speak instead'}
            </Text>
          </View>
        </View>

        {sessionCompletion ? (
          <View style={styles.completionOverlay}>
            <View style={[styles.completionCard, shadows.lg]}>
              <Text style={styles.completionEmoji}>🎉</Text>
              <Text style={styles.completionTitle}>{sessionCompletion.title}</Text>
              <Text style={styles.completionBody}>{sessionCompletion.message}</Text>

              <View style={styles.completionMetricsRow}>
                <View style={styles.completionMetric}>
                  <Text style={styles.completionMetricValue}>{sessionCompletion.completed_items}</Text>
                  <Text style={styles.completionMetricLabel}>Items done</Text>
                </View>
                <View style={styles.completionMetric}>
                  <Text style={styles.completionMetricValue}>{sessionCompletion.average_score ?? '--'}</Text>
                  <Text style={styles.completionMetricLabel}>Average score</Text>
                </View>
              </View>

              <View style={styles.completionInsightCard}>
                <Text style={styles.completionInsightLabel}>Strongest area</Text>
                <Text style={styles.completionInsightValue}>
                  {sessionCompletion.strongest_area ?? 'Building consistency'}
                </Text>
                <Text style={styles.completionInsightLabel}>Next focus</Text>
                <Text style={styles.completionInsightValue}>
                  {sessionCompletion.focus_area ?? 'General fluency'}
                </Text>
              </View>

              <PrimaryButton
                label={sessionCompletion.recommended_next_practice.title}
                onPress={handleCompletionPrimaryAction}
                loading={isStartingNextSession}
                disabled={isStartingNextSession}
                icon="🚀"
              />
              <PrimaryButton
                label={fromOnboarding === '1' ? 'Go to Home' : 'Back to Home'}
                onPress={handleCompletionSecondaryAction}
                variant="secondary"
              />
            </View>
          </View>
        ) : null}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg.base,
  },

  // ── Header ──
  header: {
    borderBottomColor: colors.border.light,
    borderBottomWidth: 1,
    backgroundColor: colors.bg.card,
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md,
  },
  contextStrip: {
    marginHorizontal: spacing.xl,
    marginTop: spacing.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radii.lg,
    backgroundColor: colors.bg.card,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  contextStripLabel: {
    ...typography.captionBold,
    color: colors.primary[600],
    textTransform: 'uppercase',
    marginBottom: 2,
  },
  contextStripText: {
    ...typography.caption,
    color: colors.text.secondary,
  },
  headerContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  headerIcon: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: colors.primary[50],
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerEmoji: {
    fontSize: 20,
  },
  headerTextArea: {
    flex: 1,
    gap: spacing.xxs,
  },
  headerTitle: {
    ...typography.bodyLgBold,
    color: colors.text.primary,
  },
  headerSubtitle: {
    ...typography.caption,
    color: colors.text.tertiary,
  },

  // ── Messages ──
  messages: {
    gap: spacing.sm,
    padding: spacing.lg,
    paddingBottom: spacing['3xl'],
  },
  messageGroup: {
    marginBottom: spacing.sm,
    gap: spacing.xs,
  },
  quickRepliesWrapper: {
    paddingLeft: 44,
  },
  coachNoteWrapper: {
    flexDirection: 'row',
    paddingLeft: 42, // Aligns content with Coach bubble text
    marginTop: -spacing.xs, // Pull closer to the user message
  },
  noteLink: {
    width: 2,
    backgroundColor: '#E2E8F0',
    marginRight: spacing.md,
    borderRadius: 1,
    height: '100%',
    marginLeft: -spacing.sm,
  },

  // ── Reply Preview ──
  replyPreview: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F8FAFC',
    borderTopWidth: 1,
    borderTopColor: '#E2E8F0',
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.sm,
    gap: spacing.md,
  },
  replyBar: {
    width: 4,
    height: '100%',
    backgroundColor: colors.primary[400],
    borderRadius: 2,
  },
  replyContent: {
    flex: 1,
    gap: 2,
  },
  replyLabel: {
    ...typography.captionBold,
    color: colors.primary[600],
    fontSize: 10,
    textTransform: 'uppercase',
  },
  replyText: {
    ...typography.caption,
    color: '#64748B',
    fontSize: 12,
  },
  replyClose: {
    padding: 4,
  },
  replyCloseIcon: {
    fontSize: 14,
    color: '#94A3B8',
    fontWeight: 'bold',
  },

  // ── Banner ──
  banner: {
    backgroundColor: colors.gold[50],
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.gold[200],
    marginHorizontal: spacing.xl,
    marginBottom: spacing.sm,
    padding: spacing.md,
  },
  bannerText: {
    ...typography.bodySemibold,
    color: colors.gold[600],
  },
  voiceBanner: {
    backgroundColor: colors.primary[50],
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.primary[100],
    gap: spacing.xxs,
    marginHorizontal: spacing.xl,
    marginBottom: spacing.sm,
    padding: spacing.md,
  },
  voiceBannerTitle: {
    ...typography.bodySemibold,
    color: colors.primary[700],
  },
  voiceBannerBody: {
    ...typography.body,
    color: colors.text.secondary,
  },
  voiceBannerMeta: {
    ...typography.captionBold,
    color: colors.primary[600],
  },
  completionOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(15, 23, 42, 0.58)',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing['2xl'],
  },
  completionCard: {
    width: '100%',
    maxWidth: 420,
    backgroundColor: colors.bg.card,
    borderRadius: radii.xl,
    padding: spacing.xl,
    gap: spacing.lg,
  },
  completionEmoji: {
    fontSize: 36,
    textAlign: 'center',
  },
  completionTitle: {
    ...typography.heading,
    color: colors.text.primary,
    textAlign: 'center',
  },
  completionBody: {
    ...typography.body,
    color: colors.text.secondary,
    textAlign: 'center',
    lineHeight: 22,
  },
  completionMetricsRow: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  completionMetric: {
    flex: 1,
    backgroundColor: colors.primary[50],
    borderRadius: radii.lg,
    padding: spacing.md,
    alignItems: 'center',
    gap: spacing.xs,
  },
  completionMetricValue: {
    ...typography.display,
    color: colors.primary[700],
  },
  completionMetricLabel: {
    ...typography.caption,
    color: colors.text.secondary,
  },
  completionInsightCard: {
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.border.light,
    backgroundColor: colors.bg.base,
    padding: spacing.md,
    gap: spacing.xs,
  },
  completionInsightLabel: {
    ...typography.captionBold,
    color: colors.text.tertiary,
    textTransform: 'uppercase',
  },
  completionInsightValue: {
    ...typography.bodySemibold,
    color: colors.text.primary,
    marginBottom: spacing.xs,
  },

  // ── Error ──
  error: {
    ...typography.body,
    color: colors.error,
    marginBottom: spacing.sm,
    marginHorizontal: spacing.xl,
  },

  // ── Composer ──
  composerWrapper: {
    backgroundColor: colors.bg.card,
    borderTopColor: colors.border.light,
    borderTopWidth: 1,
  },
  composer: {
    alignItems: 'flex-end',
    flexDirection: 'row',
    gap: spacing.md,
    padding: spacing.md,
    paddingHorizontal: spacing.lg,
  },
  inputContainer: {
    flex: 1,
    backgroundColor: colors.bg.base,
    borderRadius: radii['2xl'],
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  input: {
    color: colors.text.primary,
    fontSize: 16,
    maxHeight: 120,
    minHeight: 46,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    textAlignVertical: 'top',
  },
  sendButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: colors.primary[500],
    alignItems: 'center',
    justifyContent: 'center',
    ...shadows.sm,
  },
  sendButtonDisabled: {
    backgroundColor: colors.neutral[200],
    shadowOpacity: 0,
    elevation: 0,
  },
  voiceButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.accent[400],
    ...shadows.sm,
  },
  voiceButtonRecording: {
    backgroundColor: colors.error,
  },
  voiceButtonDisabled: {
    backgroundColor: colors.neutral[200],
    shadowOpacity: 0,
    elevation: 0,
  },
  voiceIcon: {
    fontSize: 18,
  },
  sendIcon: {
    fontSize: 20,
  },
  composerHintRow: {
    paddingBottom: spacing.sm,
    paddingHorizontal: spacing.lg,
  },
  composerHint: {
    ...typography.caption,
    color: colors.text.tertiary,
  },
});
