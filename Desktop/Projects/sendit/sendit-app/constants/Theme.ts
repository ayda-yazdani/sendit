export const theme = {
  colors: {
    // Backgrounds
    bg: "#152d4a",
    bgDark: "#0f2137",
    bgCard: "#1e3a5f",
    bgCardLight: "#24456b",
    bgInput: "#1a3352",

    // Accents
    primary: "#9b1b4a",       // Burgundy — buttons, brand, CTAs
    primaryLight: "#b8265e",
    secondary: "#4d8a8a",     // Teal — success, "in" votes, connected
    tertiary: "#a3b899",      // Sage green — tags, mild accents
    warm: "#c9917a",          // Blush/peach — warm highlights, avatars
    warmLight: "#d4a48f",

    // Text
    text: "#f0ece6",
    textSecondary: "#8a9bb5",
    textMuted: "#5a7094",
    textDark: "#152d4a",

    // Semantic
    success: "#4d8a8a",
    warning: "#c9917a",
    error: "#9b1b4a",
    maybe: "#c9917a",         // Warm for "maybe" votes
    out: "#5a7094",           // Muted for "out" votes

    // Borders
    border: "rgba(240,236,230,0.08)",
    borderLight: "rgba(240,236,230,0.15)",

    // Overlays
    overlay: "rgba(15,33,55,0.85)",
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
