export const theme = {
  colors: {
    // Backgrounds (derived from Navy #284B63)
    bg: "#1a3347",
    bgDark: "#122535",
    bgCard: "#213d55",
    bgCardLight: "#284B63",
    bgInput: "#1c3750",

    // Accents (exact palette values)
    primary: "#982649",       // Burgundy — buttons, brand, CTAs
    primaryLight: "#b03058",
    secondary: "#3C6E71",     // Teal — success, "in" votes, connected
    tertiary: "#94C595",      // Sage green — tags, mild accents
    warm: "#D8A48F",          // Blush/peach — warm highlights, avatars
    warmLight: "#e0b5a2",

    // Text
    text: "#f0ece6",
    textSecondary: "#8a9bb5",
    textMuted: "#5a7094",
    textDark: "#1a3347",

    // Semantic
    success: "#3C6E71",
    warning: "#D8A48F",
    error: "#982649",
    maybe: "#D8A48F",         // Warm for "maybe" votes
    out: "#5a7094",           // Muted for "out" votes

    // Borders
    border: "rgba(240,236,230,0.08)",
    borderLight: "rgba(240,236,230,0.15)",

    // Overlays
    overlay: "rgba(18,37,53,0.85)",
  },

  // Typography
  fonts: {
    light: "Nunito_300Light",
    regular: "Nunito_400Regular",
    semibold: "Nunito_600SemiBold",
    bold: "Nunito_700Bold",
    extrabold: "Nunito_800ExtraBold",
    black: "Nunito_900Black",
    display: "RubikBubbles_400Regular",
  },

  // Common styles
  borderRadius: {
    sm: 8,
    md: 12,
    lg: 16,
    xl: 20,
    full: 999,
  },
} as const;
