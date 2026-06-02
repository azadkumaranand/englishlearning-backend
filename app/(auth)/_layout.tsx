import { Redirect, Stack } from 'expo-router';

import { LoadingScreen } from '@/src/components/loading-screen';
import { useAuth } from '@/src/hooks/use-auth';

export default function AuthLayout() {
  const auth = useAuth();

  if (auth.status === 'loading') {
    return <LoadingScreen message="Checking your account..." />;
  }

  if (auth.status === 'authenticated') {
    return <Redirect href={auth.needsOnboarding ? '/(app)/onboarding' : '/(app)'} />;
  }

  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="login" />
      <Stack.Screen name="signup" />
    </Stack>
  );
}
