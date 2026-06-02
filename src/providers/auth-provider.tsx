import type { PropsWithChildren } from 'react';
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { authApi } from '@/src/lib/api/auth';
import { ApiError } from '@/src/lib/api/client';
import { onboardingApi } from '@/src/lib/api/onboarding';
import { queryClient } from '@/src/lib/query-client';
import type {
  LoginPayload,
  OnboardingCompleteResponse,
  Onboarding,
  OnboardingPayload,
  SignupPayload,
  User,
} from '@/src/lib/api/types';
import { clearAuthToken, loadAuthToken, saveAuthToken } from '@/src/lib/storage';

type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated';

type AuthContextValue = {
  status: AuthStatus;
  token: string | null;
  user: User | null;
  onboarding: Onboarding | null;
  needsOnboarding: boolean;
  signIn: (payload: LoginPayload) => Promise<void>;
  signUp: (payload: SignupPayload) => Promise<void>;
  signOut: () => Promise<void>;
  refreshSession: () => Promise<void>;
  completeOnboarding: (payload: OnboardingPayload) => Promise<OnboardingCompleteResponse>;
  authorizedRequest: <T>(request: (token: string) => Promise<T>) => Promise<T>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [onboarding, setOnboarding] = useState<Onboarding | null>(null);

  const clearSession = useCallback(async () => {
    await clearAuthToken();
    setToken(null);
    setUser(null);
    setOnboarding(null);
    setStatus('unauthenticated');
    queryClient.clear();
  }, []);

  const hydrateSession = useCallback(
    async (nextToken: string) => {
      const [nextUser, nextOnboarding] = await Promise.all([
        authApi.me(nextToken),
        onboardingApi.get(nextToken),
      ]);

      setToken(nextToken);
      setUser(nextUser);
      setOnboarding(nextOnboarding);
      setStatus('authenticated');
    },
    []
  );

  const refreshSession = useCallback(async () => {
    try {
      const storedToken = await loadAuthToken();
      if (!storedToken) {
        setStatus('unauthenticated');
        return;
      }

      await hydrateSession(storedToken);
    } catch {
      await clearSession();
    }
  }, [clearSession, hydrateSession]);

  useEffect(() => {
    void refreshSession();
  }, [refreshSession]);

  const signIn = useCallback(
    async (payload: LoginPayload) => {
      const response = await authApi.login(payload);
      await saveAuthToken(response.access_token);
      await hydrateSession(response.access_token);
    },
    [hydrateSession]
  );

  const signUp = useCallback(
    async (payload: SignupPayload) => {
      const response = await authApi.signup(payload);
      await saveAuthToken(response.access_token);
      await hydrateSession(response.access_token);
    },
    [hydrateSession]
  );

  const signOut = useCallback(async () => {
    await clearSession();
  }, [clearSession]);

  const completeOnboardingState = useCallback(
    async (payload: OnboardingPayload) => {
      if (!token) {
        throw new Error('Authentication is required');
      }

      const response = await onboardingApi.complete(token, payload);
      const nextOnboarding = response.onboarding;
      setOnboarding(nextOnboarding);
      setUser((currentUser) =>
        currentUser
          ? {
              ...currentUser,
              native_language: nextOnboarding.native_language,
              english_level: nextOnboarding.english_level,
              learning_goal: nextOnboarding.learning_goal,
              practice_preference: nextOnboarding.practice_preference,
              onboarding_completed: nextOnboarding.onboarding_completed,
            }
          : currentUser
      );
      return response;
    },
    [token]
  );

  const authorizedRequest = useCallback(
    async <T,>(request: (currentToken: string) => Promise<T>) => {
      if (!token) {
        await clearSession();
        throw new Error('Authentication is required');
      }

      try {
        return await request(token);
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          await clearSession();
        }
        throw error;
      }
    },
    [clearSession, token]
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      token,
      user,
      onboarding,
      needsOnboarding: status === 'authenticated' && user?.onboarding_completed !== true,
      signIn,
      signUp,
      signOut,
      refreshSession,
      completeOnboarding: completeOnboardingState,
      authorizedRequest,
    }),
    [
      authorizedRequest,
      completeOnboardingState,
      onboarding,
      refreshSession,
      signIn,
      signOut,
      signUp,
      status,
      token,
      user,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
