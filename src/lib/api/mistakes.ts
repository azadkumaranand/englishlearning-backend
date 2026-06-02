import { apiRequest } from '@/src/lib/api/client';
import type {
  MistakeReviewListResponse,
  MistakeRetryRequest,
  MistakeRetryResponse,
  MistakeRetryVoiceResponse,
} from '@/src/lib/api/types';

export const mistakesApi = {
  getReview(token: string) {
    return apiRequest<MistakeReviewListResponse>('/mistakes/review', { token });
  },
  retry(token: string, payload: MistakeRetryRequest) {
    return apiRequest<MistakeRetryResponse>('/mistakes/retry', {
      method: 'POST',
      token,
      body: JSON.stringify(payload),
    });
  },
  retryVoice(token: string, mistakeId: string, formData: FormData) {
    formData.append('mistake_id', mistakeId);
    return apiRequest<MistakeRetryVoiceResponse>('/mistakes/retry/voice', {
      method: 'POST',
      token,
      body: formData,
    });
  },
};
