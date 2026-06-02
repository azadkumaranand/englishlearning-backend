import { StyleSheet, Text, View } from 'react-native';

import { PrimaryButton } from '@/src/components/primary-button';
import { ScreenContainer } from '@/src/components/screen-container';
import { useAuth } from '@/src/hooks/use-auth';
import { colors, radii, shadows, spacing, typography } from '@/src/theme';

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.detailRow}>
      <Text style={styles.detailLabel}>{label}</Text>
      <Text style={styles.detailValue}>{value}</Text>
    </View>
  );
}

export default function ProfileScreen() {
  const auth = useAuth();
  const user = auth.user;

  return (
    <ScreenContainer scroll>
      <View style={[styles.profileCard, shadows.md]}>
        <Text style={styles.profileEyebrow}>Profile</Text>
        <Text style={styles.profileName}>{user?.full_name ?? 'Learner'}</Text>
        <Text style={styles.profileEmail}>{user?.email ?? ''}</Text>
      </View>

      <View style={[styles.infoCard, shadows.sm]}>
        <DetailRow label="Native language" value={user?.native_language ?? 'Not set'} />
        <DetailRow label="English level" value={user?.english_level?.replace(/_/g, ' ') ?? 'Not set'} />
        <DetailRow label="Learning goal" value={user?.learning_goal?.replace(/_/g, ' ') ?? 'Not set'} />
        <DetailRow
          label="Practice preference"
          value={user?.practice_preference?.replace(/_/g, ' ') ?? 'Not set'}
        />
      </View>

      <PrimaryButton label="Sign Out" onPress={() => void auth.signOut()} variant="secondary" icon="↗" />
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  profileCard: {
    backgroundColor: colors.bg.card,
    borderRadius: radii['2xl'],
    padding: spacing.xl,
    gap: spacing.xs,
  },
  profileEyebrow: {
    ...typography.eyebrow,
    color: colors.primary[600],
  },
  profileName: {
    ...typography.title,
    color: colors.text.primary,
  },
  profileEmail: {
    ...typography.bodyLg,
    color: colors.text.secondary,
  },
  infoCard: {
    backgroundColor: colors.bg.card,
    borderRadius: radii.xl,
    padding: spacing.xl,
    gap: spacing.md,
  },
  detailRow: {
    gap: spacing.xxs,
  },
  detailLabel: {
    ...typography.captionBold,
    color: colors.text.tertiary,
    textTransform: 'uppercase',
  },
  detailValue: {
    ...typography.bodyLgSemibold,
    color: colors.text.primary,
    textTransform: 'capitalize',
  },
});
