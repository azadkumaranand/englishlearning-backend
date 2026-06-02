import { apiRequest } from '@/src/lib/api/client';
import type { LearningProfile } from '@/src/lib/api/types';

export const learningProfileApi = {
  getMine(token: string) {
    return apiRequest<LearningProfile>('/learning-profile/me', { token });
  },
};
