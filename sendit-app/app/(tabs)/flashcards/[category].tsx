import { useEffect, useState, useCallback, useMemo } from "react";
import {
  View,
  Text,
  StyleSheet,
  Dimensions,
  Image,
  ScrollView,
  RefreshControl,
  Pressable,
  ActivityIndicator,
  Animated,
  PanResponder,
} from "react-native";
import { useLocalSearchParams, router } from "expo-router";
import FontAwesome from "@expo/vector-icons/FontAwesome";
import { generateSuggestion, Suggestion } from "@/lib/ai/suggestion-engine";
import { listBoardMembers, listBoardReels } from "@/lib/api/boards";
import { useAuthStore } from "@/lib/stores/auth-store";
import { theme } from "@/constants/Theme";
import { markReelReacted, unmarkReelReacted } from "@/lib/utils/reel-reactions";

// Decode HTML entities in URLs and text from extraction
function decodeHtml(text: string | null | undefined): string {
  if (!text) return "";
  return text
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#x27;/g, "'")
    .replace(/&#x2019;/g, "\u2019")
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(parseInt(n)))
    .replace(/&#x([0-9a-fA-F]+);/g, (_, h) => String.fromCharCode(parseInt(h, 16)));
}

function pickPreviewImage(data: any) {
  const frame = typeof data?.frame_image_url === "string" ? data.frame_image_url : "";
  if (frame) return decodeHtml(frame);

  const previewImages = Array.isArray(data?.preview_image_urls) ? data.preview_image_urls : [];
  const previewUrl = previewImages.find(
    (item: unknown) => typeof item === "string" && item.trim().length > 0
  ) as string | undefined;
  if (previewUrl) return decodeHtml(previewUrl);

  const thumb = typeof data?.thumbnail_url === "string" ? data.thumbnail_url : "";
  return decodeHtml(thumb);
}

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get("window");
const CARD_WIDTH = SCREEN_WIDTH - 40;
const CARD_HEIGHT = Math.max(420, Math.round(SCREEN_HEIGHT * 0.6));
const CARD_IMAGE_HEIGHT = Math.round(CARD_HEIGHT * 0.55);
const SWIPE_THRESHOLD = SCREEN_WIDTH * 0.3;

const CATEGORY_LABELS: Record<string, string> = {
  real_event: "Events",
  real_venue: "Venues",
  recipe_food: "Food",
  vibe_inspiration: "Vibes",
  humour_identity: "Humour",
  uncategorised: "Other",
};

const CATEGORY_COLORS: Record<string, string> = {
  real_event: "#982649",
  real_venue: "#3C6E71",
  recipe_food: "#D8A48F",
  vibe_inspiration: "#284B63",
  humour_identity: "#982649",
  uncategorised: "#555555",
};

interface Reel {
  id: string;
  url: string;
  platform: string;
  extraction_data: any;
  classification: string | null;
  created_at: string;
  board_id: string;
}

interface SwipedReel {
  reel: Reel;
  direction: "left" | "right";
}

export default function FlashcardScreen() {
  const { category: rawCategory, boardId: rawBoardId } = useLocalSearchParams<{ category?: string | string[]; boardId?: string | string[] }>();
  const category = Array.isArray(rawCategory) ? rawCategory[0] : rawCategory;
  const boardId = Array.isArray(rawBoardId) ? rawBoardId[0] : rawBoardId;
  const session = useAuthStore((state) => state.session);
  const [reels, setReels] = useState<Reel[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [swipedReels, setSwipedReels] = useState<SwipedReel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [suggestion, setSuggestion] = useState<Suggestion | null>(null);
  const [isGeneratingSuggestion, setIsGeneratingSuggestion] = useState(false);

  const loadData = useCallback(async (showLoading: boolean) => {
    if (!boardId || !category) return;
    if (showLoading) {
      setIsLoading(true);
    } else {
      setIsRefreshing(true);
    }

    try {
      if (session) {
        const members = await listBoardMembers(session, boardId);
        const currentMember = members.find((member) => member.device_id === session.user.id);
        if (currentMember) {
          const data = await listBoardReels(session, boardId, currentMember.id);
          const filtered = data.filter(
            (r: Reel) => (r.classification || "uncategorised") === category
          );
          setReels(filtered);
        }
      }

      const generatedSuggestion = await generateSuggestion(boardId, category);
      if (generatedSuggestion.data) setSuggestion(generatedSuggestion.data);
    } finally {
      if (showLoading) {
        setIsLoading(false);
      } else {
        setIsRefreshing(false);
      }
    }
  }, [boardId, category, session]);

  useEffect(() => {
    void loadData(true);
  }, [loadData]);

  const handleRefresh = useCallback(() => {
    void loadData(false);
  }, [loadData]);

  // Trigger suggestion generation once the user has liked at least 1 reel
  useEffect(() => {
    if (!boardId || suggestion || isGeneratingSuggestion) return;
    const hasLikes = swipedReels.some((s) => s.direction === "right");
    if (!hasLikes) return;

    setIsGeneratingSuggestion(true);
    generateSuggestion(boardId)
      .then((result) => {
        if (result.data) setSuggestion(result.data);
      })
      .catch((err) => console.warn("Suggestion generation failed:", err))
      .finally(() => setIsGeneratingSuggestion(false));
  }, [swipedReels, boardId, suggestion, isGeneratingSuggestion]);

  const allSwiped = currentIndex >= reels.length;
  const currentReel = reels[currentIndex];

  const handleSwipe = useCallback((direction: "left" | "right") => {
    if (currentIndex >= reels.length) return;
    const reel = reels[currentIndex];
    setSwipedReels((prev) => [...prev, { reel, direction }]);
    setCurrentIndex((prev) => prev + 1);
    if (boardId) {
      void markReelReacted(boardId, reel.id);
    }
  }, [currentIndex, reels, boardId]);

  const handleSkip = useCallback(() => {
    handleSwipe("left");
  }, [handleSwipe]);

  const handleUndo = useCallback(() => {
    if (currentIndex <= 0) return;
    const lastSwiped = swipedReels[swipedReels.length - 1];
    if (boardId && lastSwiped) {
      void unmarkReelReacted(boardId, lastSwiped.reel.id);
    }
    setCurrentIndex((prev) => prev - 1);
    setSwipedReels((prev) => prev.slice(0, -1));
  }, [currentIndex, swipedReels, boardId]);

  const handleRestart = useCallback(() => {
    setCurrentIndex(0);
    setSwipedReels([]);
  }, []);

  const likedReels = useMemo(
    () => swipedReels.filter((s) => s.direction === "right"),
    [swipedReels]
  );

  const label = CATEGORY_LABELS[category || ""] || category || "Reels";
  const accent = CATEGORY_COLORS[category || ""] || "#3C6E71";

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={accent} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Pressable onPress={() => router.push(`/board/${boardId}`)} style={styles.backButton}>
          <FontAwesome name="chevron-left" size={16} color={theme.colors.text} />
        </Pressable>
        <View style={styles.headerCenter}>
          <Text style={styles.headerTitle}>{label}</Text>
          <Text style={styles.headerSubtitle}>
            {Math.min(currentIndex + 1, reels.length)}/{reels.length}
            {likedReels.length > 0 ? ` · ${likedReels.length} liked` : ""}
          </Text>
        </View>
        <View style={[styles.dot, { backgroundColor: accent }]} />
      </View>

      <ScrollView
        style={styles.screenScroll}
        contentContainerStyle={styles.screenContent}
        showsVerticalScrollIndicator={false}
        alwaysBounceVertical
        refreshControl={
          <RefreshControl
            refreshing={isRefreshing}
            onRefresh={handleRefresh}
            tintColor={accent}
          />
        }
      >
        {/* TOP: Single flashcard */}
        <View style={styles.topSection}>
          {!allSwiped && currentReel ? (
            <SwipeableCard
              key={currentReel.id}
              reel={currentReel}
              accent={accent}
              onSwipe={handleSwipe}
            />
          ) : (
            <View style={styles.doneContainer}>
              <Text style={styles.doneEmoji}>✨</Text>
              <Text style={styles.doneTitle}>All caught up</Text>
              <Text style={styles.doneSubtitle}>
                You liked {likedReels.length} of {reels.length}
              </Text>
              {reels.length > 0 && (
                <Pressable style={[styles.restartButton, { borderColor: accent }]} onPress={handleRestart}>
                  <Text style={[styles.restartButtonText, { color: accent }]}>Do them again</Text>
                </Pressable>
              )}
            </View>
          )}

          {/* Action row */}
          {!allSwiped && (
            <View style={styles.actions}>
              <View style={styles.swipeLabel}>
                <FontAwesome name="arrow-left" size={10} color="#555" />
                <Text style={styles.swipeLabelText}>Nah</Text>
              </View>

              <View style={styles.actionButtons}>
                {currentIndex > 0 && (
                  <Pressable style={styles.undoButton} onPress={handleUndo}>
                    <FontAwesome name="undo" size={14} color="#888" />
                  </Pressable>
                )}
                <Pressable style={styles.skipButton} onPress={handleSkip}>
                  <FontAwesome name="forward" size={14} color="#666" />
                </Pressable>
              </View>

              <View style={styles.swipeLabel}>
                <Text style={[styles.swipeLabelText, { color: accent }]}>Like</Text>
                <FontAwesome name="arrow-right" size={10} color={accent} />
              </View>
            </View>
          )}
        </View>

        {/* BOTTOM: Recommendation feed */}
        <View style={styles.feedDivider} />
        <View style={styles.feedContent}>
          <Text style={styles.feedSectionTitle}>Recommended for you</Text>

          {/* AI-generated plan suggestion */}
          {suggestion ? (
            <MiniSuggestion suggestion={suggestion} accent={accent} />
          ) : (
            <View style={styles.suggestionEmpty}>
              {isGeneratingSuggestion && (
                <ActivityIndicator size="small" color={accent} style={{ marginBottom: 8 }} />
              )}
              <Text style={styles.suggestionEmptyText}>
                {isGeneratingSuggestion
                  ? "Generating personalised suggestions..."
                  : likedReels.length > 0
                    ? "Generating personalised suggestions..."
                    : "Swipe to unlock activity suggestions"}
              </Text>
            </View>
          )}

          {/* Liked reels as preference signal */}
          {likedReels.length > 0 && (
            <>
              <Text style={[styles.feedSectionTitle, { marginTop: 16 }]}>You're into</Text>
              {likedReels.map(({ reel }, i) => (
                <FeedItem key={`${reel.id}-${i}`} reel={reel} accent={accent} />
              ))}
            </>
          )}

          <View style={{ height: 30 }} />
        </View>
      </ScrollView>
    </View>
  );
}

// Swipeable single card using RN Animated + PanResponder (JS thread safe)
function SwipeableCard({ reel, accent, onSwipe }: { reel: Reel; accent: string; onSwipe: (dir: "left" | "right") => void }) {
  const pan = useMemo(() => new Animated.ValueXY(), []);

  const panResponder = useMemo(() => PanResponder.create({
    onStartShouldSetPanResponder: () => true,
    onMoveShouldSetPanResponder: (_, g) => Math.abs(g.dx) > 8,
    onMoveShouldSetPanResponderCapture: (_, g) => Math.abs(g.dx) > Math.abs(g.dy) && Math.abs(g.dx) > 8,
    onPanResponderTerminationRequest: () => false,
    onPanResponderMove: Animated.event([null, { dx: pan.x }], { useNativeDriver: false }),
    onPanResponderRelease: (_, gesture) => {
      if (gesture.dx > SWIPE_THRESHOLD) {
        Animated.timing(pan.x, { toValue: SCREEN_WIDTH * 1.5, duration: 250, useNativeDriver: true }).start(() => {
          onSwipe("right");
        });
      } else if (gesture.dx < -SWIPE_THRESHOLD) {
        Animated.timing(pan.x, { toValue: -SCREEN_WIDTH * 1.5, duration: 250, useNativeDriver: true }).start(() => {
          onSwipe("left");
        });
      } else {
        Animated.spring(pan.x, { toValue: 0, friction: 6, useNativeDriver: true }).start();
      }
    },
  }), [pan, onSwipe]);

  const cardStyle = {
    transform: [
      { translateX: pan.x },
      { rotate: pan.x.interpolate({
        inputRange: [-SCREEN_WIDTH, 0, SCREEN_WIDTH],
        outputRange: ["-12deg", "0deg", "12deg"],
      })},
    ],
  };

  const data = reel.extraction_data || {};
  const title = decodeHtml(data.title) || "Untitled";
  const thumbnailUrl = pickPreviewImage(data);
  const creator = data.creator || data.platform_metadata?.username;
  const venue = data.venue_name;
  const price = data.price;
  const vibe = data.vibe;
  const activity = data.activity;
  const platform = reel.platform;

  const icons: Record<string, string> = {
    youtube: "youtube-play", instagram: "instagram", tiktok: "music", x: "twitter",
  };

  return (
    <Animated.View {...panResponder.panHandlers} style={[styles.card, cardStyle]}>
        {thumbnailUrl ? (
          <Image source={{ uri: thumbnailUrl }} style={styles.cardImage} resizeMode="cover" />
        ) : (
          <View style={[styles.cardImage, { backgroundColor: accent + "20" }]} />
        )}
        <View style={styles.cardBody}>
          <View style={styles.cardTopRow}>
            <View style={[styles.platformBadge, { backgroundColor: accent + "20" }]}>
              <FontAwesome name={(icons[platform] || "globe") as any} size={11} color={accent} />
              <Text style={[styles.platformText, { color: accent }]}>{platform}</Text>
            </View>
            {creator && <Text style={styles.creator} numberOfLines={1}>@{creator}</Text>}
          </View>
          <Text style={styles.cardTitle} numberOfLines={2}>{title}</Text>
          {(venue || price || vibe || activity) && (
            <View style={styles.cardMeta}>
              {venue && (
                <View style={styles.metaItem}>
                  <FontAwesome name="map-marker" size={10} color={theme.colors.warm} />
                  <Text style={styles.metaText}>{venue}</Text>
                </View>
              )}
              {price && (
                <View style={styles.metaItem}>
                  <FontAwesome name="gbp" size={10} color={theme.colors.tertiary} />
                  <Text style={styles.metaText}>{price}</Text>
                </View>
              )}
              {vibe && <View style={styles.metaItem}><Text style={styles.metaText}>{vibe}</Text></View>}
              {activity && <View style={styles.metaItem}><Text style={styles.metaText}>{activity}</Text></View>}
            </View>
          )}
        </View>
      </Animated.View>
  );
}

function MiniSuggestion({ suggestion, accent }: { suggestion: Suggestion; accent: string }) {
  const data = suggestion.suggestion_data || {};
  return (
    <View style={[styles.miniSuggestion, { borderLeftColor: accent }]}>
      <Text style={styles.miniSuggestionLabel}>Suggestion</Text>
      <Text style={styles.miniSuggestionWhat} numberOfLines={2}>{data.what || "Plan incoming..."}</Text>
      {data.where && (
        <View style={styles.metaItem}>
          <FontAwesome name="map-marker" size={10} color={theme.colors.warm} />
          <Text style={styles.metaText}>{data.where}</Text>
        </View>
      )}
      {data.cost_per_person && (
        <View style={styles.metaItem}>
          <FontAwesome name="gbp" size={10} color={theme.colors.tertiary} />
          <Text style={styles.metaText}>{data.cost_per_person}/person</Text>
        </View>
      )}
    </View>
  );
}

function FeedItem({ reel, accent }: { reel: Reel; accent: string }) {
  const data = reel.extraction_data || {};
  const thumb = pickPreviewImage(data);
  const title = decodeHtml(data.title) || "Untitled";
  // Clean title: remove "on Instagram:" prefix patterns
  const cleanTitle = title.replace(/^.{1,30} on Instagram: "?/i, "").replace(/"$/, "");
  return (
    <View style={styles.feedItem}>
      {thumb ? (
        <Image source={{ uri: thumb }} style={styles.feedThumb} resizeMode="cover" />
      ) : (
        <View style={[styles.feedThumb, { backgroundColor: accent + "15" }]} />
      )}
      <View style={styles.feedItemBody}>
        <Text style={styles.feedItemTitle} numberOfLines={2}>{cleanTitle}</Text>
        {data.venue_name && <Text style={styles.feedItemMeta}>{data.venue_name}</Text>}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#000" },
  loadingContainer: { flex: 1, backgroundColor: "#000", alignItems: "center", justifyContent: "center" },

  header: {
    flexDirection: "row", alignItems: "center",
    paddingHorizontal: 16, paddingTop: 52, paddingBottom: 6,
  },
  backButton: {
    width: 32, height: 32, borderRadius: 16,
    backgroundColor: "rgba(255,255,255,0.08)",
    alignItems: "center", justifyContent: "center",
  },
  headerCenter: { flex: 1, marginHorizontal: 10 },
  headerTitle: { fontSize: 18, fontFamily: theme.fonts.bold, color: theme.colors.text },
  headerSubtitle: { fontSize: 11, fontFamily: theme.fonts.regular, color: "#666" },
  dot: { width: 10, height: 10, borderRadius: 5 },

  // Top section
  screenScroll: { flex: 1 },
  screenContent: { paddingBottom: 16 },
  topSection: { paddingHorizontal: 20, paddingTop: 8, paddingBottom: 8 },

  // Single card
  card: {
    width: CARD_WIDTH,
    minHeight: CARD_HEIGHT,
    backgroundColor: "#1a1a1a",
    borderRadius: 16,
    overflow: "hidden",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.5,
    shadowRadius: 12,
    elevation: 10,
  },
  cardImage: {
    width: "100%", height: CARD_IMAGE_HEIGHT,
    backgroundColor: "#2a2a2a",
    alignItems: "center", justifyContent: "center",
  },
  cardBody: { padding: 12 },
  cardTopRow: { flexDirection: "row", alignItems: "center", marginBottom: 4 },
  platformBadge: {
    flexDirection: "row", alignItems: "center",
    paddingHorizontal: 7, paddingVertical: 3, borderRadius: 6, gap: 4,
  },
  platformText: { fontSize: 11, fontFamily: theme.fonts.semibold, textTransform: "capitalize" },
  creator: { fontSize: 11, fontFamily: theme.fonts.regular, color: "#777", marginLeft: 8, flex: 1 },
  cardTitle: { fontSize: 15, fontFamily: theme.fonts.bold, color: theme.colors.text, lineHeight: 18 },
  cardMeta: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 6 },
  metaItem: { flexDirection: "row", alignItems: "center", gap: 4 },
  metaText: { fontSize: 10, fontFamily: theme.fonts.regular, color: "#999" },

  // Actions
  actions: {
    flexDirection: "row", justifyContent: "space-between", alignItems: "center",
    paddingHorizontal: 12, paddingTop: 10,
  },
  swipeLabel: { flexDirection: "row", alignItems: "center", gap: 5 },
  swipeLabelText: { fontSize: 12, fontFamily: theme.fonts.semibold, color: "#555" },
  actionButtons: { flexDirection: "row", gap: 12 },
  undoButton: {
    width: 36, height: 36, borderRadius: 18,
    backgroundColor: "rgba(255,255,255,0.06)",
    alignItems: "center", justifyContent: "center",
  },
  skipButton: {
    width: 36, height: 36, borderRadius: 18,
    backgroundColor: "rgba(255,255,255,0.06)",
    alignItems: "center", justifyContent: "center",
  },

  // Done
  doneContainer: { alignItems: "center", paddingVertical: 40 },
  doneEmoji: { fontSize: 32, marginBottom: 8 },
  doneTitle: { fontSize: 20, fontFamily: theme.fonts.bold, color: theme.colors.text, marginBottom: 4 },
  doneSubtitle: { fontSize: 13, fontFamily: theme.fonts.regular, color: "#888" },
  restartButton: {
    marginTop: 16,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 18,
    borderWidth: 1,
    backgroundColor: "rgba(255,255,255,0.04)",
  },
  restartButtonText: { fontSize: 13, fontFamily: theme.fonts.semibold },

  // Feed
  feedDivider: { height: 0.5, backgroundColor: "rgba(255,255,255,0.08)", marginHorizontal: 16, marginTop: 8 },
  feedContent: { padding: 16, paddingTop: 12 },
  feedSectionTitle: { fontSize: 14, fontFamily: theme.fonts.bold, color: theme.colors.text, marginBottom: 10 },

  miniSuggestion: {
    backgroundColor: "#1a1a1a", borderRadius: 12, padding: 12,
    borderLeftWidth: 3, marginBottom: 12,
  },
  miniSuggestionLabel: {
    fontSize: 10, fontFamily: theme.fonts.semibold, color: "#666",
    textTransform: "uppercase", letterSpacing: 1, marginBottom: 4,
  },
  miniSuggestionWhat: {
    fontSize: 14, fontFamily: theme.fonts.bold, color: theme.colors.text,
    lineHeight: 19, marginBottom: 6,
  },

  suggestionEmpty: {
    backgroundColor: "#1a1a1a", borderRadius: 12, padding: 14,
    alignItems: "center", marginBottom: 12,
  },
  suggestionEmptyText: { fontSize: 12, fontFamily: theme.fonts.regular, color: "#666" },

  feedItem: {
    flexDirection: "row", backgroundColor: "#1a1a1a",
    borderRadius: 10, overflow: "hidden", marginBottom: 8,
  },
  feedThumb: { width: 60, height: 50, backgroundColor: "#2a2a2a" },
  feedItemBody: { flex: 1, padding: 8, justifyContent: "center" },
  feedItemTitle: { fontSize: 12, fontFamily: theme.fonts.semibold, color: theme.colors.text, lineHeight: 16 },
  feedItemMeta: { fontSize: 10, fontFamily: theme.fonts.regular, color: "#888", marginTop: 2 },
});
