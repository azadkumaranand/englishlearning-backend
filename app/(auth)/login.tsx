import { useRouter } from 'expo-router';
import { useState } from 'react';

import { AuthForm } from '@/src/components/auth-form';
import { ScreenContainer } from '@/src/components/screen-container';
import { useAuth } from '@/src/hooks/use-auth';

export default function LoginScreen() {
  const auth = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <ScreenContainer scroll>
      <AuthForm
        error={error}
        loading={loading}
        mode="login"
        onSubmit={async ({ email, password }) => {
          try {
            setLoading(true);
            setError(null);
            await auth.signIn({ email, password });
            router.replace('/');
          } catch (nextError) {
            setError(nextError instanceof Error ? nextError.message : 'Unable to log in');
          } finally {
            setLoading(false);
          }
        }}
      />
    </ScreenContainer>
  );
}
