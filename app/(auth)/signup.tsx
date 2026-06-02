import { useRouter } from 'expo-router';
import { useState } from 'react';

import { AuthForm } from '@/src/components/auth-form';
import { ScreenContainer } from '@/src/components/screen-container';
import { useAuth } from '@/src/hooks/use-auth';

export default function SignupScreen() {
  const auth = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <ScreenContainer scroll>
      <AuthForm
        error={error}
        loading={loading}
        mode="signup"
        onSubmit={async ({ email, password, fullName }) => {
          try {
            setLoading(true);
            setError(null);
            await auth.signUp({
              email,
              password,
              ...(fullName ? { full_name: fullName } : {}),
            });
            router.replace('/');
          } catch (nextError) {
            setError(nextError instanceof Error ? nextError.message : 'Unable to create account');
          } finally {
            setLoading(false);
          }
        }}
      />
    </ScreenContainer>
  );
}
