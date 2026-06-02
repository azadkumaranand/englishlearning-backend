import { apiRequest } from '@/src/lib/api/client';
import type { DailyPlan } from '@/src/lib/api/types';

export const dailyPlanApi = {
  getMine(token: string) {
    return apiRequest<DailyPlan>('/daily-plan/me', { token });
  },
};
