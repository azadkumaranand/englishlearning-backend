import * as SecureStore from 'expo-secure-store';

const authTokenKey = 'english-learning.auth-token';

export async function saveAuthToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(authTokenKey, token);
}

export async function loadAuthToken(): Promise<string | null> {
  return SecureStore.getItemAsync(authTokenKey);
}

export async function clearAuthToken(): Promise<void> {
  await SecureStore.deleteItemAsync(authTokenKey);
}
