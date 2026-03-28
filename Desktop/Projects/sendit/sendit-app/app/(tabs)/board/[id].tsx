import { useEffect, useState } from "react";
import { View, Text, StyleSheet, ScrollView, ActivityIndicator, Pressable, Share, KeyboardAvoidingView, Platform } from "react-native";
import { useLocalSearchParams } from "expo-router";
import * as Clipboard from "expo-clipboard";
import { useBoardStore } from "@/lib/stores/board-store";
import { useAuthStore } from "@/lib/stores/auth-store";
import { useRealtime } from "@/lib/hooks/use-realtime";
import { MemberList } from "@/components/board/MemberList";
import { UrlInput } from "@/components/board/UrlInput";
import { supabase } from "@/lib/supabase";
import { ExtractionCard } from "@/components/extraction/ExtractionCard";
import { SuggestionCard, SuggestionEmpty } from "@/components/suggestion/SuggestionCard";
import { getActiveSuggestion, Suggestion } from "@/lib/ai/suggestion-engine";
import { TasteProfileSection } from "@/components/board/TasteProfile";
import { IdentityCard } from "@/components/board/IdentityCard";
import { useTasteStore } from "@/lib/stores/taste-store";

interface Reel {
  id: string;
  url: string;
  platform: string;
  extraction_data: any;
  classification: string | null;
  created_at: string;
}

