import { apiRequest } from '@/src/lib/api/client';
import type { ProgressDashboard } from '@/src/lib/api/types';

export const progressApi = {
  getMine(token: string) {
    return apiRequest<ProgressDashboard>('/progress/me', { token });
  },
};
