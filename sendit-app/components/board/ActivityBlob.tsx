import { useEffect } from "react";
import { View, Text, StyleSheet, Pressable } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import FontAwesome from "@expo/vector-icons/FontAwesome";
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withSequence,
  withTiming,
  Easing,
} from "react-native-reanimated";
import { theme } from "@/constants/Theme";

// Gradient palettes per vibe category — from our colour palette
const BLOB_GRADIENTS: Record<string, [string, string, string]> = {
  real_event:       ["#982649", "#D8A48F", "#982649"],
  real_venue:       ["#3C6E71", "#94C595", "#3C6E71"],
  recipe_food:      ["#D8A48F", "#94C595", "#D8A48F"],
  vibe_inspiration: ["#284B63", "#3C6E71", "#284B63"],
  humour_identity:  ["#982649", "#284B63", "#982649"],
  uncategorised:    ["#353535", "#555555", "#353535"],
  other:            ["#3C6E71", "#D8A48F", "#3C6E71"],
};

const BLOB_LABELS: Record<string, string> = {
  real_event: "Events",
  real_venue: "Venues",
  recipe_food: "Food",
  vibe_inspiration: "Vibes",
  humour_identity: "Humour",
  uncategorised: "Other",
  other: "More",
};

const BLOB_ICONS: Record<string, keyof typeof FontAwesome.glyphMap> = {
  real_event: "calendar",
  real_venue: "map-marker",
  recipe_food: "cutlery",
  vibe_inspiration: "leaf",
  humour_identity: "smile-o",
  uncategorised: "ellipsis-h",
  other: "ellipsis-h",
};

export function getBlobSize(reelCount: number, minSize = 100, maxSize = 180) {
  return Math.min(maxSize, Math.max(minSize, 80 + reelCount * 20));
}

interface ReelPreview {
  id: string;
  title?: string;
  thumbnail_url?: string;
}

interface ActivityBlobProps {
  category: string;
  reelCount: number;
  reels: ReelPreview[];
  x: number;
  y: number;
  onPress: () => void;
  index: number;
  minSize?: number;
  maxSize?: number;
  hasNotification?: boolean;
}

