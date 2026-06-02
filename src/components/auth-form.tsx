import { Link } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';
import { useState } from 'react';
import Animated, { FadeIn, FadeInDown } from 'react-native-reanimated';

import { PrimaryButton } from '@/src/components/primary-button';
import { TextField } from '@/src/components/text-field';
import { colors, radii, shadows, spacing, typography } from '@/src/theme';

type AuthFormValues = {
  email: string;
  password: string;
  fullName?: string;
};

type AuthFormProps = {
  mode: 'login' | 'signup';
  loading?: boolean;
  error?: string | null;
  onSubmit: (values: AuthFormValues) => void;
};

export function AuthForm({ mode, loading = false, error, onSubmit }: AuthFormProps) {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  return (
    <Animated.View entering={FadeIn.duration(500)} style={styles.wrapper}>
      {/* Branded header */}
      <Animated.View entering={FadeInDown.delay(100).duration(500)} style={styles.header}>
        <Text style={styles.brandEmoji}>📚</Text>
        <View style={styles.brandBadge}>
          <Text style={styles.eyebrow}>English Learning App</Text>
        </View>
        <Text style={styles.title}>
          {mode === 'login' ? 'Welcome back! 👋' : 'Join the journey 🚀'}
        </Text>
        <Text style={styles.subtitle}>
          {mode === 'login'
            ? 'Continue your English practice and keep your streak alive.'
            : 'Create your account and start improving your English today.'}
        </Text>
      </Animated.View>

      {/* Form card */}
      <Animated.View entering={FadeInDown.delay(200).duration(500)} style={[styles.formCard, shadows.md]}>
        {mode === 'signup' ? (
          <TextField
            autoCapitalize="words"
            label="Full name"
            onChangeText={setFullName}
            placeholder="Your name"
            value={fullName}
          />
        ) : null}
        <TextField
          autoCapitalize="none"
          keyboardType="email-address"
          label="Email"
          onChangeText={setEmail}
          placeholder="you@example.com"
          value={email}
        />
        <TextField
          autoCapitalize="none"
          label="Password"
          onChangeText={setPassword}
          placeholder="At least 8 characters"
          secureTextEntry
          value={password}
        />

        {error ? (
          <View style={styles.errorCard}>
            <Text style={styles.errorText}>⚠️ {error}</Text>
          </View>
        ) : null}

        <PrimaryButton
          label={mode === 'login' ? 'Log in' : 'Create account'}
          loading={loading}
          icon={mode === 'login' ? '🔑' : '✨'}
          onPress={() =>
            onSubmit({
              email: email.trim(),
              password,
              ...(mode === 'signup' ? { fullName: fullName.trim() } : {}),
            })
          }
        />
      </Animated.View>

      {/* Switch link */}
      <Animated.View entering={FadeInDown.delay(300).duration(500)} style={styles.switchRow}>
        <Text style={styles.switchText}>
          {mode === 'login' ? 'Need an account?' : 'Already have an account?'}
        </Text>
        <Link href={mode === 'login' ? '/(auth)/signup' : '/(auth)/login'} style={styles.link}>
          {mode === 'login' ? 'Sign up' : 'Log in'}
        </Link>
      </Animated.View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    flex: 1,
    justifyContent: 'center',
    gap: spacing['2xl'],
  },
  header: {
    gap: spacing.sm,
    alignItems: 'center',
  },
  brandEmoji: {
    fontSize: 56,
    marginBottom: spacing.xs,
  },
  brandBadge: {
    backgroundColor: colors.primary[50],
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: radii.full,
  },
  eyebrow: {
    ...typography.eyebrow,
    color: colors.primary[600],
  },
  title: {
    ...typography.title,
    color: colors.text.primary,
    textAlign: 'center',
  },
  subtitle: {
    ...typography.bodyLg,
    color: colors.text.secondary,
    textAlign: 'center',
    maxWidth: 300,
  },
  formCard: {
    backgroundColor: colors.bg.card,
    borderRadius: radii['2xl'],
    padding: spacing['2xl'],
    gap: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  errorCard: {
    backgroundColor: '#FEF2F2',
    padding: spacing.md,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: '#FECACA',
  },
  errorText: {
    ...typography.body,
    color: colors.error,
  },
  switchRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
    justifyContent: 'center',
  },
  switchText: {
    ...typography.body,
    color: colors.text.secondary,
  },
  link: {
    ...typography.bodySemibold,
    color: colors.primary[500],
  },
});
