const fallbackApiBaseUrl = 'http://127.0.0.1:8000';

export const env = {
  apiBaseUrl: (process.env.EXPO_PUBLIC_API_BASE_URL ?? fallbackApiBaseUrl).replace(/\/$/, ''),
};
