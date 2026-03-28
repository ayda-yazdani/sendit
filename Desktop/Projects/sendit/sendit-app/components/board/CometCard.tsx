import { useEffect } from "react";
import { View, Text, StyleSheet } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
  Easing,
  interpolate,
} from "react-native-reanimated";
import { theme } from "@/constants/Theme";
import { TasteProfileData } from "@/lib/ai/taste-engine";

interface CometCardProps {
  boardName: string;
  identityLabel: string;
  profileData: TasteProfileData;
  memberCount: number;
  reelCount: number;
}

const AnimatedLinearGradient = Animated.createAnimatedComponent(LinearGradient);

export function CometCard({
  boardName,
  identityLabel,
  profileData,
  memberCount,
  reelCount,
}: CometCardProps) {
  const rotation = useSharedValue(0);

  useEffect(() => {
    rotation.value = withRepeat(
      withTiming(360, { duration: 3000, easing: Easing.linear }),
      -1,
      false
    );
  }, []);

  const animatedBorderStyle = useAnimatedStyle(() => {
    return {
      transform: [{ rotate: `${rotation.value}deg` }],
    };
  });

  const p = profileData;

  return (
    <View style={styles.outerContainer}>
      {/* Animated gradient border */}
      <View style={styles.borderContainer}>
        <Animated.View style={[styles.gradientWrapper, animatedBorderStyle]}>
          <LinearGradient
            colors={[
              theme.colors.primary,
              theme.colors.secondary,
              theme.colors.warm,
              theme.colors.tertiary,
              theme.colors.primary,
            ]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={styles.gradientBorder}
          />
        </Animated.View>
      </View>

      {/* Card content */}
      <View style={styles.card}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.boardName}>{boardName.toUpperCase()}</Text>
          <View style={styles.statsRow}>
            <View style={styles.stat}>
              <Text style={styles.statValue}>{memberCount}</Text>
              <Text style={styles.statLabel}>members</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.stat}>
              <Text style={styles.statValue}>{reelCount}</Text>
              <Text style={styles.statLabel}>reels</Text>
            </View>
          </View>
        </View>

        {/* Identity label — the hero */}
        <Text style={styles.identityLabel}>{identityLabel}</Text>

        {/* Taste summary */}
        <View style={styles.tasteSection}>
          {/* Activities */}
          {p.activity_types?.length > 0 && (
            <View style={styles.tagRow}>
              {p.activity_types.slice(0, 4).map((a, i) => (
                <View key={i} style={styles.tag}>
                  <Text style={styles.tagText}>{a}</Text>
                </View>
              ))}
            </View>
          )}

          {/* Aesthetic */}
          {p.aesthetic && (
            <Text style={styles.aesthetic}>"{p.aesthetic}"</Text>
          )}

          {/* Meta row */}
          <View style={styles.metaRow}>
            {p.food_preferences?.[0] && (
              <Text style={styles.metaItem}>🍽 {p.food_preferences[0]}</Text>
            )}
            {p.location_patterns?.[0] && (
              <Text style={styles.metaItem}>📍 {p.location_patterns[0]}</Text>
            )}
            {p.price_range && (
              <Text style={styles.metaItem}>💰 {p.price_range}</Text>
            )}
          </View>

          {/* Humour */}
          {p.humour_style && p.humour_style !== "not enough data yet" && (
            <Text style={styles.humour}>😂 {p.humour_style}</Text>
          )}
        </View>

        {/* Platform mix dots */}
        {p.platform_mix && Object.keys(p.platform_mix).length > 0 && (
          <View style={styles.platformRow}>
            {Object.entries(p.platform_mix).map(([platform, count]) => (
              <View key={platform} style={styles.platformDot}>
                <Text style={styles.platformEmoji}>
                  {platform === "youtube" ? "▶️" : platform === "instagram" ? "📸" : platform === "tiktok" ? "🎵" : "🔗"}
                </Text>
                <Text style={styles.platformCount}>{count as number}</Text>
              </View>
            ))}
          </View>
        )}

        {/* Branding */}
        <Text style={styles.branding}>sendit</Text>
      </View>
    </View>
  );
}

const CARD_BORDER_RADIUS = 20;
const BORDER_WIDTH = 2;

const styles = StyleSheet.create({
  outerContainer: {
    position: "relative",
    borderRadius: CARD_BORDER_RADIUS,
    padding: BORDER_WIDTH,
  },
  borderContainer: {
    ...StyleSheet.absoluteFillObject,
    borderRadius: CARD_BORDER_RADIUS,
    overflow: "hidden",
  },
  gradientWrapper: {
    width: "200%",
    height: "200%",
    position: "absolute",
    top: "-50%",
    left: "-50%",
  },
  gradientBorder: {
    width: "100%",
    height: "100%",
  },
  card: {
    backgroundColor: theme.colors.bgDark,
    borderRadius: CARD_BORDER_RADIUS - BORDER_WIDTH,
    padding: 24,
    overflow: "hidden",
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 20,
  },
  boardName: {
    fontSize: 12,
    fontWeight: "700",
    color: theme.colors.textMuted,
    letterSpacing: 3,
  },
  statsRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  stat: { alignItems: "center" },
  statValue: { fontSize: 16, fontWeight: "bold", color: theme.colors.text },
  statLabel: { fontSize: 10, color: theme.colors.textMuted },
  statDivider: { width: 1, height: 20, backgroundColor: theme.colors.border },
  identityLabel: {
    fontSize: 28,
    fontWeight: "800",
    color: theme.colors.text,
    lineHeight: 34,
    marginBottom: 20,
  },
  tasteSection: { gap: 12, marginBottom: 20 },
  tagRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  tag: {
    backgroundColor: `${theme.colors.primary}25`,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderWidth: 1,
    borderColor: `${theme.colors.primary}40`,
  },
  tagText: { fontSize: 13, color: theme.colors.warm, fontWeight: "500" },
  aesthetic: {
    fontSize: 16,
    color: theme.colors.textSecondary,
    fontStyle: "italic",
    lineHeight: 22,
  },
  metaRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 16,
  },
  metaItem: { fontSize: 13, color: theme.colors.textSecondary },
  humour: { fontSize: 13, color: theme.colors.textSecondary },
  platformRow: {
    flexDirection: "row",
    gap: 12,
    marginBottom: 16,
  },
  platformDot: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: theme.colors.bgCard,
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  platformEmoji: { fontSize: 12 },
  platformCount: { fontSize: 12, fontWeight: "700", color: theme.colors.text },
  branding: {
    fontSize: 11,
    color: `${theme.colors.text}15`,
    textAlign: "right",
    letterSpacing: 3,
    fontWeight: "600",
  },
});
