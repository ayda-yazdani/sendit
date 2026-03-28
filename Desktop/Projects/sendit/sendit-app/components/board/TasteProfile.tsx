import { View, Text, StyleSheet, ActivityIndicator } from "react-native";
import { TasteProfileData } from "@/lib/ai/taste-engine";
import { Button } from "@/components/shared/Button";

interface TasteProfileDisplayProps {
  profileData: TasteProfileData;
  identityLabel: string | null;
}

function TagPill({ text, color = "#666", bg = "#f5f3f0" }: { text: string; color?: string; bg?: string }) {
  return (
    <View style={[styles.pill, { backgroundColor: bg }]}>
      <Text style={[styles.pillText, { color }]}>{text}</Text>
    </View>
  );
}

export function TasteProfileDisplay({ profileData, identityLabel }: TasteProfileDisplayProps) {
  const p = profileData;

  return (
    <View style={styles.container}>
      {/* Identity Label */}
      {identityLabel && (
        <View style={styles.identityBox}>
          <Text style={styles.identityLabel}>{identityLabel}</Text>
        </View>
      )}

      {/* Activities */}
      {p.activity_types?.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Into</Text>
          <View style={styles.pillRow}>
            {p.activity_types.map((a, i) => (
              <TagPill key={i} text={a} color="#d4562a" bg="#fdf5f2" />
            ))}
          </View>
        </View>
      )}

      {/* Food */}
      {p.food_preferences?.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Food</Text>
          <View style={styles.pillRow}>
            {p.food_preferences.map((f, i) => (
              <TagPill key={i} text={`🍽 ${f}`} color="#c49a2e" bg="#fdf8ee" />
            ))}
          </View>
        </View>
      )}

      {/* Aesthetic */}
      {p.aesthetic && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Aesthetic</Text>
          <Text style={styles.aestheticText}>{p.aesthetic}</Text>
        </View>
      )}

      {/* Location */}
      {p.location_patterns?.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Where</Text>
          <View style={styles.pillRow}>
            {p.location_patterns.map((l, i) => (
              <TagPill key={i} text={`📍 ${l}`} color="#1a9e76" bg="#f0faf6" />
            ))}
          </View>
        </View>
      )}

      {/* Price + Humour row */}
      <View style={styles.metaRow}>
        {p.price_range && (
          <View style={styles.metaItem}>
            <Text style={styles.metaLabel}>Budget</Text>
            <Text style={styles.metaValue}>💰 {p.price_range}</Text>
          </View>
        )}
        {p.humour_style && p.humour_style !== "not enough data yet" && (
          <View style={styles.metaItem}>
            <Text style={styles.metaLabel}>Humour</Text>
            <Text style={styles.metaValue}>😂 {p.humour_style}</Text>
          </View>
        )}
      </View>

      {/* Platform Mix */}
      {p.platform_mix && Object.keys(p.platform_mix).length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Sources</Text>
          <View style={styles.platformRow}>
            {Object.entries(p.platform_mix).map(([platform, count]) => (
              <View key={platform} style={styles.platformChip}>
                <Text style={styles.platformName}>{platform}</Text>
                <Text style={styles.platformCount}>{count}</Text>
              </View>
            ))}
          </View>
        </View>
      )}
    </View>
  );
}

interface TasteProfileSectionProps {
  profileData: TasteProfileData | null;
  identityLabel: string | null;
  isLoading: boolean;
  reelCount: number;
  onGenerate: () => void;
}

export function TasteProfileSection({
  profileData,
  identityLabel,
  isLoading,
  reelCount,
  onGenerate,
}: TasteProfileSectionProps) {
  if (isLoading) {
    return (
      <View style={styles.emptyContainer}>
        <ActivityIndicator size="small" color="#d4562a" />
        <Text style={styles.emptyText}>Building taste profile...</Text>
      </View>
    );
  }

  if (!profileData) {
    return (
      <View style={styles.emptyContainer}>
        <Text style={styles.emptyIcon}>🌡</Text>
        <Text style={styles.emptyTitle}>No taste profile yet</Text>
        {reelCount >= 3 ? (
          <>
            <Text style={styles.emptyText}>Ready to analyze your group's taste</Text>
            <Button title="Build Taste Profile" onPress={onGenerate} style={{ marginTop: 12, width: "100%" }} />
          </>
        ) : (
          <Text style={styles.emptyText}>Share {3 - reelCount} more reel{3 - reelCount !== 1 ? "s" : ""} to unlock</Text>
        )}
      </View>
    );
  }

  return <TasteProfileDisplay profileData={profileData} identityLabel={identityLabel} />;
}

const styles = StyleSheet.create({
  container: { backgroundColor: "#fff", borderRadius: 16, padding: 16, borderWidth: 1, borderColor: "#eee" },
  identityBox: {
    backgroundColor: "#0e0c0a",
    borderRadius: 12,
    padding: 14,
    marginBottom: 16,
    alignItems: "center",
  },
  identityLabel: { fontSize: 18, fontWeight: "bold", color: "#eeebe3", letterSpacing: 0.5 },
  section: { marginBottom: 14 },
  sectionLabel: { fontSize: 11, fontWeight: "700", color: "#999", textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 },
  pillRow: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  pill: { borderRadius: 8, paddingHorizontal: 10, paddingVertical: 5 },
  pillText: { fontSize: 13, fontWeight: "500" },
  aestheticText: { fontSize: 15, color: "#555", fontStyle: "italic" },
  metaRow: { flexDirection: "row", gap: 20, marginBottom: 14 },
  metaItem: { flex: 1 },
  metaLabel: { fontSize: 11, fontWeight: "700", color: "#999", textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 },
  metaValue: { fontSize: 14, color: "#555" },
  platformRow: { flexDirection: "row", gap: 8 },
  platformChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: "#f5f3f0",
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  platformName: { fontSize: 12, color: "#666", textTransform: "capitalize" },
  platformCount: { fontSize: 12, fontWeight: "700", color: "#333" },
  emptyContainer: {
    alignItems: "center",
    paddingVertical: 28,
    paddingHorizontal: 20,
    backgroundColor: "#f9f7f5",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#eee",
  },
  emptyIcon: { fontSize: 36, marginBottom: 10 },
  emptyTitle: { fontSize: 16, fontWeight: "600", color: "#333", marginBottom: 6 },
  emptyText: { fontSize: 13, color: "#999", textAlign: "center" },
});
