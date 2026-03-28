import { View, Text, StyleSheet, Image, Pressable, Linking } from "react-native";
import { Platform as PlatformType, PLATFORM_DISPLAY } from "@/lib/utils/platform-detect";

interface ExtractionData {
  title?: string | null;
  description?: string | null;
  thumbnail_url?: string | null;
  venue_name?: string | null;
  location?: string | null;
  price?: string | null;
  date?: string | null;
  vibe?: string | null;
  activity?: string | null;
  mood?: string | null;
  booking_url?: string | null;
  creator?: string | null;
  audio_track?: string | null;
  audio_artist?: string | null;
  error?: string;
}

interface ExtractionCardProps {
  url: string;
  platform: string;
  classification: string | null;
  extractionData: ExtractionData | null;
  createdAt: string;
}

const CLASSIFICATION_STYLES: Record<string, { label: string; color: string; bg: string }> = {
  real_event: { label: "Event", color: "#d4562a", bg: "#fdf5f2" },
  real_venue: { label: "Venue", color: "#1a9e76", bg: "#f0faf6" },
  vibe_inspiration: { label: "Vibe", color: "#8b5cf6", bg: "#f5f0ff" },
  recipe_food: { label: "Food", color: "#c49a2e", bg: "#fdf8ee" },
  humour_identity: { label: "Identity", color: "#ec4899", bg: "#fdf0f7" },
};

