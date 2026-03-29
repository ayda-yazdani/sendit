import { useEffect, useState } from "react";
import { View, Text, StyleSheet, ScrollView, ActivityIndicator } from "react-native";
import { useLocalSearchParams } from "expo-router";
import { supabase } from "@/lib/supabase";
import { useAuthStore } from "@/lib/stores/auth-store";
import { useBoardStore } from "@/lib/stores/board-store";
import { useRealtime } from "@/lib/hooks/use-realtime";
import { Suggestion } from "@/lib/ai/suggestion-engine";
import { SuggestionCard } from "@/components/suggestion/SuggestionCard";
import { VoteButtons } from "@/components/commitment/VoteButtons";
import { CommitmentTally } from "@/components/commitment/CommitmentTally";
import { ReceiptWall } from "@/components/commitment/ReceiptWall";
import { theme } from "@/constants/Theme";

type VoteStatus = "in" | "maybe" | "out";

interface Commitment {
  id: string;
  suggestion_id: string;
  member_id: string;
  status: VoteStatus;
  receipt_url: string | null;
}

export default function SuggestionScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { session } = useAuthStore();
  const { activeBoardMembers } = useBoardStore();

  const [suggestion, setSuggestion] = useState<Suggestion | null>(null);
  const [commitments, setCommitments] = useState<Commitment[]>([]);
  const [currentMemberId, setCurrentMemberId] = useState<string | null>(null);
  const [myVote, setMyVote] = useState<VoteStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Load suggestion + commitments + find current member
  useEffect(() => {
    if (!id) return;
    const load = async () => {
      // Fetch suggestion
      const { data: sug } = await supabase
        .from("suggestions")
        .select("*")
        .eq("id", id)
        .single();
      if (sug) setSuggestion(sug as Suggestion);

      // Fetch commitments
      const { data: comms } = await supabase
        .from("commitments")
        .select("*")
        .eq("suggestion_id", id);
      if (comms) setCommitments(comms);

      // Find current member ID
      if (sug && session?.user.id) {
        const { data: member } = await supabase
          .from("members")
          .select("id")
          .eq("board_id", sug.board_id)
          .eq("user_id", session.user.id)
          .single();
        if (member) {
          setCurrentMemberId(member.id);
          const myComm = comms?.find((c: Commitment) => c.member_id === member.id);
          if (myComm) setMyVote(myComm.status);
        }
      }

      // Fetch board members if not already loaded
      if (sug && activeBoardMembers.length === 0) {
        useBoardStore.getState().fetchBoardMembers(sug.board_id);
      }

      setIsLoading(false);
    };
    load();
  }, [id, session]);

  // Real-time commitment updates
  useRealtime({
    table: "commitments",
    filter: `suggestion_id=eq.${id}`,
    onChange: async () => {
      const { data } = await supabase
        .from("commitments")
        .select("*")
        .eq("suggestion_id", id);
      if (data) {
        setCommitments(data);
        if (currentMemberId) {
          const mine = data.find((c: Commitment) => c.member_id === currentMemberId);
          if (mine) setMyVote(mine.status);
        }
      }
    },
  });

  const handleVoted = (status: VoteStatus) => {
    setMyVote(status);
    // Update local commitments optimistically
    setCommitments(prev => {
      const existing = prev.findIndex(c => c.member_id === currentMemberId);
      if (existing >= 0) {
        const updated = [...prev];
        updated[existing] = { ...updated[existing], status };
        return updated;
      }
      return [...prev, {
        id: "temp",
        suggestion_id: id!,
        member_id: currentMemberId!,
        status,
        receipt_url: null,
      }];
    });
  };

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={theme.colors.primary} />
      </View>
    );
  }

  if (!suggestion) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.errorText}>Suggestion not found</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Plan</Text>
      </View>

      {/* Suggestion Card */}
      <View style={styles.section}>
        <SuggestionCard
          suggestion={suggestion}
          boardId={suggestion.board_id}
          onNewSuggestion={(s) => setSuggestion(s)}
        />
      </View>

      {/* Vote Buttons */}
      {currentMemberId && (
        <View style={styles.section}>
          <VoteButtons
            suggestionId={suggestion.id}
            memberId={currentMemberId}
            currentVote={myVote}
            onVoted={handleVoted}
          />
        </View>
      )}

      {/* Commitment Tally */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Who's coming?</Text>
        <CommitmentTally
          commitments={commitments}
          members={activeBoardMembers}
        />
      </View>

      {/* Receipt Wall */}
      <View style={styles.section}>
        <ReceiptWall
          commitments={commitments}
          members={activeBoardMembers}
          currentMemberId={currentMemberId}
          suggestionId={id!}
        />
      </View>

      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.bg },
  loadingContainer: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: theme.colors.bg },
  errorText: { fontSize: 16, color: theme.colors.textSecondary },
  header: { padding: 20, paddingTop: 60 },
  headerTitle: { fontSize: 28, fontWeight: "bold", color: theme.colors.text },
  section: { paddingHorizontal: 20, marginBottom: 20 },
  sectionTitle: { fontSize: 16, fontWeight: "700", color: theme.colors.text, marginBottom: 12 },
});
