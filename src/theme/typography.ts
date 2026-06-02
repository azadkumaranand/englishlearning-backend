import { TextStyle } from 'react-native';

/**
 * Typography scale — consistent text styles across the app.
 */

export const fontWeights = {
    regular: '400' as TextStyle['fontWeight'],
    medium: '500' as TextStyle['fontWeight'],
    semibold: '600' as TextStyle['fontWeight'],
    bold: '700' as TextStyle['fontWeight'],
    extrabold: '800' as TextStyle['fontWeight'],
};

export const typography = {
    caption: {
        fontSize: 12,
        lineHeight: 16,
        fontWeight: fontWeights.medium,
    } as TextStyle,

    captionBold: {
        fontSize: 12,
        lineHeight: 16,
        fontWeight: fontWeights.bold,
    } as TextStyle,

    body: {
        fontSize: 14,
        lineHeight: 20,
        fontWeight: fontWeights.regular,
    } as TextStyle,

    bodyMedium: {
        fontSize: 14,
        lineHeight: 20,
        fontWeight: fontWeights.medium,
    } as TextStyle,

    bodySemibold: {
        fontSize: 14,
        lineHeight: 20,
        fontWeight: fontWeights.semibold,
    } as TextStyle,

    bodyLg: {
        fontSize: 16,
        lineHeight: 24,
        fontWeight: fontWeights.regular,
    } as TextStyle,

    bodyLgSemibold: {
        fontSize: 16,
        lineHeight: 24,
        fontWeight: fontWeights.semibold,
    } as TextStyle,

    bodyLgBold: {
        fontSize: 16,
        lineHeight: 24,
        fontWeight: fontWeights.bold,
    } as TextStyle,

    subheading: {
        fontSize: 18,
        lineHeight: 26,
        fontWeight: fontWeights.bold,
    } as TextStyle,

    heading: {
        fontSize: 22,
        lineHeight: 30,
        fontWeight: fontWeights.extrabold,
    } as TextStyle,

    title: {
        fontSize: 28,
        lineHeight: 36,
        fontWeight: fontWeights.extrabold,
    } as TextStyle,

    display: {
        fontSize: 34,
        lineHeight: 42,
        fontWeight: fontWeights.extrabold,
    } as TextStyle,

    eyebrow: {
        fontSize: 12,
        lineHeight: 16,
        fontWeight: fontWeights.bold,
        letterSpacing: 1.2,
        textTransform: 'uppercase' as const,
    } as TextStyle,
};
