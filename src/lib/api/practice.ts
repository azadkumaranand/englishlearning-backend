import { ApiError, apiRequest, apiStreamRequest } from '@/src/lib/api/client';
import type {
  ChatRequestMetadata,
  ChatResponse,
  CreatePracticeSessionPayload,
  MessageCorrection,
  PracticeSession,
  PracticeSessionDetail,
  VoiceChatResponse,
} from '@/src/lib/api/types';

export type PracticeChatStreamEvent =
  | {
      type: 'status';
      phase: 'received' | 'evaluating' | 'replying' | 'feedback';
      message: string;
    }
  | {
      type: 'assistant_delta';
      delta: string;
      snapshot: string;
    }
  | {
      type: 'final';
      data: ChatResponse;
    }
  | {
      type: 'error';
      detail: string;
    };

function isUuidLike(value: string) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
}

export const practiceApi = {
  createSession(token: string, payload: CreatePracticeSessionPayload) {
    return apiRequest<PracticeSessionDetail>('/practice/sessions', {
      method: 'POST',
      token,
      body: JSON.stringify(payload),
    });
  },
  listSessions(token: string) {
    return apiRequest<PracticeSession[]>('/practice/sessions', { token });
  },
  getSession(token: string, sessionId: string) {
    return apiRequest<PracticeSessionDetail>(`/practice/sessions/${sessionId}`, { token });
  },
  completeSession(token: string, sessionId: string) {
    return apiRequest<PracticeSessionDetail>(`/practice/sessions/${sessionId}/complete`, {
      method: 'PATCH',
      token,
    });
  },
  chat(token: string, sessionId: string, content: string, metadata?: ChatRequestMetadata | null) {
    return apiRequest<ChatResponse>(`/practice/sessions/${sessionId}/chat`, {
      method: 'POST',
      token,
      body: JSON.stringify({ content, metadata_json: metadata ?? undefined }),
    });
  },
  async chatStream(
    token: string,
    sessionId: string,
    content: string,
    metadata: ChatRequestMetadata | null | undefined,
    onEvent: (event: Exclude<PracticeChatStreamEvent, { type: 'final' }>) => void
  ): Promise<ChatResponse> {
    let finalResponse: ChatResponse | null = null;

    await apiStreamRequest<PracticeChatStreamEvent>(`/practice/sessions/${sessionId}/chat/stream`, {
      method: 'POST',
      token,
      body: JSON.stringify({ content, metadata_json: metadata ?? undefined }),
      onEvent: (event) => {
        if (event.type === 'final') {
          finalResponse = event.data;
          return;
        }
        if (event.type === 'error') {
          throw new ApiError(event.detail || 'Chat stream failed', 0, event);
        }
        onEvent(event);
      },
    });

    if (!finalResponse) {
      throw new ApiError('Chat stream ended without a final response.', 0, null);
    }

    return finalResponse;
  },
  voiceChat(token: string, sessionId: string, formData: FormData) {
    return apiRequest<VoiceChatResponse>(`/practice/sessions/${sessionId}/voice-chat`, {
      method: 'POST',
      token,
      body: formData,
    });
  },
  getCorrection(token: string, sessionId: string, messageId: string) {
    if (!isUuidLike(messageId)) {
      return Promise.resolve(null);
    }
    return apiRequest<MessageCorrection>(
      `/practice/sessions/${sessionId}/messages/${messageId}/correction`,
      { token }
    );
  },
};
