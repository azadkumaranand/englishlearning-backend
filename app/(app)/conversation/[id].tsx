import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import {
  Animated,
  Easing,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { EmptyState } from '@/src/components/empty-state';
import { PrimaryButton } from '@/src/components/primary-button';
import { ScreenContainer } from '@/src/components/screen-container';
import { useAuth } from '@/src/hooks/use-auth';
import { useVoicePractice } from '@/src/hooks/use-voice-practice';
import { conversationApi } from '@/src/lib/api/conversation';
import type { ConversationReplyResponse, ConversationScenario } from '@/src/lib/api/types';
import { formatLearningAreaLabel } from '@/src/lib/learning-profile';
import { colors, radii, shadows, spacing, typography } from '@/src/theme';

type ChatMessage = {
  id: string;
  role: 'ai' | 'user';
  text: string;
};

type VoiceModeStatus = 'idle' | 'listening' | 'processing' | 'speaking';
type VoiceStage = 'ready' | 'listening' | 'processing' | 'speaking';

const NO_RESPONSE_TIMEOUT_MS = 20_000;
const SILENCE_AUTO_STOP_MS = 5_000;
const SPEECH_START_THRESHOLD = -58;
const SPEECH_ACTIVE_THRESHOLD = -64;

function StatusBadge({ label, tone }: { label: string; tone: 'good' | 'warn' | 'great' }) {
  return (
    <View
      style={[
        styles.statusBadge,
        tone === 'good' && styles.statusBadgeGood,
        tone === 'warn' && styles.statusBadgeWarn,
        tone === 'great' && styles.statusBadgeGreat,
      ]}>
      <Text style={styles.statusBadgeText}>{label}</Text>
    </View>
  );
}

function getStageCopy(stage: VoiceStage, hasTranscript: boolean) {
  switch (stage) {
    case 'speaking':
      return {
        chip: 'Coach speaking',
        title: 'Listen',
        hint: 'Replay anytime if you miss a word.',
        icon: 'volume-high' as const,
      };
    case 'listening':
      return {
        chip: 'Listening',
        title: 'Speak',
        hint: 'Pause for a few seconds when you finish.',
        icon: 'microphone' as const,
      };
    case 'processing':
      return {
        chip: 'Thinking',
        title: 'Checking',
        hint: 'Preparing the next reply.',
        icon: 'progress-clock' as const,
      };
    case 'ready':
    default:
      return {
        chip: 'Ready',
        title: hasTranscript ? 'Next turn' : 'Your turn',
        hint: 'Tap the mic to answer.',
        icon: 'microphone-outline' as const,
      };
  }
}

export default function ConversationSessionScreen() {
  const auth = useAuth();
  const router = useRouter();
  const params = useLocalSearchParams<{
    id?: string;
    scenario?: string;
    title?: string;
    aiMessage?: string;
    goal?: string;
    level?: string;
    maxTurns?: string;
  }>();
  const {
    voiceError,
    setVoiceError,
    isStartingRecording,
    isRecording,
    recordingDurationMs,
    recordingMetering,
    startRecording,
    stopRecording,
    cancelRecording,
    speakingMessageId,
    speakAssistantMessage,
    stopSpeaking,
  } = useVoicePractice();

  const sessionId = typeof params.id === 'string' ? params.id : '';
  const scenario = typeof params.scenario === 'string' ? (params.scenario as ConversationScenario) : null;
  const title = typeof params.title === 'string' ? params.title : 'Conversation Practice';
  const openingMessage =
    typeof params.aiMessage === 'string' ? params.aiMessage : 'Hello. Let’s start speaking practice.';
  const level = typeof params.level === 'string' ? params.level : 'beginner';
  const maxTurns = Number.parseInt(typeof params.maxTurns === 'string' ? params.maxTurns : '5', 10) || 5;

  const [draft, setDraft] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([{ id: 'ai-0', role: 'ai', text: openingMessage }]);
  const [lastFeedback, setLastFeedback] = useState<ConversationReplyResponse | null>(null);
  const [completionSummary, setCompletionSummary] = useState<ConversationReplyResponse['summary']>(null);
  const [pendingCompletionSummary, setPendingCompletionSummary] =
    useState<ConversationReplyResponse['summary']>(null);
  const [completedTurns, setCompletedTurns] = useState(0);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [typingMode, setTypingMode] = useState(false);
  const [lastTranscript, setLastTranscript] = useState<string | null>(null);
  const [voiceStatus, setVoiceStatus] = useState<VoiceModeStatus>('idle');
  const openingPromptPlayedRef = useRef<string | null>(null);
  const recordBeganAtRef = useRef<number | null>(null);
  const lastSpeechAtRef = useRef<number | null>(null);
  const hasDetectedSpeechRef = useRef(false);
  const autoHandlingRef = useRef(false);

  const resetVoiceActivityTracking = useCallback(() => {
    recordBeganAtRef.current = null;
    lastSpeechAtRef.current = null;
    hasDetectedSpeechRef.current = false;
    autoHandlingRef.current = false;
  }, []);

  const beginAutoListening = useCallback(async () => {
    if (
      typingMode ||
      completionSummary ||
      pendingCompletionSummary ||
      isStartingRecording ||
      isRecording ||
      autoHandlingRef.current
    ) {
      return;
    }

    try {
      setVoiceError(null);
      await startRecording();
    } catch (error) {
      setVoiceStatus('idle');
      setVoiceError(error instanceof Error ? error.message : 'Microphone could not start.');
    }
  }, [
    completionSummary,
    pendingCompletionSummary,
    isRecording,
    isStartingRecording,
    setVoiceError,
    startRecording,
    typingMode,
  ]);

  const applyReply = useCallback(
    async (
      response: ConversationReplyResponse,
      userMessage: string,
      options?: { transcript?: string | null }
    ) => {
      setMessages((current) => [
        ...current,
        { id: `user-${response.turn_number}`, role: 'user', text: userMessage },
        { id: `ai-${response.turn_number}`, role: 'ai', text: response.ai_reply },
      ]);
      setCompletedTurns(response.turn_number);
      setLastFeedback(response);
      setDraft('');
      setTypingMode(false);
      setLastTranscript(options?.transcript ?? userMessage);
      setVoiceStatus(response.session_completed ? 'idle' : 'speaking');
      await speakAssistantMessage(`ai-${response.turn_number}`, response.ai_reply, {
        language: 'en',
        onDone: () => {
          if (response.session_completed) {
            setPendingCompletionSummary(response.summary ?? null);
            setVoiceStatus('idle');
            return;
          }
          void beginAutoListening();
        },
      });
    },
    [beginAutoListening, speakAssistantMessage]
  );

  const continuePracticeMutation = useMutation({
    mutationFn: () =>
      scenario
        ? auth.authorizedRequest((token) => conversationApi.start(token, { scenario }))
        : Promise.reject(new Error('Scenario is unavailable for this practice session.')),
    onSuccess: (response) => {
      setPendingCompletionSummary(null);
      router.replace({
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

  const exitConversationMutation = useMutation({
    mutationFn: async () => {
      await cancelRecording();
      await stopSpeaking();
      return auth.authorizedRequest((token) => conversationApi.exit(token, sessionId));
    },
    onSuccess: () => {
      router.replace('/(app)/conversation-scenarios');
    },
    onError: (error) => {
      setVoiceError(error instanceof Error ? error.message : 'Could not leave this conversation right now.');
    },
  });

  const replyMutation = useMutation({
    mutationFn: (userMessage: string) =>
      auth.authorizedRequest((token) =>
        conversationApi.reply(token, {
          session_id: sessionId,
          user_message: userMessage,
        })
      ),
    onMutate: () => {
      setVoiceError(null);
      setVoiceStatus('processing');
    },
    onSuccess: (response, userMessage) => {
      void applyReply(response, userMessage);
    },
    onError: (error) => {
      setVoiceStatus('idle');
      setVoiceError(error instanceof Error ? error.message : 'Could not send your message. Try again.');
    },
  });

  const voiceReplyMutation = useMutation({
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
      formData.append('source', 'roleplay_voice_mode');
      return auth.authorizedRequest((token) => conversationApi.voiceReply(token, sessionId, formData));
    },
    onMutate: () => {
      setVoiceError(null);
      setVoiceStatus('processing');
    },
    onSuccess: (response) => {
      void applyReply(response.result, response.transcript, {
        transcript: response.transcript,
      });
    },
    onError: (error) => {
      setVoiceStatus('idle');
      setVoiceError(error instanceof Error ? error.message : 'Could not process your voice reply. Try again.');
    },
  });

  const currentCoachMessage = useMemo(() => {
    const aiMessages = messages.filter((message) => message.role === 'ai');
    return aiMessages[aiMessages.length - 1] ?? messages[0];
  }, [messages]);

  const turnLabel = useMemo(() => {
    if (completionSummary) {
      return `${maxTurns} / ${maxTurns}`;
    }
    return `${Math.min(completedTurns + 1, maxTurns)} / ${maxTurns}`;
  }, [completedTurns, completionSummary, maxTurns]);

  const feedbackTone =
    lastFeedback?.feedback_level === 'excellent'
      ? 'great'
      : lastFeedback?.feedback_level === 'good'
        ? 'good'
        : 'warn';

  const isBusy =
    replyMutation.isPending ||
    voiceReplyMutation.isPending ||
    continuePracticeMutation.isPending ||
    exitConversationMutation.isPending;
  const isVoiceCapturing = isStartingRecording || isRecording;
  const stageMode: VoiceStage = isBusy
    ? 'processing'
    : isVoiceCapturing
      ? 'listening'
      : speakingMessageId === currentCoachMessage.id
        ? 'speaking'
        : 'ready';
  const stageCopy = getStageCopy(stageMode, Boolean(lastTranscript));
  const orbScale = useRef(new Animated.Value(1)).current;
  const ringScale = useRef(new Animated.Value(1)).current;
  const ringOpacity = useRef(new Animated.Value(0.18)).current;
  const spinValue = useRef(new Animated.Value(0)).current;
  const waveValues = useRef([0, 1, 2, 3].map(() => new Animated.Value(0.45))).current;
  const stageAnimationsRef = useRef<Animated.CompositeAnimation[]>([]);

  useEffect(() => {
    stageAnimationsRef.current.forEach((animation) => animation.stop());
    stageAnimationsRef.current = [];
    orbScale.stopAnimation();
    ringScale.stopAnimation();
    ringOpacity.stopAnimation();
    spinValue.stopAnimation();
    waveValues.forEach((value) => value.stopAnimation());
    orbScale.setValue(1);
    ringScale.setValue(1);
    ringOpacity.setValue(stageMode === 'ready' ? 0.08 : 0.16);
    spinValue.setValue(0);
    waveValues.forEach((value) => value.setValue(0.45));

    if (stageMode === 'listening') {
      const pulse = Animated.loop(
        Animated.parallel([
          Animated.sequence([
            Animated.timing(orbScale, {
              toValue: 1.06,
              duration: 700,
              easing: Easing.inOut(Easing.ease),
              useNativeDriver: true,
            }),
            Animated.timing(orbScale, {
              toValue: 1,
              duration: 700,
              easing: Easing.inOut(Easing.ease),
              useNativeDriver: true,
            }),
          ]),
          Animated.sequence([
            Animated.timing(ringScale, {
              toValue: 1.35,
              duration: 1400,
              easing: Easing.out(Easing.ease),
              useNativeDriver: true,
            }),
            Animated.timing(ringScale, {
              toValue: 1,
              duration: 0,
              useNativeDriver: true,
            }),
          ]),
          Animated.sequence([
            Animated.timing(ringOpacity, {
              toValue: 0.32,
              duration: 300,
              useNativeDriver: true,
            }),
            Animated.timing(ringOpacity, {
              toValue: 0.08,
              duration: 1100,
              useNativeDriver: true,
            }),
          ]),
        ])
      );
      pulse.start();
      stageAnimationsRef.current.push(pulse);
    } else if (stageMode === 'speaking') {
      const waveLoop = Animated.loop(
        Animated.parallel(
          waveValues.map((value, index) =>
            Animated.sequence([
              Animated.delay(index * 110),
              Animated.timing(value, {
                toValue: 1,
                duration: 360,
                easing: Easing.inOut(Easing.ease),
                useNativeDriver: true,
              }),
              Animated.timing(value, {
                toValue: 0.4,
                duration: 360,
                easing: Easing.inOut(Easing.ease),
                useNativeDriver: true,
              }),
            ])
          )
        )
      );
      const breathe = Animated.loop(
        Animated.sequence([
          Animated.timing(orbScale, {
            toValue: 1.04,
            duration: 520,
            easing: Easing.inOut(Easing.ease),
            useNativeDriver: true,
          }),
          Animated.timing(orbScale, {
            toValue: 1,
            duration: 520,
            easing: Easing.inOut(Easing.ease),
            useNativeDriver: true,
          }),
        ])
      );
      waveLoop.start();
      breathe.start();
      stageAnimationsRef.current.push(waveLoop, breathe);
    } else if (stageMode === 'processing') {
      const spin = Animated.loop(
        Animated.timing(spinValue, {
          toValue: 1,
          duration: 1200,
          easing: Easing.linear,
          useNativeDriver: true,
        })
      );
      const pulse = Animated.loop(
        Animated.sequence([
          Animated.timing(orbScale, {
            toValue: 1.03,
            duration: 450,
            easing: Easing.inOut(Easing.ease),
            useNativeDriver: true,
          }),
          Animated.timing(orbScale, {
            toValue: 1,
            duration: 450,
            easing: Easing.inOut(Easing.ease),
            useNativeDriver: true,
          }),
        ])
      );
      spin.start();
      pulse.start();
      stageAnimationsRef.current.push(spin, pulse);
    }

    return () => {
      stageAnimationsRef.current.forEach((animation) => animation.stop());
      stageAnimationsRef.current = [];
    };
  }, [orbScale, ringOpacity, ringScale, spinValue, stageMode, waveValues]);

  const ringAnimatedStyle = {
    opacity: ringOpacity,
    transform: [{ scale: ringScale }],
  };
  const orbAnimatedStyle = {
    transform: [{ scale: orbScale }],
  };
  const spinnerAnimatedStyle = {
    transform: [
      {
        rotate: spinValue.interpolate({
          inputRange: [0, 1],
          outputRange: ['0deg', '360deg'],
        }),
      },
    ],
  };

  const replayPromptWithNudge = useCallback(async () => {
    autoHandlingRef.current = true;
    try {
      await cancelRecording();
      setVoiceStatus('speaking');
      await speakAssistantMessage(
        `reprompt-${currentCoachMessage.id}-${Date.now()}`,
        `Are you there? ${currentCoachMessage.text}`,
        {
          language: 'en',
          onDone: () => {
            void beginAutoListening();
          },
        }
      );
    } catch (error) {
      setVoiceStatus('idle');
      setVoiceError(error instanceof Error ? error.message : 'Could not restart voice listening.');
      autoHandlingRef.current = false;
    }
  }, [beginAutoListening, cancelRecording, currentCoachMessage.id, currentCoachMessage.text, setVoiceError, speakAssistantMessage]);

  const autoSubmitVoiceReply = useCallback(async () => {
    if (autoHandlingRef.current) {
      return;
    }
    autoHandlingRef.current = true;
    try {
      await voiceReplyMutation.mutateAsync();
    } catch (error) {
      setVoiceStatus('idle');
      setVoiceError(error instanceof Error ? error.message : 'Voice recording failed.');
      autoHandlingRef.current = false;
    }
  }, [setVoiceError, voiceReplyMutation]);

  useEffect(() => {
    if (!sessionId) return;
    if (openingPromptPlayedRef.current === sessionId) return;
    openingPromptPlayedRef.current = sessionId;
    void speakAssistantMessage('ai-0', openingMessage, {
      language: 'en',
      onDone: () => {
        void beginAutoListening();
      },
    });
    setVoiceStatus('speaking');
  }, [beginAutoListening, openingMessage, sessionId, speakAssistantMessage]);

  useEffect(() => {
    if (speakingMessageId === null && voiceStatus === 'speaking') {
      setVoiceStatus('idle');
    }
  }, [speakingMessageId, voiceStatus]);

  useEffect(() => {
    if (isRecording) {
      setVoiceStatus('listening');
      if (recordBeganAtRef.current === null) {
        const now = Date.now();
        recordBeganAtRef.current = now;
        lastSpeechAtRef.current = now;
        hasDetectedSpeechRef.current = false;
        autoHandlingRef.current = false;
      }
      return;
    }
    resetVoiceActivityTracking();
    if (voiceStatus === 'listening' && !isStartingRecording) {
      setVoiceStatus('idle');
    }
  }, [isRecording, isStartingRecording, resetVoiceActivityTracking, voiceStatus]);

  useEffect(() => {
    if (!isRecording) {
      return;
    }

    const metering = recordingMetering;
    if (typeof metering !== 'number') {
      if (recordingDurationMs >= 1800) {
        const now = Date.now();
        lastSpeechAtRef.current = now;
        hasDetectedSpeechRef.current = true;
      }
      return;
    }

    const threshold = hasDetectedSpeechRef.current ? SPEECH_ACTIVE_THRESHOLD : SPEECH_START_THRESHOLD;
    if (metering > threshold) {
      const now = Date.now();
      lastSpeechAtRef.current = now;
      hasDetectedSpeechRef.current = true;
    }
  }, [isRecording, recordingDurationMs, recordingMetering]);

  useEffect(() => {
    if (!isRecording || isBusy) {
      return;
    }

    const intervalId = setInterval(() => {
      const now = Date.now();
      const startedAt = recordBeganAtRef.current;
      const lastSpeechAt = lastSpeechAtRef.current;

      if (!startedAt || autoHandlingRef.current) {
        return;
      }

      if (!hasDetectedSpeechRef.current && now - startedAt >= NO_RESPONSE_TIMEOUT_MS) {
        void replayPromptWithNudge();
        return;
      }

      if (hasDetectedSpeechRef.current && lastSpeechAt && now - lastSpeechAt >= SILENCE_AUTO_STOP_MS) {
        void autoSubmitVoiceReply();
      }
    }, 500);

    return () => {
      clearInterval(intervalId);
    };
  }, [autoSubmitVoiceReply, isBusy, isRecording, replayPromptWithNudge]);

  const handleVoicePress = useCallback(async () => {
    if (completionSummary || pendingCompletionSummary || isBusy || isStartingRecording) {
      return;
    }

    try {
      if (!isRecording) {
        setVoiceError(null);
        await startRecording();
        return;
      }
      await voiceReplyMutation.mutateAsync();
    } catch (error) {
      setVoiceStatus('idle');
      setVoiceError(error instanceof Error ? error.message : 'Voice recording failed.');
    }
  }, [
    completionSummary,
    pendingCompletionSummary,
    isBusy,
    isRecording,
    isStartingRecording,
    setVoiceError,
    startRecording,
    voiceReplyMutation,
  ]);

  if (!sessionId) {
    return (
      <ScreenContainer edges={['right', 'left', 'bottom']}>
        <EmptyState
          icon="💬"
          title="Conversation session unavailable"
          description="Start a new roleplay scenario from the Practice tab."
        />
        <PrimaryButton label="Back to Practice" onPress={() => router.replace('/(app)/(tabs)/practice')} />
      </ScreenContainer>
    );
  }

  if (completionSummary) {
    return (
      <ScreenContainer scroll edges={['right', 'left', 'bottom']}>
        <View style={[styles.completeCard, shadows.md]}>
          <Text style={styles.completeEmoji}>🎉</Text>
          <Text style={styles.completeTitle}>Conversation Complete</Text>
          <Text style={styles.completeBody}>
            You finished your {title.toLowerCase()} voice practice session. Keep the same energy in
            the next roleplay.
          </Text>
        </View>

        <View style={styles.summaryRow}>
          <View style={[styles.summaryMetricCard, shadows.sm]}>
            <Text style={styles.summaryMetricValue}>{completionSummary.average_score}</Text>
            <Text style={styles.summaryMetricLabel}>Average score</Text>
          </View>
          <View style={[styles.summaryMetricCard, shadows.sm]}>
            <Text style={styles.summaryMetricValue}>{maxTurns}</Text>
            <Text style={styles.summaryMetricLabel}>Turns completed</Text>
          </View>
        </View>

        <View style={[styles.feedbackCard, shadows.sm]}>
          <Text style={styles.feedbackTitle}>Session summary</Text>
          <View style={styles.summaryList}>
            <Text style={styles.feedbackText}>
              Strong area: {formatLearningAreaLabel(completionSummary.best_area)}
            </Text>
            <Text style={styles.feedbackText}>
              Weak area: {formatLearningAreaLabel(completionSummary.weak_area)}
            </Text>
            <Text style={styles.feedbackText}>Tip: {completionSummary.tip}</Text>
          </View>
        </View>

        <View style={styles.completeActions}>
          <PrimaryButton label="Practice Again" onPress={() => router.replace('/(app)/conversation-scenarios')} />
          <PrimaryButton
            label="Back to Home"
            variant="secondary"
            onPress={() => router.replace('/(app)/(tabs)')}
          />
        </View>
      </ScreenContainer>
    );
  }

  if (pendingCompletionSummary) {
    return (
      <ScreenContainer scroll edges={['right', 'left', 'bottom']}>
        <View style={[styles.completeCard, shadows.md]}>
          <Text style={styles.completeEmoji}>🌟</Text>
          <Text style={styles.completeTitle}>You’ve got this level.</Text>
          <Text style={styles.completeBody}>
            You handled this conversation well. Want to finish here, or keep practicing the same
            level once more?
          </Text>
        </View>

        <View style={styles.summaryRow}>
          <View style={[styles.summaryMetricCard, shadows.sm]}>
            <Text style={styles.summaryMetricValue}>{pendingCompletionSummary.average_score}</Text>
            <Text style={styles.summaryMetricLabel}>Average score</Text>
          </View>
          <View style={[styles.summaryMetricCard, shadows.sm]}>
            <Text style={styles.summaryMetricValue}>{maxTurns}</Text>
            <Text style={styles.summaryMetricLabel}>Turns finished</Text>
          </View>
        </View>

        <View style={[styles.feedbackCard, shadows.sm]}>
          <Text style={styles.feedbackTitle}>Before you move on</Text>
          <View style={styles.summaryList}>
            <Text style={styles.feedbackText}>
              Strong area: {formatLearningAreaLabel(pendingCompletionSummary.best_area)}
            </Text>
            <Text style={styles.feedbackText}>
              Keep improving: {formatLearningAreaLabel(pendingCompletionSummary.weak_area)}
            </Text>
            <Text style={styles.feedbackText}>{pendingCompletionSummary.tip}</Text>
          </View>
        </View>

        <View style={styles.completeActions}>
          <PrimaryButton
            label="Continue Same Level"
            onPress={() => continuePracticeMutation.mutate()}
            loading={continuePracticeMutation.isPending}
            disabled={continuePracticeMutation.isPending}
          />
          <PrimaryButton
            label="Complete Practice"
            variant="secondary"
            onPress={() => {
              setCompletionSummary(pendingCompletionSummary);
              setPendingCompletionSummary(null);
            }}
          />
        </View>

        {continuePracticeMutation.error ? (
          <Text style={styles.footerError}>
            {continuePracticeMutation.error instanceof Error
              ? continuePracticeMutation.error.message
              : 'Could not continue the same level right now.'}
          </Text>
        ) : null}
      </ScreenContainer>
    );
  }

  const typingFooter = typingMode ? (
    <View style={styles.footer}>
      {voiceError ? <Text style={styles.footerError}>{voiceError}</Text> : null}
      <View style={styles.textFooter}>
        <TextInput
          multiline
          value={draft}
          onChangeText={setDraft}
          placeholder="Type your answer in English…"
          placeholderTextColor={colors.text.tertiary}
          style={styles.input}
          editable={!isBusy}
        />
        <View style={styles.textFooterActions}>
          <PrimaryButton
            label="Send"
            onPress={() => replyMutation.mutate(draft.trim())}
            disabled={draft.trim().length === 0 || isBusy}
            loading={replyMutation.isPending}
          />
          <PrimaryButton
            label="Use Voice"
            variant="secondary"
            onPress={() => setTypingMode(false)}
          />
        </View>
      </View>
    </View>
  ) : null;

  return (
    <ScreenContainer footer={typingFooter} edges={['right', 'left', 'bottom']}>
      <View style={styles.headerCard}>
        <View style={styles.headerTopRow}>
          <View style={styles.headerCopy}>
            <Text style={styles.headerTitle}>{title}</Text>
          </View>
          <View style={styles.turnPill}>
            <Text style={styles.turnPillText}>Turn {turnLabel}</Text>
          </View>
        </View>
        <View style={styles.headerMetaRow}>
          <View style={styles.metaPill}>
            <MaterialCommunityIcons name="signal" size={14} color={colors.primary[700]} />
            <Text style={styles.metaPillText}>{level.replace(/_/g, ' ')}</Text>
          </View>
          <Pressable
            onPress={() => exitConversationMutation.mutate()}
            disabled={exitConversationMutation.isPending}
            style={({ pressed }) => [
              styles.leavePill,
              exitConversationMutation.isPending && styles.leavePillDisabled,
              pressed && !exitConversationMutation.isPending && styles.leavePillPressed,
            ]}>
            <MaterialCommunityIcons name="logout-variant" size={14} color={colors.error} />
            <Text style={styles.leavePillText}>
              {exitConversationMutation.isPending ? 'Leaving' : 'Leave'}
            </Text>
          </Pressable>
        </View>
      </View>

      <View style={[styles.controlCard, shadows.sm]}>
        <View style={styles.controlStatusRowCompact}>
          <View style={styles.livePill}>
            <MaterialCommunityIcons name={stageCopy.icon} size={14} color={colors.primary[700]} />
            <Text style={styles.livePillText}>{stageCopy.chip}</Text>
          </View>
          <View style={styles.livePill}>
            <MaterialCommunityIcons
              name={isVoiceCapturing ? 'record-rec' : speakingMessageId ? 'volume-high' : 'microphone-outline'}
              size={14}
              color={colors.primary[700]}
            />
            <Text style={styles.livePillText}>
              Turn {turnLabel}
            </Text>
          </View>
        </View>
        <View style={styles.voiceStage}>
          <View style={styles.stageVisualWrap}>
            <Animated.View style={[styles.voiceRing, ringAnimatedStyle]} />
            <Animated.View
              style={[
                styles.voiceOrb,
                stageMode === 'listening' && styles.voiceOrbActive,
                (isBusy || isStartingRecording) && styles.voiceOrbDisabled,
                orbAnimatedStyle,
              ]}>
              {stageMode === 'processing' ? (
                <Animated.View style={spinnerAnimatedStyle}>
                  <MaterialCommunityIcons name="progress-clock" size={36} color={colors.text.inverse} />
                </Animated.View>
              ) : (
                <MaterialCommunityIcons
                  name={stageMode === 'speaking' ? 'volume-high' : isRecording ? 'microphone' : 'microphone-outline'}
                  size={38}
                  color={colors.text.inverse}
                />
              )}
            </Animated.View>
          </View>
          <View style={styles.controlCopyCompact}>
            <Text style={styles.controlTitleCompact}>{stageCopy.title}</Text>
            <Text style={styles.voiceStatusTextCompact}>{stageCopy.hint}</Text>
            {stageMode === 'listening' ? (
              <Text style={styles.voiceModeMeta}>
                {isStartingRecording
                  ? 'Starting mic...'
                  : `${Math.max(1, Math.floor(recordingDurationMs / 1000))}s`}
              </Text>
            ) : null}
          </View>
          <View style={styles.waveRow}>
            {waveValues.map((value, index) => (
              <Animated.View
                key={index}
                style={[
                  styles.waveBar,
                  {
                    opacity: stageMode === 'processing' ? 0.4 : stageMode === 'ready' ? 0.18 : 0.9,
                    transform: [
                      {
                        scaleY:
                          stageMode === 'listening' && typeof recordingMetering === 'number'
                            ? Math.max(
                                0.35,
                                Math.min(1.4, 1 + (recordingMetering + 60) / 18 + index * 0.02)
                              )
                            : value,
                      },
                    ],
                  },
                ]}
              />
            ))}
          </View>
        </View>
        <Pressable
          onPress={() => void handleVoicePress()}
          disabled={isBusy || isStartingRecording}
          style={({ pressed }) => [
            styles.primaryVoiceAction,
            isVoiceCapturing && styles.primaryVoiceActionActive,
            (isBusy || isStartingRecording) && styles.primaryVoiceActionDisabled,
            pressed && !isBusy && !isStartingRecording && styles.primaryVoiceActionPressed,
          ]}>
          <MaterialCommunityIcons
            name={isBusy ? 'progress-clock' : isRecording ? 'stop-circle-outline' : 'microphone'}
            size={22}
            color={colors.text.inverse}
          />
          <Text style={styles.primaryVoiceActionText}>
            {isBusy
              ? 'Processing'
              : isStartingRecording
                ? 'Starting mic'
                : isRecording
                  ? 'Send answer'
                  : 'Speak'}
          </Text>
        </Pressable>
        <View style={styles.inlineActionsRow}>
          <Pressable
            onPress={() => void speakAssistantMessage(currentCoachMessage.id, currentCoachMessage.text, { language: 'en' })}
            style={styles.inlineActionButton}>
            <MaterialCommunityIcons name="volume-high" size={18} color={colors.primary[700]} />
            <Text style={styles.inlineActionText}>{speakingMessageId === currentCoachMessage.id ? 'Stop' : 'Replay'}</Text>
          </Pressable>
          <Pressable onPress={() => setTypingMode(true)} style={styles.inlineActionButton}>
            <MaterialCommunityIcons name="keyboard-outline" size={18} color={colors.primary[700]} />
            <Text style={styles.inlineActionText}>Type</Text>
          </Pressable>
          <Pressable onPress={() => setDetailsOpen((value) => !value)} style={styles.inlineActionButton}>
            <MaterialCommunityIcons name="text-box-search-outline" size={18} color={colors.primary[700]} />
            <Text style={styles.inlineActionText}>{detailsOpen ? 'Hide' : 'Details'}</Text>
          </Pressable>
        </View>
        {voiceError ? <Text style={styles.inlineError}>{voiceError}</Text> : null}
      </View>

      {detailsOpen ? (
        <ScrollView
          style={styles.detailsScroll}
          contentContainerStyle={styles.detailsContent}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}>
          <View style={[styles.promptCard, shadows.sm]}>
            <View style={styles.promptHeader}>
              <Text style={styles.promptLabel}>Coach prompt</Text>
            </View>
            <Text style={styles.promptText}>{currentCoachMessage.text}</Text>
          </View>

          {lastTranscript ? (
            <View style={[styles.transcriptPreviewCard, shadows.sm]}>
              <Text style={styles.transcriptPreviewLabel}>You said</Text>
              <Text style={styles.transcriptPreviewText}>{lastTranscript}</Text>
            </View>
          ) : null}

          {lastFeedback ? (
            <View style={[styles.feedbackCard, shadows.sm]}>
              <View style={styles.feedbackHeader}>
                <Text style={styles.feedbackTitle}>Turn feedback</Text>
                <StatusBadge
                  label={lastFeedback.feedback_level.replace('_', ' ')}
                  tone={feedbackTone}
                />
              </View>
              <Text style={styles.feedbackScore}>Score: {lastFeedback.score}</Text>
              <Text style={styles.feedbackBlockLabel}>Corrected sentence</Text>
              <Text style={styles.feedbackText}>{lastFeedback.corrected_sentence}</Text>
              <Text style={styles.feedbackBlockLabel}>Natural sentence</Text>
              <Text style={styles.feedbackText}>{lastFeedback.natural_sentence}</Text>
              {lastFeedback.mistakes.length > 0 ? (
                <>
                  <Text style={styles.feedbackBlockLabel}>Mistakes</Text>
                  <View style={styles.mistakeList}>
                    {lastFeedback.mistakes.map((mistake, index) => (
                      <View key={`${mistake.type}-${index}`} style={styles.mistakeItem}>
                        <Text style={styles.mistakeType}>{formatLearningAreaLabel(mistake.type)}</Text>
                        <Text style={styles.feedbackText}>
                          {mistake.issue} → {mistake.fix}
                        </Text>
                        <Text style={styles.feedbackReason}>{mistake.reason}</Text>
                      </View>
                    ))}
                  </View>
                </>
              ) : null}
              <Text style={styles.feedbackBlockLabel}>Encouragement</Text>
              <Text style={styles.feedbackText}>{lastFeedback.encouragement}</Text>
            </View>
          ) : (
            <View style={[styles.feedbackCard, shadows.sm]}>
              <Text style={styles.feedbackTitle}>No turn details yet</Text>
              <Text style={styles.feedbackText}>
                Speak your first answer and the transcript, corrections, and feedback will appear here.
              </Text>
            </View>
          )}

          <View style={[styles.historyCard, shadows.sm]}>
            <Text style={styles.feedbackTitle}>Conversation text</Text>
            <View style={styles.historyList}>
              {messages.map((message) => (
                <View
                  key={message.id}
                  style={[
                    styles.historyBubble,
                    message.role === 'user' ? styles.historyBubbleUser : styles.historyBubbleAi,
                  ]}>
                  <Text style={styles.historyRole}>{message.role === 'user' ? 'You' : 'Coach'}</Text>
                  <Text
                    style={[
                      styles.historyText,
                      message.role === 'user' ? styles.historyTextUser : styles.historyTextAi,
                    ]}>
                    {message.text}
                  </Text>
                </View>
              ))}
            </View>
          </View>
        </ScrollView>
      ) : null}
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  headerCard: {
    backgroundColor: colors.bg.card,
    borderRadius: radii.xl,
    padding: spacing.lg,
    gap: spacing.sm,
  },
  headerTopRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: spacing.md,
  },
  headerCopy: {
    flex: 1,
    gap: spacing.xs,
  },
  headerTitle: {
    ...typography.subheading,
    color: colors.text.primary,
  },
  headerMetaRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  metaPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: radii.full,
    backgroundColor: colors.primary[50],
  },
  metaPillText: {
    ...typography.captionBold,
    color: colors.primary[700],
    textTransform: 'capitalize',
  },
  leavePill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: radii.full,
    borderWidth: 1,
    borderColor: colors.border.light,
    backgroundColor: colors.bg.card,
  },
  leavePillText: {
    ...typography.captionBold,
    color: colors.error,
  },
  leavePillDisabled: {
    opacity: 0.6,
  },
  leavePillPressed: {
    opacity: 0.82,
  },
  turnPill: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radii.full,
    backgroundColor: colors.primary[50],
  },
  turnPillText: {
    ...typography.captionBold,
    color: colors.primary[700],
  },
  voiceStatusText: {
    ...typography.body,
    color: colors.text.secondary,
  },
  voiceModeMeta: {
    ...typography.captionBold,
    color: colors.primary[700],
  },
  promptCard: {
    backgroundColor: colors.bg.card,
    borderRadius: radii.xl,
    padding: spacing.xl,
    gap: spacing.sm,
  },
  promptHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.sm,
  },
  promptLabel: {
    ...typography.captionBold,
    color: colors.text.tertiary,
    textTransform: 'uppercase',
  },
  replayPill: {
    borderRadius: radii.full,
    backgroundColor: colors.primary[50],
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  replayPillText: {
    ...typography.captionBold,
    color: colors.primary[700],
  },
  promptText: {
    ...typography.bodyLg,
    color: colors.text.primary,
    lineHeight: 24,
  },
  transcriptPreviewCard: {
    backgroundColor: colors.primary[50],
    borderRadius: radii.xl,
    padding: spacing.lg,
    gap: spacing.xs,
  },
  transcriptPreviewLabel: {
    ...typography.captionBold,
    color: colors.primary[700],
    textTransform: 'uppercase',
  },
  transcriptPreviewText: {
    ...typography.body,
    color: colors.text.primary,
  },
  detailsScroll: {
    flex: 1,
  },
  detailsContent: {
    gap: spacing.md,
    paddingBottom: spacing.xl,
  },
  feedbackCard: {
    backgroundColor: colors.bg.card,
    borderRadius: radii.xl,
    padding: spacing.xl,
    gap: spacing.sm,
  },
  feedbackHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: spacing.md,
  },
  feedbackTitle: {
    ...typography.subheading,
    color: colors.text.primary,
  },
  feedbackScore: {
    ...typography.bodyLgBold,
    color: colors.primary[700],
  },
  feedbackBlockLabel: {
    ...typography.captionBold,
    color: colors.text.tertiary,
    textTransform: 'uppercase',
    marginTop: spacing.xs,
  },
  feedbackText: {
    ...typography.body,
    color: colors.text.primary,
  },
  mistakeList: {
    gap: spacing.sm,
  },
  mistakeItem: {
    gap: spacing.xxs,
  },
  mistakeType: {
    ...typography.bodyMedium,
    color: colors.text.primary,
  },
  feedbackReason: {
    ...typography.body,
    color: colors.text.secondary,
  },
  historyCard: {
    backgroundColor: colors.bg.card,
    borderRadius: radii.xl,
    padding: spacing.xl,
    gap: spacing.md,
  },
  historyList: {
    gap: spacing.sm,
  },
  historyBubble: {
    borderRadius: radii.xl,
    padding: spacing.md,
    gap: spacing.xs,
  },
  historyBubbleAi: {
    backgroundColor: colors.bg.base,
  },
  historyBubbleUser: {
    backgroundColor: colors.primary[600],
  },
  historyRole: {
    ...typography.captionBold,
    textTransform: 'uppercase',
    color: colors.text.tertiary,
  },
  historyText: {
    ...typography.body,
  },
  historyTextAi: {
    color: colors.text.primary,
  },
  historyTextUser: {
    color: colors.text.inverse,
  },
  statusBadge: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: radii.full,
  },
  statusBadgeGood: {
    backgroundColor: colors.primary[50],
  },
  statusBadgeWarn: {
    backgroundColor: '#FFF4E8',
  },
  statusBadgeGreat: {
    backgroundColor: '#EAF9F0',
  },
  statusBadgeText: {
    ...typography.captionBold,
    color: colors.text.primary,
    textTransform: 'capitalize',
  },
  footer: {
    gap: spacing.sm,
  },
  footerError: {
    ...typography.body,
    color: colors.error,
  },
  controlCard: {
    backgroundColor: colors.bg.card,
    borderRadius: radii.xl,
    padding: spacing.lg,
    gap: spacing.md,
  },
  controlStatusRowCompact: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.sm,
  },
  voiceStage: {
    alignItems: 'center',
    gap: spacing.md,
  },
  stageVisualWrap: {
    width: 132,
    height: 132,
    alignItems: 'center',
    justifyContent: 'center',
  },
  voiceRing: {
    position: 'absolute',
    width: 132,
    height: 132,
    borderRadius: 66,
    borderWidth: 2,
    borderColor: colors.primary[200],
    backgroundColor: colors.primary[50],
  },
  controlCopyCompact: {
    gap: spacing.xxs,
    alignItems: 'center',
  },
  controlTitleCompact: {
    ...typography.subheading,
    color: colors.text.primary,
    textAlign: 'center',
  },
  voiceStatusTextCompact: {
    ...typography.bodyMedium,
    color: colors.text.secondary,
    textAlign: 'center',
  },
  waveRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'center',
    gap: 6,
    minHeight: 22,
  },
  waveBar: {
    width: 6,
    height: 18,
    borderRadius: radii.full,
    backgroundColor: colors.primary[500],
  },
  inlineActionsRow: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  inlineActionButton: {
    borderRadius: radii.full,
    borderWidth: 1,
    borderColor: colors.border.light,
    backgroundColor: colors.bg.card,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
    gap: spacing.xs,
    flex: 1,
  },
  inlineActionText: {
    ...typography.captionBold,
    color: colors.primary[700],
  },
  inlineError: {
    ...typography.body,
    color: colors.error,
    textAlign: 'center',
  },
  livePill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: radii.full,
    backgroundColor: colors.primary[50],
  },
  livePillText: {
    ...typography.captionBold,
    color: colors.primary[700],
  },
  voiceOrb: {
    width: 96,
    height: 96,
    borderRadius: 48,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.primary[600],
    alignSelf: 'center',
    ...shadows.md,
  },
  voiceOrbActive: {
    backgroundColor: colors.primary[700],
    transform: [{ scale: 1.02 }],
  },
  voiceOrbDisabled: {
    opacity: 0.7,
  },
  voiceOrbPressed: {
    transform: [{ scale: 0.98 }],
  },
  primaryVoiceAction: {
    minHeight: 54,
    borderRadius: radii.full,
    backgroundColor: colors.primary[600],
    paddingHorizontal: spacing.lg,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
  },
  primaryVoiceActionActive: {
    backgroundColor: colors.primary[700],
  },
  primaryVoiceActionDisabled: {
    opacity: 0.72,
  },
  primaryVoiceActionPressed: {
    transform: [{ scale: 0.985 }],
  },
  primaryVoiceActionText: {
    ...typography.bodyLgBold,
    color: colors.text.inverse,
  },
  textFooter: {
    gap: spacing.sm,
  },
  textFooterActions: {
    gap: spacing.sm,
  },
  input: {
    minHeight: 112,
    maxHeight: 180,
    borderRadius: radii.xl,
    borderWidth: 1,
    borderColor: colors.border.light,
    backgroundColor: colors.bg.card,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    color: colors.text.primary,
    textAlignVertical: 'top',
    ...typography.body,
  },
  completeCard: {
    backgroundColor: colors.bg.card,
    borderRadius: radii.xl,
    padding: spacing['2xl'],
    alignItems: 'center',
    gap: spacing.sm,
  },
  completeEmoji: {
    fontSize: 42,
  },
  completeTitle: {
    ...typography.title,
    color: colors.text.primary,
    textAlign: 'center',
  },
  completeBody: {
    ...typography.bodyLg,
    color: colors.text.secondary,
    textAlign: 'center',
  },
  summaryRow: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  summaryMetricCard: {
    flex: 1,
    backgroundColor: colors.bg.card,
    borderRadius: radii.xl,
    padding: spacing.xl,
    gap: spacing.xs,
  },
  summaryMetricValue: {
    ...typography.display,
    color: colors.primary[700],
  },
  summaryMetricLabel: {
    ...typography.body,
    color: colors.text.secondary,
  },
  summaryList: {
    gap: spacing.sm,
  },
  completeActions: {
    gap: spacing.md,
  },
});
