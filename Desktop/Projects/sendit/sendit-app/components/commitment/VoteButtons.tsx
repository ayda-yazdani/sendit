import { View, Text, StyleSheet, Pressable, ActivityIndicator } from "react-native";
import { useState } from "react";
import { supabase } from "@/lib/supabase";

type VoteStatus = "in" | "maybe" | "out";

interface VoteButtonsProps {
  suggestionId: string;
  memberId: string;
  currentVote: VoteStatus | null;
  onVoted: (status: VoteStatus) => void;
}

export function VoteButtons({ suggestionId, memberId, currentVote, onVoted }: VoteButtonsProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleVote = async (status: VoteStatus) => {
    if (isSubmitting) return;
    setIsSubmitting(true);

    // Optimistic update
    onVoted(status);

    const { error } = await supabase
      .from("commitments")
      .upsert(
        {
          suggestion_id: suggestionId,
          member_id: memberId,
          status,
          updated_at: new Date().toISOString(),
        },
        { onConflict: "suggestion_id,member_id" }
      );

    if (error) {
      console.error("Vote failed:", error);
      // Revert optimistic update
      if (currentVote) onVoted(currentVote);
    }

    setIsSubmitting(false);
  };

  return (
    <View style={styles.container}>
      <Text style={styles.label}>Are you in?</Text>
      <View style={styles.buttons}>
        <Pressable
          style={[styles.button, styles.inButton, currentVote === "in" && styles.inActive]}
          onPress={() => handleVote("in")}
          disabled={isSubmitting}
        >
          <Text style={[styles.buttonText, currentVote === "in" && styles.activeText]}>
            {currentVote === "in" ? "✓ I'm In" : "I'm In"}
          </Text>
        </Pressable>

        <Pressable
          style={[styles.button, styles.maybeButton, currentVote === "maybe" && styles.maybeActive]}
          onPress={() => handleVote("maybe")}
          disabled={isSubmitting}
        >
          <Text style={[styles.buttonText, styles.maybeText, currentVote === "maybe" && styles.activeText]}>
            {currentVote === "maybe" ? "✓ Maybe" : "Maybe"}
          </Text>
        </Pressable>

        <Pressable
          style={[styles.button, styles.outButton, currentVote === "out" && styles.outActive]}
          onPress={() => handleVote("out")}
          disabled={isSubmitting}
        >
          <Text style={[styles.buttonText, styles.outText, currentVote === "out" && styles.activeText]}>
            {currentVote === "out" ? "✓ Out" : "Out"}
          </Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginTop: 8 },
  label: { fontSize: 14, fontWeight: "600", color: "#333", marginBottom: 10 },
  buttons: { flexDirection: "row", gap: 8 },
  button: { flex: 1, paddingVertical: 14, borderRadius: 12, alignItems: "center", borderWidth: 2 },
  buttonText: { fontSize: 15, fontWeight: "600" },
  activeText: { color: "#fff" },

  inButton: { borderColor: "#1a9e76", backgroundColor: "transparent" },
  inActive: { backgroundColor: "#1a9e76", borderColor: "#1a9e76" },

  maybeButton: { borderColor: "#c49a2e", backgroundColor: "transparent" },
  maybeText: { color: "#c49a2e" },
  maybeActive: { backgroundColor: "#c49a2e", borderColor: "#c49a2e" },

  outButton: { borderColor: "#999", backgroundColor: "transparent" },
  outText: { color: "#999" },
  outActive: { backgroundColor: "#999", borderColor: "#999" },
});
