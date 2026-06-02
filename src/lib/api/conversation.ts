import { apiRequest, apiUploadRequest } from '@/src/lib/api/client';
import type {
  ConversationReplyRequest,
  ConversationReplyResponse,
  ConversationSessionStateResponse,
  ConversationStartRequest,
  ConversationStartResponse,
  ConversationVoiceReplyResponse,
} from '@/src/lib/api/types';

export const conversationApi = {
  start(token: string, payload: ConversationStartRequest) {
    return apiRequest<ConversationStartResponse>('/conversation/start', {
      method: 'POST',
      token,
      body: JSON.stringify(payload),
    });
  },
  reply(token: string, payload: ConversationReplyRequest) {
    return apiRequest<ConversationReplyResponse>('/conversation/reply', {
      method: 'POST',
      token,
      body: JSON.stringify(payload),
    });
  },
  exit(token: string, sessionId: string) {
    return apiRequest<ConversationSessionStateResponse>(`/conversation/${sessionId}/exit`, {
      method: 'PATCH',
      token,
    });
  },
  voiceReply(token: string, sessionId: string, formData: FormData) {
    return apiUploadRequest<ConversationVoiceReplyResponse>(`/conversation/${sessionId}/reply/voice`, {
      method: 'POST',
      token,
      body: formData,
    });
  },
};
