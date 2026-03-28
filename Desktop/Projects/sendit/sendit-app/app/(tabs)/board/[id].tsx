import { useEffect, useState } from "react";
import { View, Text, StyleSheet, ScrollView, ActivityIndicator, Pressable, Share } from "react-native";
import { useLocalSearchParams } from "expo-router";
import * as Clipboard from "expo-clipboard";
import { useBoardStore } from "@/lib/stores/board-store";
import { useRealtime } from "@/lib/hooks/use-realtime";
import { MemberList } from "@/components/board/MemberList";

export default function BoardDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { activeBoard, activeBoardMembers, fetchBoardMembers, setActiveBoard } = useBoardStore();
  const [isLoading, setIsLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  // Load board if navigated directly (not from list)
  useEffect(() => {
    if (!activeBoard && id) {
      const board = useBoardStore.getState().boards.find((b) => b.id === id);
      if (board) setActiveBoard(board);
    }
  }, [id, activeBoard]);

  // Fetch members
  useEffect(() => {
    if (id) {
      fetchBoardMembers(id).finally(() => setIsLoading(false));
    }
  }, [id]);

  // Real-time member updates
  useRealtime({
    table: "members",
    filter: `board_id=eq.${id}`,
    onInsert: () => fetchBoardMembers(id!),
    onDelete: () => fetchBoardMembers(id!),
    onUpdate: () => fetchBoardMembers(id!),
  });

  const handleCopyCode = async () => {
    if (!activeBoard) return;
    await Clipboard.setStringAsync(activeBoard.join_code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleShareInvite = async () => {
    if (!activeBoard) return;
    await Share.share({
      message: `Join "${activeBoard.name}" on Sendit! Code: ${activeBoard.join_code}`,
    });
  };

  return (
    <ScrollView style={styles.container}>
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

      {/* Members */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Members</Text>
        {isLoading ? (
          <ActivityIndicator size="small" color="#d4562a" style={{ paddingVertical: 20 }} />
        ) : (
          <MemberList members={activeBoardMembers} />
        )}
      </View>

      {/* Placeholder sections for future epics */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Reels</Text>
        <View style={styles.placeholder}>
          <Text style={styles.placeholderIcon}>🎬</Text>
          <Text style={styles.placeholderText}>Shared reels will appear here</Text>
          <Text style={styles.placeholderHint}>Paste a URL or share from any app</Text>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Taste Profile</Text>
        <View style={styles.placeholder}>
          <Text style={styles.placeholderIcon}>🌡</Text>
          <Text style={styles.placeholderText}>Group taste builds after 3+ reels</Text>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Suggestion</Text>
        <View style={styles.placeholder}>
          <Text style={styles.placeholderIcon}>💡</Text>
          <Text style={styles.placeholderText}>Plan suggestion will appear here</Text>
        </View>
      </View>

      <View style={{ height: 40 }} />
    </ScrollView>
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
