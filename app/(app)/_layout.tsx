import { Redirect, Stack, usePathname } from 'expo-router';

import { LoadingScreen } from '@/src/components/loading-screen';
import { useAuth } from '@/src/hooks/use-auth';
import { colors } from '@/src/theme';

export default function AppLayout() {
  const auth = useAuth();
  const pathname = usePathname();

  if (auth.status === 'loading') {
    return <LoadingScreen message="Preparing your practice flow… ✨" />;
  }

  if (auth.status === 'unauthenticated') {
    return <Redirect href="/(auth)/login" />;
  }

  if (auth.needsOnboarding && pathname !== '/onboarding') {
    return <Redirect href="/(app)/onboarding" />;
  }

  if (!auth.needsOnboarding && pathname === '/onboarding') {
    return <Redirect href="/(app)" />;
  }

  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: colors.bg.base },
        headerShadowVisible: false,
        headerTintColor: colors.text.primary,
        headerTitleStyle: {
          fontWeight: '700',
          fontSize: 18,
        },
        contentStyle: { backgroundColor: colors.bg.base },
        animation: 'slide_from_right',
      }}>
      <Stack.Screen name="index" options={{ headerShown: false }} />
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      <Stack.Screen name="onboarding" options={{ title: 'Setup', headerShown: false }} />
      <Stack.Screen name="conversation-scenarios" options={{ title: 'Roleplay Scenarios' }} />
      <Stack.Screen name="conversation/[id]" options={{ title: 'Conversation Practice' }} />
      <Stack.Screen name="mistake-review" options={{ title: 'Mistake Review' }} />
      <Stack.Screen name="session/[id]" options={{ title: 'Practice' }} />
    </Stack>
  );
}
