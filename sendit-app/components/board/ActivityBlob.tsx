import { useEffect } from "react";
import { View, Text, StyleSheet, Pressable } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
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
};

const BLOB_LABELS: Record<string, string> = {
  real_event: "Events",
  real_venue: "Venues",
  recipe_food: "Food",
  vibe_inspiration: "Vibes",
  humour_identity: "Humour",
};

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
}

export function ActivityBlob({ category, reelCount, reels, x, y, onPress, index }: ActivityBlobProps) {
  // Size based on reel count — min 100, max 180
  const baseSize = Math.min(180, Math.max(100, 80 + reelCount * 20));

  // Floating animation — each blob drifts differently
  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);
  const scale = useSharedValue(1);

  useEffect(() => {
    const driftX = 6 + (index % 3) * 4;
    const driftY = 8 + (index % 2) * 5;
    const duration = 3000 + index * 700;

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
        withTiming(1.04, { duration: duration + 200, easing: Easing.inOut(Easing.sin) }),
        withTiming(0.96, { duration: duration + 200, easing: Easing.inOut(Easing.sin) }),
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
      <Pressable onPress={onPress} style={styles.pressable}>
        {/* Outer glow layer */}
        <View style={[styles.glowLayer, { width: baseSize + 30, height: baseSize + 30, borderRadius: (baseSize + 30) / 2 }]}>
          <LinearGradient
            colors={[gradients[0] + "40", gradients[1] + "20", "transparent"]}
            style={StyleSheet.absoluteFill}
            start={{ x: 0.3, y: 0 }}
            end={{ x: 0.7, y: 1 }}
          />
        </View>

        {/* Main blob */}
        <View style={[styles.blob, { width: baseSize, height: baseSize, borderRadius: baseSize / 2 }]}>
          <LinearGradient
            colors={gradients}
            style={StyleSheet.absoluteFill}
            start={{ x: 0.2, y: 0 }}
            end={{ x: 0.8, y: 1 }}
          />

          {/* Inner highlight for 3D depth */}
          <LinearGradient
            colors={["rgba(255,255,255,0.15)", "transparent", "rgba(0,0,0,0.1)"]}
            style={[StyleSheet.absoluteFill, { borderRadius: baseSize / 2 }]}
            start={{ x: 0.3, y: 0 }}
            end={{ x: 0.7, y: 1 }}
          />

          {/* Mini reel card previews inside blob */}
          <View style={styles.reelPreviews}>
            {reels.slice(0, 3).map((reel, i) => (
              <View
                key={reel.id}
                style={[
                  styles.miniCard,
                  {
                    transform: [
                      { rotate: `${-8 + i * 8}deg` },
                      { translateX: -10 + i * 10 },
                      { translateY: -5 + i * 5 },
                    ],
                  },
                ]}
              >
                <View style={styles.miniCardLine} />
                <View style={[styles.miniCardLine, { width: "60%" }]} />
              </View>
            ))}
          </View>

          {/* Reel count */}
          <View style={styles.countBadge}>
            <Text style={styles.countText}>{reelCount}</Text>
          </View>
        </View>

        {/* Label below blob */}
        <Text style={styles.label}>{label}</Text>
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
  glowLayer: {
    position: "absolute",
    overflow: "hidden",
    opacity: 0.5,
  },
  blob: {
    overflow: "hidden",
    alignItems: "center",
    justifyContent: "center",
    opacity: 0.75,
    // Shadow for depth
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.4,
    shadowRadius: 16,
    elevation: 12,
  },
  reelPreviews: {
    alignItems: "center",
    justifyContent: "center",
  },
  miniCard: {
    width: 36,
    height: 24,
    backgroundColor: "rgba(255,255,255,0.2)",
    borderRadius: 4,
    padding: 4,
    marginVertical: 1,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.3,
    shadowRadius: 2,
  },
  miniCardLine: {
    width: "80%",
    height: 3,
    backgroundColor: "rgba(255,255,255,0.3)",
    borderRadius: 2,
    marginBottom: 2,
  },
  countBadge: {
    position: "absolute",
    bottom: 8,
    right: 8,
    backgroundColor: "rgba(0,0,0,0.5)",
    borderRadius: 10,
    paddingHorizontal: 7,
    paddingVertical: 2,
  },
  countText: {
    color: "#fff",
    fontSize: 11,
    fontFamily: theme.fonts.bold,
  },
  label: {
    marginTop: 8,
    fontSize: 13,
    fontFamily: theme.fonts.semibold,
    color: theme.colors.text,
    textAlign: "center",
    textShadowColor: "rgba(0,0,0,0.8)",
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 4,
  },
});
