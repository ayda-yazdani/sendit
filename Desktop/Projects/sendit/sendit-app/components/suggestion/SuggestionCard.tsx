import { useState } from "react";
import { View, Text, StyleSheet, Pressable, Linking, ActivityIndicator } from "react-native";
import { router } from "expo-router";
import { Suggestion, generateSuggestion, archiveSuggestion } from "@/lib/ai/suggestion-engine";
import { Button } from "@/components/shared/Button";
import { theme } from "@/constants/Theme";

interface SuggestionCardProps {
  suggestion: Suggestion;
  boardId: string;
  onNewSuggestion: (suggestion: Suggestion) => void;
}

export function SuggestionCard({ suggestion, boardId, onNewSuggestion }: SuggestionCardProps) {
  const [showWhy, setShowWhy] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const s = suggestion.suggestion_data;

  const handleBooking = () => {
    if (s.booking_url) Linking.openURL(s.booking_url);
  };

  const handleRegenerate = async () => {
    setIsRegenerating(true);
    try {
      await archiveSuggestion(suggestion.id);
      const result = await generateSuggestion(boardId, s.what);
      if (result.data) onNewSuggestion(result.data);
    } catch (err) {
      console.error("Regenerate failed:", err);
    } finally {
      setIsRegenerating(false);
    }
  };

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Text style={styles.label}>SUGGESTED PLAN</Text>
        <Text style={styles.emoji}>💡</Text>
      </View>

      <Text style={styles.what}>{s.what}</Text>

      <View style={styles.details}>
        <View style={styles.detailRow}>
          <Text style={styles.detailIcon}>📍</Text>
          <Text style={styles.detailText}>{s.where}</Text>
        </View>
        <View style={styles.detailRow}>
          <Text style={styles.detailIcon}>📅</Text>
          <Text style={styles.detailText}>{s.when}</Text>
        </View>
        <View style={styles.detailRow}>
          <Text style={styles.detailIcon}>💰</Text>
          <Text style={styles.detailText}>{s.cost_per_person} per person</Text>
        </View>
      </View>

      {/* Why this? */}
      <Pressable onPress={() => setShowWhy(!showWhy)} style={styles.whyToggle}>
        <Text style={styles.whyToggleText}>
          {showWhy ? "Hide reasoning ▲" : "Why this? ▼"}
        </Text>
      </Pressable>
      {showWhy && (
        <View style={styles.whyBox}>
          <Text style={styles.whyText}>{s.why}</Text>
          {s.influenced_by?.length > 0 && (
            <Text style={styles.influencedBy}>
              Based on {s.influenced_by.length} reel{s.influenced_by.length !== 1 ? "s" : ""} your group shared
            </Text>
          )}
        </View>
      )}

      {/* Actions */}
      <Button
        title="View Plan & Vote"
        onPress={() => router.push(`/suggestion/${suggestion.id}`)}
        style={{ marginBottom: 8 }}
      />
      <View style={styles.actions}>
        {s.booking_url ? (
          <Button title="Book Now" onPress={handleBooking} variant="secondary" style={{ flex: 1, marginRight: 8 }} />
        ) : null}
        <Button
          title={isRegenerating ? "..." : "Different Idea"}
          onPress={handleRegenerate}
          variant="ghost"
          loading={isRegenerating}
          style={{ flex: 1 }}
        />
      </View>
    </View>
  );
}

interface SuggestionEmptyProps {
  boardId: string;
  onGenerated: (suggestion: Suggestion) => void;
  hasEnoughReels: boolean;
}

export function SuggestionEmpty({ boardId, onGenerated, hasEnoughReels }: SuggestionEmptyProps) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const result = await generateSuggestion(boardId);
      if (result.data) onGenerated(result.data);
      else if (result.message) setError(result.message);
      else if (result.error) setError(result.error);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <View style={styles.emptyCard}>
      <Text style={styles.emptyIcon}>💡</Text>
      <Text style={styles.emptyTitle}>No suggestion yet</Text>
      {hasEnoughReels ? (
        <>
          <Text style={styles.emptyHint}>Ready to generate a plan from your group's taste</Text>
          <Button
            title={isGenerating ? "Thinking..." : "Generate Suggestion"}
            onPress={handleGenerate}
            loading={isGenerating}
            style={{ marginTop: 16, width: "100%" }}
          />
        </>
      ) : (
        <Text style={styles.emptyHint}>Share 3+ reels to unlock AI suggestions</Text>
      )}
      {error && <Text style={styles.errorText}>{error}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: theme.colors.bgCard,
    borderRadius: 16,
    padding: 20,
    borderWidth: 2,
    borderColor: theme.colors.primary,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 3,
  },
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 12 },
  label: { fontSize: 11, fontWeight: "700", color: theme.colors.primary, letterSpacing: 1.5, fontFamily: theme.fonts.bold },
  emoji: { fontSize: 24 },
  what: { fontSize: 22, fontWeight: "bold", color: theme.colors.text, marginBottom: 16, lineHeight: 28, fontFamily: theme.fonts.bold },
  details: { gap: 10, marginBottom: 16 },
  detailRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  detailIcon: { fontSize: 16 },
  detailText: { fontSize: 15, color: theme.colors.textSecondary, flex: 1, fontFamily: theme.fonts.regular },
  whyToggle: { paddingVertical: 8 },
  whyToggleText: { fontSize: 14, color: theme.colors.primary, fontWeight: "600", fontFamily: theme.fonts.semibold },
  whyBox: { backgroundColor: theme.colors.bgCardLight, borderRadius: 10, padding: 14, marginBottom: 16 },
  whyText: { fontSize: 14, color: theme.colors.textSecondary, lineHeight: 20, fontFamily: theme.fonts.regular },
  influencedBy: { fontSize: 12, color: theme.colors.textMuted, marginTop: 8, fontStyle: "italic", fontFamily: theme.fonts.regular },
  actions: { flexDirection: "row", gap: 8 },
  emptyCard: {
    alignItems: "center",
    paddingVertical: 32,
    paddingHorizontal: 20,
    backgroundColor: theme.colors.bgCard,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: theme.colors.borderLight,
    borderStyle: "dashed",
  },
  emptyIcon: { fontSize: 40, marginBottom: 12 },
  emptyTitle: { fontSize: 18, fontWeight: "600", color: theme.colors.text, marginBottom: 8, fontFamily: theme.fonts.semibold },
  emptyHint: { fontSize: 14, color: theme.colors.textSecondary, textAlign: "center", fontFamily: theme.fonts.regular },
  errorText: { fontSize: 12, color: theme.colors.warm, marginTop: 12, textAlign: "center", fontFamily: theme.fonts.regular },
});
