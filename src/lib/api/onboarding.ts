import { apiRequest } from '@/src/lib/api/client';
import type { Onboarding, OnboardingCompleteResponse, OnboardingPayload } from '@/src/lib/api/types';

export const onboardingApi = {
  get(token: string) {
    return apiRequest<Onboarding>('/onboarding', { token });
  },
  complete(token: string, payload: OnboardingPayload) {
    return apiRequest<OnboardingCompleteResponse>('/onboarding/complete', {
      method: 'POST',
      token,
      body: JSON.stringify(payload),
    });
  },
};
