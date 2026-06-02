import { apiRequest } from '@/src/lib/api/client';
import type { AuthResponse, LoginPayload, SignupPayload, User } from '@/src/lib/api/types';

export const authApi = {
  signup(payload: SignupPayload) {
    return apiRequest<AuthResponse>('/auth/signup', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
  login(payload: LoginPayload) {
    return apiRequest<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
  me(token: string) {
    return apiRequest<User>('/auth/me', { token });
  },
};
