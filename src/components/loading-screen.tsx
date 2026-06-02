import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withSequence,
  withTiming,
  runOnJS,
} from 'react-native-reanimated';
import { Ionicons } from '@expo/vector-icons';

import { colors, radii, spacing, typography, shadows } from '@/src/theme';

const rotatingMessages = [
  'Polishing your personalized learning path...',
  'Crafting real-time feedback for your answers...',
  'Preparing your interactive speaking practice...',
  'Analyzing your common mistakes to customize review...',
  'Structuring today’s key conversation topics...',
];

export function LoadingScreen({ message }: { message?: string }) {
  const [currentMessageIndex, setCurrentMessageIndex] = useState(0);
  const textOpacity = useSharedValue(1);

  // Animated values for the glowing orb
  const pulseScale1 = useSharedValue(1);
  const pulseScale2 = useSharedValue(1);
  const orbRotation = useSharedValue(0);

  // Rotate messages with fade transition
  useEffect(() => {
    if (message) return; // Don't rotate if static message is provided

    const interval = setInterval(() => {
      // Fade out
      textOpacity.value = withTiming(0, { duration: 400 }, () => {
        // Change index on JS thread
        runOnJS(setCurrentMessageIndex)((prev) => (prev + 1) % rotatingMessages.length);
        // Fade in
        textOpacity.value = withTiming(1, { duration: 400 });
      });
    }, 3500);

    return () => clearInterval(interval);
  }, [message, textOpacity]);

  // Pulse & Rotation animations
  useEffect(() => {
    pulseScale1.value = withRepeat(
      withSequence(
        withTiming(1.3, { duration: 1200, easing: Easing.inOut(Easing.ease) }),
        withTiming(1.0, { duration: 1200, easing: Easing.inOut(Easing.ease) })
      ),
      -1,
      false
    );

    pulseScale2.value = withRepeat(
      withSequence(
        withTiming(1.6, { duration: 1800, easing: Easing.inOut(Easing.ease) }),
        withTiming(1.0, { duration: 1800, easing: Easing.inOut(Easing.ease) })
      ),
      -1,
      false
    );

    orbRotation.value = withRepeat(
      withTiming(360, { duration: 6000, easing: Easing.linear }),
      -1,
      false
    );
  }, [pulseScale1, pulseScale2, orbRotation]);

  const animatedPulse1 = useAnimatedStyle(() => ({
    transform: [{ scale: pulseScale1.value }],
    opacity: 1 - (pulseScale1.value - 1) / 0.3 * 0.5, // Fades as it expands
  }));

  const animatedPulse2 = useAnimatedStyle(() => ({
    transform: [{ scale: pulseScale2.value }],
    opacity: 1 - (pulseScale2.value - 1) / 0.6 * 0.7, // Fades as it expands
  }));

  const animatedOrbRotation = useAnimatedStyle(() => ({
    transform: [{ rotate: `${orbRotation.value}deg` }],
  }));

  const animatedText = useAnimatedStyle(() => ({
    opacity: textOpacity.value,
  }));

  const displayMessage = message ?? rotatingMessages[currentMessageIndex];

  return (
    <View style={styles.container}>
      <LinearGradient
        colors={['#F0F4F3', '#E6ECEB', '#DBE5E3']}
        style={StyleSheet.absoluteFillObject}
      />

      {/* Decorative background shapes */}
      <View style={styles.ambientShapeTop} />
      <View style={styles.ambientShapeBottom} />

      <View style={styles.loaderContainer}>
        {/* Breathing / Pulsing Glowing Rings */}
        <View style={styles.orbWrapper}>
          <Animated.View style={[styles.pulseRing, styles.pulseRingOuter, animatedPulse2]} />
          <Animated.View style={[styles.pulseRing, styles.pulseRingInner, animatedPulse1]} />
          
          <Animated.View style={[styles.centralOrb, shadows.md, animatedOrbRotation]}>
            <LinearGradient
              colors={colors.gradients.primary}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
              style={styles.gradientOrb}
            >
              <Ionicons name="sparkles" size={32} color={colors.text.inverse} />
            </LinearGradient>
          </Animated.View>
        </View>

        {/* Text Area */}
        <View style={styles.textContainer}>
          <Text style={styles.kicker}>AI English Coach</Text>
          <Text style={styles.title}>Setting up your session</Text>
          
          <Animated.View style={[styles.messageWrapper, animatedText]}>
            <Text style={styles.message}>{displayMessage}</Text>
          </Animated.View>
        </View>

        {/* Micro status indicator */}
        <View style={[styles.statusPill, shadows.sm]}>
          <View style={styles.liveDot} />
          <Text style={styles.statusText}>Connecting to tutor model...</Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.xl,
    backgroundColor: '#F0F4F3',
  },
  ambientShapeTop: {
    position: 'absolute',
    top: -100,
    right: -50,
    width: 300,
    height: 300,
    borderRadius: 150,
    backgroundColor: 'rgba(13, 148, 136, 0.08)',
  },
  ambientShapeBottom: {
    position: 'absolute',
    bottom: -120,
    left: -60,
    width: 320,
    height: 320,
    borderRadius: 160,
    backgroundColor: 'rgba(108, 92, 231, 0.06)',
  },
  loaderContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
    gap: spacing.xl,
  },
  orbWrapper: {
    width: 160,
    height: 160,
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
    marginBottom: spacing.md,
  },
  pulseRing: {
    position: 'absolute',
    borderRadius: 999,
    borderWidth: 1.5,
  },
  pulseRingInner: {
    width: 100,
    height: 100,
    borderColor: 'rgba(13, 148, 136, 0.3)',
    backgroundColor: 'rgba(13, 148, 136, 0.05)',
  },
  pulseRingOuter: {
    width: 120,
    height: 120,
    borderColor: 'rgba(108, 92, 231, 0.2)',
    backgroundColor: 'rgba(108, 92, 231, 0.03)',
  },
  centralOrb: {
    width: 76,
    height: 76,
    borderRadius: 38,
    overflow: 'hidden',
    backgroundColor: colors.primary[500],
  },
  gradientOrb: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  textContainer: {
    alignItems: 'center',
    gap: spacing.xs,
    paddingHorizontal: spacing.md,
  },
  kicker: {
    ...typography.eyebrow,
    color: colors.primary[600],
    letterSpacing: 2.5,
    marginBottom: spacing.xxs,
  },
  title: {
    ...typography.heading,
    color: colors.text.primary,
    textAlign: 'center',
  },
  messageWrapper: {
    minHeight: 48,
    justifyContent: 'center',
    marginTop: spacing.xs,
  },
  message: {
    ...typography.bodyLg,
    color: colors.text.secondary,
    textAlign: 'center',
    lineHeight: 22,
  },
  statusPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    backgroundColor: colors.bg.card,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg,
    borderRadius: radii.full,
    borderWidth: 1,
    borderColor: colors.border.light,
    marginTop: spacing.lg,
  },
  liveDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.success,
  },
  statusText: {
    ...typography.captionBold,
    color: colors.text.secondary,
  },
});
