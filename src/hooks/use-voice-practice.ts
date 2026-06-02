import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import {
  AudioModule,
  AudioQuality,
  IOSOutputFormat,
  setAudioModeAsync,
  useAudioRecorder,
  useAudioRecorderState,
} from 'expo-audio';
import * as Speech from 'expo-speech';
import type { Voice } from 'expo-speech';

type CompletedRecording = {
  uri: string;
  durationMs: number | null;
  mimeType: string;
  fileName: string;
};

type SpeakMessageOptions = {
  language?: string | null;
  onDone?: () => void;
  onStopped?: () => void;
  onError?: () => void;
};

const VOICE_RECORDING_OPTIONS = {
  isMeteringEnabled: true,
  extension: '.m4a',
  sampleRate: 16000,
  numberOfChannels: 1,
  bitRate: 64000,
  android: {
    extension: '.m4a',
    sampleRate: 16000,
    outputFormat: 'mpeg4' as const,
    audioEncoder: 'aac' as const,
  },
  ios: {
    extension: '.m4a',
    sampleRate: 16000,
    outputFormat: IOSOutputFormat.MPEG4AAC,
    audioQuality: AudioQuality.HIGH,
  },
  web: {
    mimeType: 'audio/webm',
    bitsPerSecond: 64000,
  },
};

function inferAudioMimeType(uri: string): string {
  const lowerUri = uri.toLowerCase();
  if (lowerUri.endsWith('.m4a')) return 'audio/m4a';
  if (lowerUri.endsWith('.mp4')) return 'audio/mp4';
  if (lowerUri.endsWith('.aac')) return 'audio/aac';
  if (lowerUri.endsWith('.caf')) return 'audio/x-caf';
  if (lowerUri.endsWith('.wav')) return 'audio/wav';
  if (lowerUri.endsWith('.mp3')) return 'audio/mpeg';
  if (lowerUri.endsWith('.webm')) return 'audio/webm';
  if (lowerUri.endsWith('.ogg')) return 'audio/ogg';
  return 'audio/m4a';
}

function normalizeLanguageTag(language: string | null | undefined) {
  if (!language) return null;
  const normalized = language.trim().replace(/_/g, '-');
  return normalized.length > 0 ? normalized : null;
}

function pickVoiceForLanguage(voices: Voice[], language: string | null) {
  if (!language) return null;

  const normalizedTarget = language.toLowerCase();
  const exactMatch = voices.find((voice) => voice.language.toLowerCase() === normalizedTarget);
  if (exactMatch) {
    return exactMatch;
  }

  const targetBase = normalizedTarget.split('-')[0];
  return voices.find((voice) => voice.language.toLowerCase().split('-')[0] === targetBase) ?? null;
}