export default function BoardDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { activeBoard, activeBoardMembers, fetchBoardMembers, setActiveBoard } = useBoardStore();
  const { deviceId } = useAuthStore();
  const [isLoading, setIsLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [reels, setReels] = useState<Reel[]>([]);
  const [currentMemberId, setCurrentMemberId] = useState<string | null>(null);
  const [suggestion, setSuggestion] = useState<Suggestion | null>(null);
  const { profile: tasteProfile, isLoading: tasteLoading, fetchProfile, regenerateProfile } = useTasteStore();

  // Load board if navigated directly
  useEffect(() => {
    if (!activeBoard && id) {
      const board = useBoardStore.getState().boards.find((b) => b.id === id);
      if (board) setActiveBoard(board);
    }
  }, [id, activeBoard]);

  // Fetch members + reels + find current member
  useEffect(() => {
    if (!id) return;
    const load = async () => {
      await fetchBoardMembers(id);

      // Find current user's member ID
      if (deviceId) {
        const { data: member } = await supabase
          .from("members")
          .select("id")
          .eq("board_id", id)
          .eq("device_id", deviceId)
          .single();
        if (member) setCurrentMemberId(member.id);
      }

      // Fetch reels
      const { data: reelData } = await supabase
        .from("reels")
        .select("*")
        .eq("board_id", id)
        .order("created_at", { ascending: false });
      if (reelData) setReels(reelData);

      // Fetch taste profile
      await fetchProfile(id);

      // Fetch active suggestion
      const activeSuggestion = await getActiveSuggestion(id);
      if (activeSuggestion) setSuggestion(activeSuggestion);

      setIsLoading(false);
    };
    load();
  }, [id, deviceId]);

  // Real-time member updates
  useRealtime({
    table: "members",
    filter: `board_id=eq.${id}`,
    onInsert: () => fetchBoardMembers(id!),
    onDelete: () => fetchBoardMembers(id!),
  });

  // Real-time taste profile updates
  useRealtime({
    table: "taste_profiles",
    filter: `board_id=eq.${id}`,
    onChange: () => fetchProfile(id!),
  });

  // Real-time reel updates
  useRealtime({
    table: "reels",
    filter: `board_id=eq.${id}`,
    onInsert: (payload: any) => {
      setReels((prev) => [payload.new, ...prev]);
    },
    onUpdate: (payload: any) => {
      setReels((prev) => prev.map((r) => (r.id === payload.new.id ? payload.new : r)));
    },
  });

  const handleCopyCode = async () => {
    if (!activeBoard) return;
    await Clipboard.setStringAsync(activeBoard.join_code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleShareInvite = async () => {
    if (!activeBoard) return;
    await Share.share({ message: `Join "${activeBoard.name}" on Sendit! Code: ${activeBoard.join_code}` });
  };

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView style={styles.container} keyboardShouldPersistTaps="handled">
        {/* Board Header */}
        <View style={styles.header}>
          <Text style={styles.boardName}>{activeBoard?.name ?? "Board"}</Text>
          <Text style={styles.memberCount}>
            {activeBoardMembers.length} member{activeBoardMembers.length !== 1 ? "s" : ""}
          </Text>
        </View>

        {/* Join Code */}
        {activeBoard && (
          <View style={styles.codeSection}>
            <View style={styles.codeRow}>
              <View>
                <Text style={styles.codeLabel}>Join Code</Text>
                <Text style={styles.codeValue}>{activeBoard.join_code}</Text>
              </View>
              <View style={styles.codeActions}>
                <Pressable style={styles.codeButton} onPress={handleCopyCode}>
                  <Text style={styles.codeButtonText}>{copied ? "Copied!" : "Copy"}</Text>
                </Pressable>
                <Pressable style={styles.codeButton} onPress={handleShareInvite}>
                  <Text style={styles.codeButtonText}>Share</Text>
                </Pressable>
              </View>
            </View>
          </View>
        )}

        {/* Reels */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Reels ({reels.length})</Text>
          {reels.length === 0 ? (
            <View style={styles.placeholder}>
              <Text style={styles.placeholderIcon}>🎬</Text>
              <Text style={styles.placeholderText}>No reels yet</Text>
              <Text style={styles.placeholderHint}>Paste a URL below to share content</Text>
            </View>
          ) : (
            reels.map((reel) => (
              <ExtractionCard
                key={reel.id}
                url={reel.url}
                platform={reel.platform}
                classification={reel.classification}
                extractionData={reel.extraction_data}
                createdAt={reel.created_at}
              />
            ))
          )}
        </View>

        {/* Members */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Members</Text>
          {isLoading ? (
            <ActivityIndicator size="small" color="#d4562a" style={{ paddingVertical: 20 }} />
          ) : (
            <MemberList members={activeBoardMembers} />
          )}
        </View>

        {/* Identity Card */}
        {tasteProfile?.identity_label && tasteProfile?.profile_data && activeBoard && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Group Identity</Text>
            <IdentityCard
              boardName={activeBoard.name}
              identityLabel={tasteProfile.identity_label}
              profileData={tasteProfile.profile_data}
            />
          </View>
        )}

        {/* Suggestion */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Suggestion</Text>
          {suggestion ? (
            <SuggestionCard
              suggestion={suggestion}
              boardId={id!}
              onNewSuggestion={(s) => setSuggestion(s)}
            />
          ) : (
            <SuggestionEmpty
              boardId={id!}
              hasEnoughReels={reels.length >= 3}
              onGenerated={(s) => setSuggestion(s)}
            />
          )}
        </View>

        {/* Taste Profile */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Taste Profile</Text>
          <TasteProfileSection
            profileData={tasteProfile?.profile_data || null}
            identityLabel={tasteProfile?.identity_label || null}
            isLoading={tasteLoading}
            reelCount={reels.length}
            onGenerate={() => regenerateProfile(id!)}
          />
        </View>

        <View style={{ height: 100 }} />
      </ScrollView>

      {/* URL Input pinned to bottom */}
      {id && currentMemberId && (
        <UrlInput boardId={id} memberId={currentMemberId} />
      )}
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  header: { padding: 20, paddingTop: 60 },
  boardName: { fontSize: 28, fontWeight: "bold", color: "#333", marginBottom: 4 },
  memberCount: { fontSize: 14, color: "#999" },
  codeSection: { paddingHorizontal: 20, marginBottom: 16 },
  codeRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", backgroundColor: "#f5f0eb", borderRadius: 12, padding: 16 },
  codeLabel: { fontSize: 11, color: "#999", textTransform: "uppercase", marginBottom: 4 },
  codeValue: { fontSize: 20, fontWeight: "bold", color: "#d4562a", letterSpacing: 3 },
  codeActions: { flexDirection: "row", gap: 8 },
  codeButton: { backgroundColor: "#fff", borderRadius: 8, paddingHorizontal: 14, paddingVertical: 8, borderWidth: 1, borderColor: "#ddd" },
  codeButtonText: { fontSize: 13, fontWeight: "600", color: "#d4562a" },
  section: { paddingHorizontal: 20, marginBottom: 20 },
  sectionTitle: { fontSize: 16, fontWeight: "700", color: "#333", marginBottom: 12 },
  placeholder: { alignItems: "center", paddingVertical: 24, backgroundColor: "#f9f7f5", borderRadius: 12, borderWidth: 1, borderColor: "#eee" },
  placeholderIcon: { fontSize: 32, marginBottom: 8 },
  placeholderText: { fontSize: 14, color: "#999", fontWeight: "500" },
  placeholderHint: { fontSize: 12, color: "#bbb", marginTop: 4 },
});
