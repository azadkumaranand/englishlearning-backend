import type { Onboarding } from '@/src/lib/api/types';

export function isOnboardingComplete(onboarding: Onboarding | null): boolean {
  if (!onboarding) {
    return false;
  }

  return onboarding.onboarding_completed === true;
}