export function useVoicePractice() {
  const [isStartingRecording, setIsStartingRecording] = useState(false);
  const [isRecordingActive, setIsRecordingActive] = useState(false);
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [speakingMessageId, setSpeakingMessageId] = useState<string | null>(null);
  const [availableVoices, setAvailableVoices] = useState<Voice[]>([]);
  const speakingMessageIdRef = useRef<string | null>(null);
  const recorder = useAudioRecorder(VOICE_RECORDING_OPTIONS, (status) => {
    if (status.hasError && status.error) {
      setVoiceError(status.error);
      setIsStartingRecording(false);
      setIsRecordingActive(false);
    }
    if (status.isFinished) {
      setIsStartingRecording(false);
      setIsRecordingActive(false);
    }
  });
  const recorderState = useAudioRecorderState(recorder, 100);

  useEffect(() => {
    speakingMessageIdRef.current = speakingMessageId;
  }, [speakingMessageId]);

  useEffect(() => {
    let isMounted = true;

    void Speech.getAvailableVoicesAsync()
      .then((voices) => {
        if (isMounted) {
          setAvailableVoices(voices);
        }
      })
      .catch(() => {
        if (isMounted) {
          setAvailableVoices([]);
        }
      });

    return () => {
      isMounted = false;
      void Speech.stop();
    };
  }, []);

  const ensurePermissions = useCallback(async () => {
    const permission = await AudioModule.requestRecordingPermissionsAsync();
    if (!permission.granted) {
      throw new Error('Microphone permission is required for voice practice');
    }
  }, []);

  const waitForRecordingState = useCallback(
    async (predicate: (status: ReturnType<typeof recorder.getStatus>) => boolean, timeoutMs = 1500) => {
      const startedAt = Date.now();
      while (Date.now() - startedAt < timeoutMs) {
        const status = recorder.getStatus();
        if (predicate(status)) {
          return status;
        }
        await new Promise((resolve) => setTimeout(resolve, 50));
      }
      return recorder.getStatus();
    },
    [recorder]
  );

  const startRecording = useCallback(async () => {
    setVoiceError(null);
    setIsStartingRecording(true);
    try {
      await Speech.stop();
      setSpeakingMessageId(null);
      await ensurePermissions();
      await setAudioModeAsync({
        allowsRecording: true,
        playsInSilentMode: true,
        interruptionMode: 'doNotMix',
        shouldRouteThroughEarpiece: false,
      });
      await recorder.prepareToRecordAsync();
      recorder.record();
      const status = await waitForRecordingState((current) => current.isRecording);
      if (!status.isRecording) {
        throw new Error('Microphone did not start properly. Tap the mic again and speak after the beep.');
      }
      setIsRecordingActive(true);
    } finally {
      setIsStartingRecording(false);
    }
  }, [ensurePermissions, recorder, waitForRecordingState]);

  const stopRecording = useCallback(async (): Promise<CompletedRecording> => {
    const activeStatus = recorder.getStatus();
    if (!activeStatus.isRecording) {
      throw new Error('Recording is not active yet. Wait a moment, then tap again to send your answer.');
    }

    try {
      await recorder.stop();
      const stoppedStatus = await waitForRecordingState((current) => !current.isRecording);
      await setAudioModeAsync({
        allowsRecording: false,
        playsInSilentMode: true,
      });

      const uri = recorder.uri;
      if (!uri) {
        throw new Error('Recording failed. Please try again.');
      }

      const durationMs = stoppedStatus.durationMillis || activeStatus.durationMillis || null;
      if (durationMs !== null && durationMs < 1200) {
        throw new Error('Recording was too short. Hold the mic for a moment, then speak for 2 to 5 seconds.');
      }

      const fileName = uri.split('/').pop() ?? `voice-${Date.now()}.m4a`;
      return {
        uri,
        durationMs,
        mimeType: inferAudioMimeType(uri),
        fileName,
      };
    } finally {
      setIsRecordingActive(false);
    }
  }, [recorder, waitForRecordingState]);

  const cancelRecording = useCallback(async () => {
    const activeStatus = recorder.getStatus();
    if (!activeStatus.isRecording) {
      setIsRecordingActive(false);
      return;
    }

    try {
      await recorder.stop();
      await waitForRecordingState((current) => !current.isRecording);
      await setAudioModeAsync({
        allowsRecording: false,
        playsInSilentMode: true,
      });
    } finally {
      setIsRecordingActive(false);
    }
  }, [recorder, waitForRecordingState]);

  const stopSpeaking = useCallback(async () => {
    setSpeakingMessageId(null);
    await Speech.stop();
  }, []);

  const speakAssistantMessage = useCallback(
    async (messageId: string, text: string, options?: SpeakMessageOptions) => {
      if (speakingMessageIdRef.current === messageId) {
        await stopSpeaking();
        return;
      }

      await Speech.stop();
      setSpeakingMessageId(messageId);
      const language = normalizeLanguageTag(options?.language);
      const matchingVoice = pickVoiceForLanguage(availableVoices, language);

      Speech.speak(text, {
        language: language ?? undefined,
        voice: matchingVoice?.identifier,
        rate: 0.96,
        pitch: 1,
        onDone: () => {
          setSpeakingMessageId(null);
          options?.onDone?.();
        },
        onStopped: () => {
          setSpeakingMessageId(null);
          options?.onStopped?.();
        },
        onError: () => {
          setSpeakingMessageId(null);
          setVoiceError('Assistant audio playback is unavailable right now');
          options?.onError?.();
        },
      });
    },
    [availableVoices, stopSpeaking]
  );

  return useMemo(
    () => ({
      voiceError,
      setVoiceError,
      isStartingRecording,
      isRecording: isRecordingActive || recorderState.isRecording,
      recordingDurationMs: recorderState.durationMillis ?? 0,
      recordingMetering: recorderState.metering ?? null,
      startRecording,
      stopRecording,
      cancelRecording,
      speakingMessageId,
      speakAssistantMessage,
      stopSpeaking,
    }),
    [
      isStartingRecording,
      isRecordingActive,
      recorderState.durationMillis,
      recorderState.isRecording,
      recorderState.metering,
      speakAssistantMessage,
      speakingMessageId,
      startRecording,
      stopRecording,
      cancelRecording,
      stopSpeaking,
      voiceError,
    ]
  );
}