export function ActivityBlob({
  category,
  reelCount,
  reels,
  x,
  y,
  onPress,
  index,
  minSize,
  maxSize,
  hasNotification,
}: ActivityBlobProps) {
  // Size based on reel count — min 100, max 180
  const baseSize = getBlobSize(reelCount, minSize, maxSize);
  const labelFontSize = Math.max(12, Math.min(15, Math.round(baseSize * 0.085)));
  const dotSize = Math.max(10, Math.round(baseSize * 0.12));
  const dotBorder = Math.max(2, Math.round(dotSize * 0.2));
  const dotOffset = Math.max(4, Math.round(dotSize * 0.25));
  const iconSize = Math.max(18, Math.round(baseSize * 0.22));
  const iconWrapperSize = Math.max(34, Math.round(baseSize * 0.4));

  // Floating animation — each blob drifts differently
  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);
  const scale = useSharedValue(1);

  useEffect(() => {
    const driftX = 4 + (index % 3) * 3;
    const driftY = 4 + (index % 2) * 4;
    const duration = 3600 + index * 600;

    translateX.value = withRepeat(
      withSequence(
        withTiming(driftX, { duration, easing: Easing.inOut(Easing.sin) }),
        withTiming(-driftX, { duration, easing: Easing.inOut(Easing.sin) }),
      ),
      -1,
      true,
    );
    translateY.value = withRepeat(
      withSequence(
        withTiming(-driftY, { duration: duration + 500, easing: Easing.inOut(Easing.sin) }),
        withTiming(driftY, { duration: duration + 500, easing: Easing.inOut(Easing.sin) }),
      ),
      -1,
      true,
    );
    scale.value = withRepeat(
      withSequence(
        withTiming(1.02, { duration: duration + 200, easing: Easing.inOut(Easing.sin) }),
        withTiming(0.985, { duration: duration + 200, easing: Easing.inOut(Easing.sin) }),
      ),
      -1,
      true,
    );
  }, []);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [
      { translateX: translateX.value },
      { translateY: translateY.value },
      { scale: scale.value },
    ],
  }));

  const gradients = BLOB_GRADIENTS[category] || BLOB_GRADIENTS.vibe_inspiration;
  const label = BLOB_LABELS[category] || category;
  const iconName = BLOB_ICONS[category] || "circle";

  return (
    <Animated.View
      style={[
        styles.blobContainer,
        {
          left: x - baseSize / 2,
          top: y - baseSize / 2,
          width: baseSize,
          height: baseSize,
        },
        animatedStyle,
      ]}
    >
      <Pressable
        onPress={onPress}
        style={({ pressed }) => [styles.pressable, pressed && styles.pressablePressed]}
        hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        accessibilityRole="button"
        accessibilityLabel={hasNotification ? `${label}, new reels` : label}
      >
        {/* Outer glow layer */}
        <View
          style={[
            styles.glowLayer,
            {
              width: baseSize + 34,
              height: baseSize + 34,
              borderRadius: (baseSize + 34) / 2,
            },
          ]}
        >
          <LinearGradient
            colors={[gradients[0] + "55", gradients[1] + "33", "transparent"]}
            style={StyleSheet.absoluteFill}
            start={{ x: 0.3, y: 0 }}
            end={{ x: 0.7, y: 1 }}
          />
        </View>

        <View style={[styles.blobWrapper, { width: baseSize, height: baseSize }]}>
          {/* Main blob */}
          <View
            style={[
              styles.blob,
              { width: baseSize, height: baseSize, borderRadius: baseSize / 2 },
            ]}
          >
            <LinearGradient
              colors={gradients}
              style={StyleSheet.absoluteFill}
              start={{ x: 0.2, y: 0 }}
              end={{ x: 0.8, y: 1 }}
            />

            {/* Inner highlight for depth */}
            <LinearGradient
              colors={["rgba(255,255,255,0.28)", "rgba(255,255,255,0.06)", "rgba(0,0,0,0.18)"]}
              style={[StyleSheet.absoluteFill, { borderRadius: baseSize / 2 }]}
              start={{ x: 0.3, y: 0 }}
              end={{ x: 0.7, y: 1 }}
            />

            <View style={[styles.blobRim, { borderRadius: baseSize / 2 }]} />

            <LinearGradient
              colors={["rgba(255,255,255,0.35)", "transparent"]}
              style={[styles.blobSheen, { borderRadius: baseSize / 2 }]}
              start={{ x: 0.1, y: 0.1 }}
              end={{ x: 0.6, y: 0.6 }}
            />

            <View
              style={[
                styles.iconCenter,
                { width: iconWrapperSize, height: iconWrapperSize, borderRadius: iconWrapperSize / 2 },
              ]}
            >
              <FontAwesome name={iconName} size={iconSize} color="rgba(255,255,255,0.95)" />
            </View>
          </View>

          {hasNotification && (
            <View
              style={[
                styles.notificationDot,
                {
                  width: dotSize,
                  height: dotSize,
                  borderRadius: dotSize / 2,
                  borderWidth: dotBorder,
                  top: -dotOffset,
                  right: -dotOffset,
                },
              ]}
            />
          )}
        </View>

        {/* Label below blob */}
        <View style={styles.labelPill}>
          <Text style={[styles.label, { fontSize: labelFontSize }]}>{label}</Text>
        </View>
      </Pressable>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  blobContainer: {
    position: "absolute",
    alignItems: "center",
    justifyContent: "center",
  },
  pressable: {
    alignItems: "center",
    justifyContent: "center",
  },
  pressablePressed: {
    opacity: 0.88,
  },
  glowLayer: {
    position: "absolute",
    overflow: "hidden",
    opacity: 0.7,
  },
  blob: {
    overflow: "hidden",
    alignItems: "center",
    justifyContent: "center",
    opacity: 0.9,
    // Shadow for depth
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.35,
    shadowRadius: 18,
    elevation: 10,
  },
  blobRim: {
    ...StyleSheet.absoluteFillObject,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.18)",
  },
  blobSheen: {
    ...StyleSheet.absoluteFillObject,
  },
  iconBadge: {
    position: "absolute",
    top: 10,
    left: 10,
    paddingHorizontal: 7,
    paddingVertical: 5,
    borderRadius: 12,
    backgroundColor: "rgba(0,0,0,0.35)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.14)",
  },
  blobWrapper: {
    alignItems: "center",
    justifyContent: "center",
  },
  iconCenter: {
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(0,0,0,0.28)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.16)",
  },
  notificationDot: {
    position: "absolute",
    backgroundColor: theme.colors.warm,
    borderColor: "rgba(255,255,255,0.9)",
    shadowColor: "rgba(0,0,0,0.6)",
    shadowOpacity: 0.65,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 0 },
    elevation: 6,
  },
  labelPill: {
    marginTop: 8,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 14,
    backgroundColor: "rgba(0,0,0,0.35)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.12)",
  },
  label: {
    fontFamily: theme.fonts.semibold,
    color: theme.colors.text,
    textAlign: "center",
    textShadowColor: "rgba(0,0,0,0.7)",
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 4,
  },
});
