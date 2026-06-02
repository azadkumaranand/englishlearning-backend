import { apiRequest } from '@/src/lib/api/client';
import type {
  MistakePattern,
  PersonalizationRecommendation,
  PersonalizationSummary,
} from '@/src/lib/api/types';

export const personalizationApi = {
  getSummary(token: string) {
    return apiRequest<PersonalizationSummary>('/personalization/summary', { token });
  },
  getRecommendation(token: string) {
    return apiRequest<PersonalizationRecommendation>('/personalization/recommendation', { token });
  },
  getMistakes(token: string, limit = 10) {
    return apiRequest<MistakePattern[]>(`/personalization/mistakes?limit=${limit}`, { token });
  },
};