function timeAgo(dateStr: string): string {
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export function ExtractionCard({
  url,
  platform,
  classification,
  extractionData,
  createdAt,
}: ExtractionCardProps) {
  const platformInfo = PLATFORM_DISPLAY[platform as PlatformType] || PLATFORM_DISPLAY.other;
  const classStyle = classification ? CLASSIFICATION_STYLES[classification] : null;
  const data = extractionData;

  // Loading / error states
  if (!data) {
    return (
      <View style={styles.card}>
        <View style={styles.headerRow}>
          <Text style={styles.platformBadge}>{platformInfo.emoji} {platformInfo.label}</Text>
        </View>
        <Text style={styles.analyzing}>Analyzing...</Text>
        <Text style={styles.urlText} numberOfLines={1}>{url}</Text>
      </View>
    );
  }

  if (data.error) {
    return (
      <View style={styles.card}>
        <View style={styles.headerRow}>
          <Text style={styles.platformBadge}>{platformInfo.emoji} {platformInfo.label}</Text>
        </View>
        <Text style={styles.errorText}>Could not extract this content</Text>
        <Text style={styles.urlText} numberOfLines={1}>{url}</Text>
      </View>
    );
  }

  return (
    <Pressable
      style={[styles.card, classStyle && { borderLeftColor: classStyle.color, borderLeftWidth: 4 }]}
      onPress={() => Linking.openURL(url)}
    >
      {/* Header: platform + classification + time */}
      <View style={styles.headerRow}>
        <Text style={styles.platformBadge}>{platformInfo.emoji} {platformInfo.label}</Text>
        {classStyle && (
          <View style={[styles.classBadge, { backgroundColor: classStyle.bg }]}>
            <Text style={[styles.classText, { color: classStyle.color }]}>{classStyle.label}</Text>
          </View>
        )}
        <Text style={styles.timeAgo}>{timeAgo(createdAt)}</Text>
      </View>

      {/* Thumbnail + Title row */}
      <View style={styles.contentRow}>
        {data.thumbnail_url && (
          <Image source={{ uri: data.thumbnail_url }} style={styles.thumbnail} />
        )}
        <View style={styles.contentText}>
          {data.title && (
            <Text style={styles.title} numberOfLines={2}>{data.title}</Text>
          )}
          {data.creator && (
            <Text style={styles.creator}>@{data.creator}</Text>
          )}
        </View>
      </View>

      {/* Venue / Location / Price / Date */}
      {(data.venue_name || data.location || data.price || data.date) && (
        <View style={styles.metaSection}>
          {data.venue_name && (
            <View style={styles.metaRow}>
              <Text style={styles.metaIcon}>📍</Text>
              <Text style={styles.metaText}>{data.venue_name}</Text>
            </View>
          )}
          {data.location && !data.venue_name && (
            <View style={styles.metaRow}>
              <Text style={styles.metaIcon}>📍</Text>
              <Text style={styles.metaText}>{data.location}</Text>
            </View>
          )}
          {data.price && (
            <View style={styles.metaRow}>
              <Text style={styles.metaIcon}>💰</Text>
              <Text style={styles.metaText}>{data.price}</Text>
            </View>
          )}
          {data.date && (
            <View style={styles.metaRow}>
              <Text style={styles.metaIcon}>📅</Text>
              <Text style={styles.metaText}>{data.date}</Text>
            </View>
          )}
        </View>
      )}

      {/* Vibe / Activity / Mood tags */}
      {(data.vibe || data.activity || data.mood) && (
        <View style={styles.tagRow}>
          {data.activity && <Text style={styles.tag}>{data.activity}</Text>}
          {data.vibe && <Text style={styles.tag}>{data.vibe}</Text>}
          {data.mood && <Text style={[styles.tag, styles.moodTag]}>{data.mood}</Text>}
        </View>
      )}

      {/* Audio track */}
      {data.audio_track && (
        <View style={styles.audioRow}>
          <Text style={styles.audioIcon}>🎵</Text>
          <Text style={styles.audioText}>
            {data.audio_track}{data.audio_artist ? ` — ${data.audio_artist}` : ""}
          </Text>
        </View>
      )}

      {/* Booking button for events */}
      {data.booking_url && classification === "real_event" && (
        <Pressable
          style={styles.bookingButton}
          onPress={(e) => {
            e.stopPropagation?.();
            Linking.openURL(data.booking_url!);
          }}
        >
          <Text style={styles.bookingText}>🎟 Get Tickets</Text>
        </Pressable>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#fff",
    borderRadius: 14,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: "#eee",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 1,
  },
  headerRow: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 10 },
  platformBadge: { fontSize: 13, fontWeight: "600", color: "#555" },
  classBadge: { borderRadius: 6, paddingHorizontal: 8, paddingVertical: 2 },
  classText: { fontSize: 11, fontWeight: "700", textTransform: "uppercase", letterSpacing: 0.5 },
  timeAgo: { fontSize: 11, color: "#bbb", marginLeft: "auto" },
  analyzing: { fontSize: 15, color: "#c49a2e", fontWeight: "500", marginBottom: 6 },
  errorText: { fontSize: 14, color: "#e74c3c", marginBottom: 6 },
  urlText: { fontSize: 11, color: "#ccc" },
  contentRow: { flexDirection: "row", gap: 12, marginBottom: 10 },
  thumbnail: { width: 72, height: 96, borderRadius: 8, backgroundColor: "#f0f0f0" },
  contentText: { flex: 1, justifyContent: "center" },
  title: { fontSize: 15, fontWeight: "600", color: "#333", lineHeight: 20, marginBottom: 4 },
  creator: { fontSize: 13, color: "#999" },
  metaSection: { gap: 6, marginBottom: 10 },
  metaRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  metaIcon: { fontSize: 14 },
  metaText: { fontSize: 14, color: "#555" },
  tagRow: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginBottom: 10 },
  tag: {
    fontSize: 12,
    color: "#666",
    backgroundColor: "#f5f3f0",
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 4,
    overflow: "hidden",
  },
  moodTag: { backgroundColor: "#f0edff", color: "#8b5cf6" },
  audioRow: { flexDirection: "row", alignItems: "center", gap: 6, marginBottom: 8 },
  audioIcon: { fontSize: 13 },
  audioText: { fontSize: 12, color: "#888", fontStyle: "italic" },
  bookingButton: {
    backgroundColor: "#d4562a",
    borderRadius: 10,
    paddingVertical: 10,
    alignItems: "center",
  },
  bookingText: { color: "#fff", fontSize: 14, fontWeight: "600" },
});
