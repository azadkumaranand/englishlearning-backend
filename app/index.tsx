import { Redirect } from 'expo-router';

import { LoadingScreen } from '@/src/components/loading-screen';
import { useAuth } from '@/src/hooks/use-auth';

export default function IndexScreen() {
  const auth = useAuth();

  if (auth.status === 'loading') {
    return <LoadingScreen message="Loading your learning space..." />;
  }

  if (auth.status === 'unauthenticated') {
    return <Redirect href="/(auth)/login" />;
  }

  if (auth.needsOnboarding) {
    return <Redirect href="/(app)/onboarding" />;
  }

  return <Redirect href="/(app)" />;
}
