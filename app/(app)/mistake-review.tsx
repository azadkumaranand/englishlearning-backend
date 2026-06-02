import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import Animated, { FadeInUp, Layout } from 'react-native-reanimated';
import { Feather, Ionicons } from '@expo/vector-icons';

import { EmptyState } from '@/src/components/empty-state';
import { LoadingScreen } from '@/src/components/loading-screen';
import { PrimaryButton } from '@/src/components/primary-button';
import { ScreenContainer } from '@/src/components/screen-container';
import { useAuth } from '@/src/hooks/use-auth';
import { useVoicePractice } from '@/src/hooks/use-voice-practice';
import { mistakesApi } from '@/src/lib/api/mistakes';
import { practiceApi } from '@/src/lib/api/practice';
import type { MistakeRetryResponse } from '@/src/lib/api/types';
import { queryClient } from '@/src/lib/query-client';
import { formatLearningAreaLabel } from '@/src/lib/learning-profile';
import { colors, radii, shadows, spacing, typography, fontWeights } from '@/src/theme';

function renderFormattedExplanation(text: string | null | undefined) {
  if (!text) return null;
  const parts = text.split(/('[^']+'|"[^"]+")/g);
  return (
    <Text style={styles.explanationText}>
      {parts.map((part, index) => {
        const isQuoted = (part.startsWith("'") && part.endsWith("'")) || (part.startsWith('"') && part.endsWith('"'));
        if (isQuoted) {
          return (
            <Text key={index} style={styles.highlightedWord}>
              {part}
            </Text>
          );
        }
        return part;
      })}
    </Text>
  );
}

export default function MistakeReviewScreen() {
  const auth = useAuth();
  const router = useRouter();
  const globalQueryClient = useQueryClient();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answer, setAnswer] = useState('');
  const [currentResult, setCurrentResult] = useState<MistakeRetryResponse | null>(null);
  const [completedResults, setCompletedResults] = useState<Record<string, MistakeRetryResponse>>({});
  const [voiceTranscript, setVoiceTranscript] = useState<string | null>(null);
  const [inputFocused, setInputFocused] = useState(false);
  
  const {
    voiceError,
    setVoiceError,
    isRecording,
    recordingDurationMs,
    startRecording,
    stopRecording,
  } = useVoicePractice();

  const reviewQuery = useQuery({
    queryKey: ['mistakes-review', 'screen'],
    queryFn: () => auth.authorizedRequest((token) => mistakesApi.getReview(token)),
  });

  const startTranslationSessionMutation = useMutation({
    mutationFn: () =>
      auth.authorizedRequest((token) =>
        practiceApi.createSession(token, {
          mode: 'translation_practice',
          title: 'Translation Practice',
        })
      ),
    onSuccess: (session) => {
      queryClient.setQueryData(['practice-session', session.id], session);
      router.replace(`/(app)/session/${session.id}`);
    },
  });

  const retryMutation = useMutation({
    mutationFn: ({
      mistakeId,
      retryAnswer,
    }: {
      mistakeId: string;
      retryAnswer: string;
    }) =>
      auth.authorizedRequest((token) =>
        mistakesApi.retry(token, {
          mistake_id: mistakeId,
          retry_answer: retryAnswer,
          input_mode: 'text',
        })
      ),
    onSuccess: (result) => {
      setCurrentResult(result);
      setVoiceError(null);
      void globalQueryClient.invalidateQueries({ queryKey: ['learning-profile'] });
      void globalQueryClient.invalidateQueries({ queryKey: ['mistakes-review'] });
    },
  });

  const voiceRetryMutation = useMutation({
    mutationFn: async ({ mistakeId }: { mistakeId: string }) => {
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
      formData.append('source', 'mistake-review');
      return auth.authorizedRequest((token) => mistakesApi.retryVoice(token, mistakeId, formData));
    },
    onSuccess: (response) => {
      setVoiceTranscript(response.transcript);
      setCurrentResult(response.result);
      setAnswer(response.transcript);
      setVoiceError(null);
      void globalQueryClient.invalidateQueries({ queryKey: ['learning-profile'] });
      void globalQueryClient.invalidateQueries({ queryKey: ['mistakes-review'] });
    },
    onError: (error) => {
      setVoiceError(error instanceof Error ? error.message : 'Voice retry failed');
    },
  });

  const mistakes = reviewQuery.data?.mistakes ?? [];
  const currentMistake = mistakes[currentIndex] ?? null;
  const isFinished = mistakes.length > 0 && currentIndex >= mistakes.length;
  const improvedCount = useMemo(
    () => Object.values(completedResults).filter((result) => result.status === 'improved').length,
    [completedResults]
  );
  const stillNeedPracticeCount = useMemo(
    () => Object.values(completedResults).filter((result) => result.status !== 'improved').length,
    [completedResults]
  );

  const handleSubmit = () => {
    if (!currentMistake || !answer.trim() || retryMutation.isPending || voiceRetryMutation.isPending) {
      return;
    }
    retryMutation.mutate({
      mistakeId: currentMistake.id,
      retryAnswer: answer.trim(),
    });
  };

  const handleVoicePress = async () => {
    if (!currentMistake || retryMutation.isPending || voiceRetryMutation.isPending) {
      return;
    }

    try {
      if (!isRecording) {
        setVoiceError(null);
        await startRecording();
        return;
      }
      await voiceRetryMutation.mutateAsync({ mistakeId: currentMistake.id });
    } catch (error) {
      setVoiceError(error instanceof Error ? error.message : 'Voice retry failed');
    }
  };

  const handleNextMistake = () => {
    if (!currentMistake || !currentResult) {
      return;
    }
    setCompletedResults((current) => ({
      ...current,
      [currentMistake.id]: currentResult,
    }));
    setCurrentIndex((index) => index + 1);
    setCurrentResult(null);
    setAnswer('');
    setVoiceTranscript(null);
    setVoiceError(null);
  };

  const handleTryAgain = () => {
    setCurrentResult(null);
    setVoiceTranscript(null);
    setVoiceError(null);
  };

  if (reviewQuery.isLoading) {
    return <LoadingScreen message="Preparing your mistake review…" />;
  }

  if (reviewQuery.error) {
    return (
      <ScreenContainer edges={['right', 'left', 'bottom']}>
        <EmptyState
          icon={<Feather name="alert-octagon" size={48} color={colors.error} />}
          title="Review unavailable"
          description="We could not load your saved mistakes right now."
        />
        <PrimaryButton label="Retry" onPress={() => void reviewQuery.refetch()} />
      </ScreenContainer>
    );
  }

  if (mistakes.length === 0) {
    return (
      <ScreenContainer edges={['right', 'left', 'bottom']}>
        <EmptyState
          icon={<Ionicons name="sparkles" size={54} color={colors.success} />}
          title="All cleaned up!"
          description="No mistakes to review right now. Excellent job!"
        />
        <View style={styles.emptyStateAction}>
          <PrimaryButton label="Back to Home" onPress={() => router.replace('/(app)/(tabs)')} variant="secondary" />
        </View>
      </ScreenContainer>
    );
  }

  if (isFinished) {
    return (
      <ScreenContainer scroll edges={['right', 'left', 'bottom']}>
        <Animated.View entering={FadeInUp.delay(100).springify()} style={[styles.summaryCard, shadows.md]}>
          <LinearGradient
            colors={colors.gradients.hero}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={styles.summaryGradient}
          >
            <Ionicons name="trophy" size={44} color={colors.gold[300]} style={styles.trophyIcon} />
            <Text style={styles.summaryTitle}>Review complete!</Text>
            <Text style={styles.summaryBody}>
              You have completed this review set.
            </Text>
            
            <View style={styles.summaryStatsRow}>
              <View style={styles.summaryStatItem}>
                <Text style={styles.summaryStatVal}>{improvedCount}</Text>
                <Text style={styles.summaryStatLabel}>Improved</Text>
              </View>
              <View style={styles.summaryStatDivider} />
              <View style={styles.summaryStatItem}>
                <Text style={styles.summaryStatVal}>{stillNeedPracticeCount}</Text>
                <Text style={styles.summaryStatLabel}>Need Practice</Text>
              </View>
            </View>
          </LinearGradient>
        </Animated.View>

        <View style={styles.summaryActions}>
          <PrimaryButton
            label="Practice Translation"
            onPress={() => startTranslationSessionMutation.mutate()}
            loading={startTranslationSessionMutation.isPending}
            icon={<Feather name="edit-3" size={18} color={colors.text.inverse} />}
          />
          <PrimaryButton
            label="Back to Home"
            onPress={() => router.replace('/(app)/(tabs)')}
            variant="secondary"
            icon={<Feather name="home" size={18} color={colors.text.primary} />}
          />
        </View>
      </ScreenContainer>
    );
  }

  if (!currentMistake) {
    return (
      <ScreenContainer edges={['right', 'left', 'bottom']}>
        <EmptyState icon="❓" title="No review item found" description="Please go back and try again." />
      </ScreenContainer>
    );
  }

  const isSubmitting = retryMutation.isPending || voiceRetryMutation.isPending;
  const progressPercent = ((currentIndex) / mistakes.length) * 100;

  return (
    <ScreenContainer scroll edges={['right', 'left', 'bottom']}>
      {/* Visual Progress Bar */}
      <View style={styles.progressHeader}>
        <View style={styles.progressLabelRow}>
          <Text style={styles.progressText}>
            Reviewing {currentIndex + 1} of {mistakes.length}
          </Text>
          <View style={styles.focusPill}>
            <Text style={styles.focusPillText}>
              {formatLearningAreaLabel(currentMistake.focus_area)}
            </Text>
          </View>
        </View>
        <View style={styles.progressBarBg}>
          <Animated.View style={[styles.progressBarFill, { width: `${progressPercent}%` }]} layout={Layout.springify()} />
        </View>
      </View>

      {/* Side-by-side / Stacked Visual Comparison Card */}
      <Animated.View entering={FadeInUp.delay(150).springify()} style={[styles.comparisonCard, shadows.sm]}>
        {/* Wrong Sentence Block */}
        <View style={[styles.sentenceBlock, styles.wrongBlock]}>
          <View style={styles.blockHeader}>
            <Ionicons name="close-circle" size={18} color={colors.error} />
            <Text style={[styles.blockLabel, { color: colors.error }]}>Wrong Sentence</Text>
          </View>
          <Text style={styles.sentenceText}>{currentMistake.wrong_sentence}</Text>
        </View>

        {/* Correct Sentence Block */}
        <View style={[styles.sentenceBlock, styles.correctBlock]}>
          <View style={styles.blockHeader}>
            <Ionicons name="checkmark-circle" size={18} color={colors.success} />
            <Text style={[styles.blockLabel, { color: colors.success }]}>Correct Sentence</Text>
          </View>
          <Text style={styles.sentenceText}>{currentMistake.correct_sentence}</Text>
        </View>

        {/* Explanation Block */}
        <View style={styles.explanationBlock}>
          <View style={styles.explanationHeader}>
            <Ionicons name="bulb-outline" size={16} color={colors.primary[600]} />
            <Text style={styles.explanationLabel}>Grammar Lesson</Text>
          </View>
          {renderFormattedExplanation(currentMistake.explanation)}
        </View>
      </Animated.View>

      {/* Retry Question Card */}
      <Animated.View entering={FadeInUp.delay(200).springify()} style={[styles.questionCard, shadows.sm]}>
        <View style={styles.questionHeader}>
          <Ionicons name="sparkles" size={18} color={colors.primary[600]} />
          <Text style={styles.questionTitle}>Retry Challenge</Text>
        </View>
        <Text style={styles.questionBody}>{currentMistake.retry_question}</Text>
      </Animated.View>

      {/* Answer & Submission Card */}
      {!currentResult ? (
        <Animated.View entering={FadeInUp.delay(250).springify()} style={[styles.inputCard, shadows.sm]}>
          <TextInput
            multiline
            value={answer}
            onChangeText={setAnswer}
            placeholder="Type your corrected answer here…"
            placeholderTextColor={colors.text.tertiary}
            style={[styles.input, inputFocused && styles.inputActive]}
            editable={!isSubmitting && !isRecording}
            onFocus={() => setInputFocused(true)}
            onBlur={() => setInputFocused(false)}
          />

          <View style={styles.inputActions}>
            <Pressable
              onPress={() => void handleVoicePress()}
              disabled={isSubmitting}
              style={({ pressed }) => [
                styles.voiceButton,
                isRecording ? styles.voiceButtonRecording : styles.voiceButtonIdle,
                pressed && { opacity: 0.8 },
              ]}
            >
              <Feather name={isRecording ? 'square' : 'mic'} size={20} color={isRecording ? colors.error : colors.primary[600]} />
              <Text style={[styles.voiceButtonText, isRecording ? { color: colors.error } : { color: colors.primary[700] }]}>
                {isRecording ? `Stop (${Math.max(1, Math.floor(recordingDurationMs / 1000))}s)` : 'Speak'}
              </Text>
            </Pressable>

            <View style={styles.submitWrapper}>
              <PrimaryButton
                label="Submit"
                onPress={handleSubmit}
                loading={retryMutation.isPending}
                disabled={!answer.trim() || isRecording || voiceRetryMutation.isPending}
                icon={<Feather name="send" size={16} color={colors.text.inverse} />}
              />
            </View>
          </View>

          {voiceError ? <Text style={styles.errorText}>⚠️ {voiceError}</Text> : null}
        </Animated.View>
      ) : (
        /* Result & Feedback Card */
        <Animated.View entering={FadeInUp.delay(200).springify()} style={[styles.resultCard, shadows.md]}>
          <LinearGradient
            colors={currentResult.status === 'improved' ? ['#ecfdf5', '#f0fdf4'] : ['#fffbeb', '#fef3c7']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={[
              styles.resultGradient,
              { borderColor: currentResult.status === 'improved' ? colors.success + '40' : colors.gold[300] + '40' },
            ]}
          >
            <View style={styles.resultHeader}>
              <View style={styles.badgeRow}>
                <View
                  style={[
                    styles.resultBadge,
                    currentResult.status === 'improved' ? styles.badgeSuccess : styles.badgeWarning,
                  ]}
                >
                  <Text
                    style={[
                      styles.resultBadgeText,
                      currentResult.status === 'improved' ? styles.badgeTextSuccess : styles.badgeTextWarning,
                    ]}
                  >
                    {currentResult.status === 'improved' ? 'IMPROVED' : 'TRY AGAIN'}
                  </Text>
                </View>
              </View>
              <Text style={styles.resultScore}>Score: {currentResult.score}/100</Text>
            </View>

            {voiceTranscript ? (
              <View style={styles.speechMetaBlock}>
                <Text style={styles.speechMetaLabel}>Voice Transcript:</Text>
                <Text style={styles.speechMetaText}>{`"${voiceTranscript}"`}</Text>
              </View>
            ) : null}

            <View style={styles.feedbackDivider} />

            <View style={styles.feedbackRow}>
              <Text style={styles.cardLabel}>Correct Answer</Text>
              <Text style={styles.feedbackValue}>{currentResult.correct_answer}</Text>
            </View>

            {currentResult.natural_answer && (
              <View style={styles.feedbackRow}>
                <Text style={styles.cardLabel}>Alternative Natural Option</Text>
                <Text style={styles.feedbackValue}>{currentResult.natural_answer}</Text>
              </View>
            )}

            <View style={styles.feedbackRow}>
              <Text style={styles.cardLabel}>Tutor Feedback</Text>
              {renderFormattedExplanation(currentResult.feedback)}
            </View>

            {currentResult.remaining_issue ? (
              <View style={styles.feedbackRow}>
                <Text style={[styles.cardLabel, { color: colors.error }]}>Remaining Issue</Text>
                {renderFormattedExplanation(currentResult.remaining_issue)}
              </View>
            ) : null}

            <View style={styles.resultActions}>
              <Pressable style={styles.retryActionBtn} onPress={handleTryAgain}>
                <Feather name="refresh-cw" size={16} color={colors.text.secondary} />
                <Text style={styles.retryActionText}>Try Again</Text>
              </Pressable>
              
              <View style={styles.nextActionWrapper}>
                <PrimaryButton
                  label={currentIndex === mistakes.length - 1 ? 'Finish Review' : 'Next Mistake'}
                  onPress={handleNextMistake}
                  icon={<Feather name="arrow-right" size={16} color={colors.text.inverse} />}
                />
              </View>
            </View>
          </LinearGradient>
        </Animated.View>
      )}
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  progressHeader: {
    gap: spacing.xs,
    marginTop: spacing.xxs,
    marginBottom: spacing.xs,
  },
  progressLabelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  progressText: {
    ...typography.bodySemibold,
    color: colors.text.secondary,
  },
  focusPill: {
    backgroundColor: colors.primary[50],
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xxs,
    borderRadius: radii.full,
  },
  focusPillText: {
    ...typography.captionBold,
    color: colors.primary[700],
    textTransform: 'uppercase',
  },
  progressBarBg: {
    height: 6,
    backgroundColor: colors.neutral[100],
    borderRadius: radii.full,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    backgroundColor: colors.primary[500],
    borderRadius: radii.full,
  },
  comparisonCard: {
    backgroundColor: colors.bg.card,
    borderRadius: radii.xl,
    padding: spacing.lg,
    gap: spacing.md,
    marginBottom: spacing.md,
  },
  sentenceBlock: {
    padding: spacing.md,
    borderRadius: radii.lg,
    gap: spacing.xs,
  },
  wrongBlock: {
    backgroundColor: '#fff5f5',
    borderLeftWidth: 4,
    borderLeftColor: colors.error,
  },
  correctBlock: {
    backgroundColor: '#f0fdf4',
    borderLeftWidth: 4,
    borderLeftColor: colors.success,
  },
  blockHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  blockLabel: {
    ...typography.captionBold,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  sentenceText: {
    ...typography.bodyLgSemibold,
    color: colors.text.primary,
  },
  explanationBlock: {
    marginTop: spacing.sm,
    padding: spacing.md,
    borderRadius: radii.lg,
    backgroundColor: colors.primary[50] + '40', // soft translucent teal
    borderLeftWidth: 3,
    borderLeftColor: colors.primary[500],
    gap: spacing.xs,
  },
  explanationHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xxs,
  },
  explanationLabel: {
    ...typography.captionBold,
    color: colors.primary[700],
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  explanationText: {
    ...typography.bodyMedium,
    color: colors.primary[900], // High contrast dark slate-teal
    lineHeight: 22,
  },
  highlightedWord: {
    ...typography.bodyMedium,
    fontWeight: fontWeights.bold,
    color: colors.primary[700], // Highlight key words in vibrant teal
  },
  cardLabel: {
    ...typography.captionBold,
    color: colors.text.tertiary,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  questionCard: {
    backgroundColor: colors.bg.card,
    borderRadius: radii.xl,
    padding: spacing.lg,
    gap: spacing.xs,
    marginBottom: spacing.md,
    borderLeftWidth: 4,
    borderLeftColor: colors.primary[400],
  },
  questionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  questionTitle: {
    ...typography.bodySemibold,
    color: colors.text.secondary,
  },
  questionBody: {
    ...typography.bodyLgBold,
    color: colors.text.primary,
  },
  inputCard: {
    backgroundColor: colors.bg.card,
    borderRadius: radii.xl,
    padding: spacing.lg,
    gap: spacing.md,
    marginBottom: spacing.xl,
  },
  input: {
    minHeight: 100,
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.border.light,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    ...typography.body,
    color: colors.text.primary,
    textAlignVertical: 'top',
    backgroundColor: colors.neutral[50],
  },
  inputActive: {
    borderColor: colors.primary[400],
    backgroundColor: colors.bg.card,
  },
  inputActions: {
    flexDirection: 'row',
    gap: spacing.md,
    alignItems: 'center',
  },
  voiceButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.xs,
    height: 48,
    borderRadius: radii.lg,
    paddingHorizontal: spacing.lg,
    borderWidth: 1.5,
  },
  voiceButtonIdle: {
    backgroundColor: colors.primary[50],
    borderColor: colors.primary[100],
  },
  voiceButtonRecording: {
    backgroundColor: '#fff5f5',
    borderColor: colors.error + '40',
  },
  voiceButtonText: {
    ...typography.bodyMedium,
    fontWeight: fontWeights.bold,
  },
  submitWrapper: {
    flex: 1,
  },
  resultCard: {
    borderRadius: radii['2xl'],
    overflow: 'hidden',
    marginBottom: spacing.xl,
  },
  resultGradient: {
    padding: spacing.xl,
    gap: spacing.md,
    borderWidth: 1.5,
    borderRadius: radii['2xl'],
  },
  resultHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  badgeRow: {
    flexDirection: 'row',
  },
  resultBadge: {
    borderRadius: radii.full,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
  },
  badgeSuccess: {
    backgroundColor: colors.success + '20',
  },
  badgeWarning: {
    backgroundColor: colors.gold[100],
  },
  resultBadgeText: {
    ...typography.captionBold,
    letterSpacing: 1,
  },
  badgeTextSuccess: {
    color: colors.success,
  },
  badgeTextWarning: {
    color: colors.gold[600],
  },
  resultScore: {
    ...typography.bodyLgBold,
    color: colors.text.primary,
  },
  speechMetaBlock: {
    backgroundColor: 'rgba(0,0,0,0.03)',
    padding: spacing.sm,
    borderRadius: radii.md,
    gap: spacing.xxs,
  },
  speechMetaLabel: {
    ...typography.captionBold,
    color: colors.text.tertiary,
  },
  speechMetaText: {
    ...typography.body,
    fontStyle: 'italic',
    color: colors.text.secondary,
  },
  feedbackDivider: {
    height: 1,
    backgroundColor: 'rgba(0,0,0,0.06)',
    marginVertical: spacing.xxs,
  },
  feedbackRow: {
    gap: spacing.xxs,
  },
  feedbackValue: {
    ...typography.bodyLgSemibold,
    color: colors.text.primary,
  },
  feedbackExplanation: {
    ...typography.body,
    color: colors.text.secondary,
    lineHeight: 18,
  },
  resultActions: {
    flexDirection: 'row',
    gap: spacing.md,
    alignItems: 'center',
    marginTop: spacing.sm,
  },
  retryActionBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    height: 48,
    borderRadius: radii.lg,
    paddingHorizontal: spacing.lg,
    borderWidth: 1.5,
    borderColor: colors.border.light,
    backgroundColor: colors.neutral[0],
  },
  retryActionText: {
    ...typography.bodyMedium,
    fontWeight: fontWeights.bold,
    color: colors.text.secondary,
  },
  nextActionWrapper: {
    flex: 1,
  },
  summaryCard: {
    borderRadius: radii['2xl'],
    overflow: 'hidden',
    marginBottom: spacing.lg,
  },
  summaryGradient: {
    padding: spacing['2xl'],
    alignItems: 'center',
    gap: spacing.sm,
  },
  trophyIcon: {
    marginBottom: spacing.xs,
  },
  summaryTitle: {
    ...typography.title,
    color: colors.text.inverse,
  },
  summaryBody: {
    ...typography.bodyLg,
    color: colors.primary[100],
    textAlign: 'center',
  },
  summaryStatsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.15)',
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md,
    borderRadius: radii.xl,
    marginTop: spacing.md,
    width: '100%',
    justifyContent: 'space-around',
  },
  summaryStatItem: {
    alignItems: 'center',
    flex: 1,
  },
  summaryStatVal: {
    fontSize: 24,
    fontWeight: '800',
    color: colors.text.inverse,
  },
  summaryStatLabel: {
    ...typography.captionBold,
    color: colors.primary[100],
  },
  summaryStatDivider: {
    width: 1,
    height: 30,
    backgroundColor: 'rgba(255,255,255,0.2)',
  },
  summaryActions: {
    gap: spacing.md,
    marginBottom: spacing.xl,
  },
  emptyStateAction: {
    marginTop: spacing.md,
    paddingHorizontal: spacing.xl,
  },
  errorText: {
    ...typography.bodyMedium,
    color: colors.error,
  },
});
