import { View, Text, StyleSheet, Image, Pressable, Linking } from "react-native";
import { Platform as PlatformType, PLATFORM_DISPLAY } from "@/lib/utils/platform-detect";
import { theme } from "@/constants/Theme";

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
  real_event: { label: "Event", color: "#9b1b4a", bg: "rgba(155,27,74,0.15)" },
  real_venue: { label: "Venue", color: "#4d8a8a", bg: "rgba(77,138,138,0.15)" },
  vibe_inspiration: { label: "Vibe", color: "#c9917a", bg: "rgba(201,145,122,0.15)" },
  recipe_food: { label: "Food", color: "#a3b899", bg: "rgba(163,184,153,0.15)" },
  humour_identity: { label: "Identity", color: "#b8265e", bg: "rgba(184,38,94,0.15)" },
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
    backgroundColor: theme.colors.bgCard,
    borderRadius: 14,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: theme.colors.borderLight,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 2,
  },
  headerRow: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 10 },
  platformBadge: { fontSize: 13, fontWeight: "600", color: theme.colors.textSecondary },
  classBadge: { borderRadius: 6, paddingHorizontal: 8, paddingVertical: 2 },
  classText: { fontSize: 11, fontWeight: "700", textTransform: "uppercase", letterSpacing: 0.5 },
  timeAgo: { fontSize: 11, color: theme.colors.textMuted, marginLeft: "auto" },
  analyzing: { fontSize: 15, color: theme.colors.warm, fontWeight: "500", marginBottom: 6 },
  errorText: { fontSize: 14, color: theme.colors.warm, marginBottom: 6 },
  urlText: { fontSize: 11, color: theme.colors.textMuted },
  contentRow: { flexDirection: "row", gap: 12, marginBottom: 10 },
  thumbnail: { width: 72, height: 96, borderRadius: 10, backgroundColor: theme.colors.bgCardLight },
  contentText: { flex: 1, justifyContent: "center" },
  title: { fontSize: 15, fontWeight: "600", color: theme.colors.text, lineHeight: 20, marginBottom: 4 },
  creator: { fontSize: 13, color: theme.colors.textSecondary },
  metaSection: { gap: 6, marginBottom: 10 },
  metaRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  metaIcon: { fontSize: 14 },
  metaText: { fontSize: 14, color: theme.colors.textSecondary },
  tagRow: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginBottom: 10 },
  tag: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    backgroundColor: theme.colors.bgCardLight,
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 4,
    overflow: "hidden",
  },
  moodTag: { backgroundColor: "rgba(184,38,94,0.15)", color: theme.colors.primaryLight },
  audioRow: { flexDirection: "row", alignItems: "center", gap: 6, marginBottom: 8 },
  audioIcon: { fontSize: 13 },
  audioText: { fontSize: 12, color: theme.colors.textSecondary, fontStyle: "italic" },
  bookingButton: {
    backgroundColor: theme.colors.primary,
    borderRadius: 10,
    paddingVertical: 10,
    alignItems: "center",
  },
  bookingText: { color: "#fff", fontSize: 14, fontWeight: "600" },
});
