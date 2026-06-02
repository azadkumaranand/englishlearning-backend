/**
 * Premium color palette for the English Learning App.
 * Teal-based primary with warm accent and semantic tokens.
 */

export const colors = {
  // ── Primary Teal Gradient ──
  primary: {
    50: '#EFFCF9',
    100: '#C6F7E9',
    200: '#8EEDC7',
    300: '#5BE5B0',
    400: '#2DD4A0',
    500: '#0D9488',   // main brand
    600: '#0F766E',   // legacy primary (kept for compatibility)
    700: '#115E59',
    800: '#134E4A',
    900: '#0C3C38',
  },

  // ── Accent — Violet/Indigo for contrast pop ──
  accent: {
    50: '#F0EEFF',
    100: '#D9D4FF',
    200: '#B5ACFF',
    300: '#8B7FFF',
    400: '#6C5CE7',   // main accent
    500: '#5A4BD1',
    600: '#4C3FB3',
  },

  // ── Gold — Streaks, rewards, gamification ──
  gold: {
    50: '#FFFBEB',
    100: '#FEF3C7',
    200: '#FDE68A',
    300: '#FCD34D',
    400: '#FBBF24',   // main gold
    500: '#F59E0B',
    600: '#D97706',
  },

  // ── Semantic ──
  success: '#10B981',
  warning: '#F59E0B',
  error: '#EF4444',
  info: '#3B82F6',

  // ── Severity (for correction cards) ──
  severity: {
    none: '#10B981',
    low: '#10B981',
    medium: '#F59E0B',
    high: '#EF4444',
  },

  // ── Neutral Surface Tones ──
  neutral: {
    0: '#FFFFFF',
    50: '#F8FAFC',
    100: '#F1F5F9',
    150: '#EEF2F6',
    200: '#E2E8F0',
    300: '#CBD5E1',
    400: '#94A3B8',
    500: '#64748B',
    600: '#475569',
    700: '#334155',
    800: '#1E293B',
    900: '#0F172A',
  },

  // ── Backgrounds ──
  bg: {
    base: '#F0F4F3',
    card: '#FFFFFF',
    elevated: '#FFFFFF',
    subtle: '#F6FAF9',
    hero: '#E6F7F4',
  },

  // ── Text ──
  text: {
    primary: '#0F172A',
    secondary: '#475569',
    tertiary: '#94A3B8',
    inverse: '#FFFFFF',
    accent: '#0D9488',
    link: '#0D9488',
  },

  // ── Borders ──
  border: {
    light: '#E2E8F0',
    medium: '#CBD5E1',
    focus: '#0D9488',
  },

  // ── Gradients ──
  gradients: {
    primary: ['#0D9488', '#0F766E'], // Teal gradient
    accent: ['#6C5CE7', '#5A4BD1'], // Violet gradient
    hero: ['#0D9488', '#0F766E', '#115E59'], // Deep teal for hero
    gold: ['#FBBF24', '#F59E0B'],
    glass: ['rgba(255, 255, 255, 0.15)', 'rgba(255, 255, 255, 0.05)'], // Glassmorphism
  },
} as const;
