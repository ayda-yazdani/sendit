import { useEffect, useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  Share,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { useLocalSearchParams, router } from "expo-router";
import * as Clipboard from "expo-clipboard";
import FontAwesome from "@expo/vector-icons/FontAwesome";
import { useBoardStore } from "@/lib/stores/board-store";
import { useAuthStore } from "@/lib/stores/auth-store";
import { useRealtime } from "@/lib/hooks/use-realtime";
import { UrlInput } from "@/components/board/UrlInput";
import { BlobGraphView } from "@/components/board/BlobGraphView";
import { useTasteStore } from "@/lib/stores/taste-store";
import { theme } from "@/constants/Theme";
import { listBoardReels } from "@/lib/api/boards";

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
  const { session } = useAuthStore();
  const [reels, setReels] = useState<Reel[]>([]);
  const [currentMemberId, setCurrentMemberId] = useState<string | null>(null);
  const { fetchProfile } = useTasteStore();

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

      const members = useBoardStore.getState().activeBoardMembers;
      const currentMember = members.find((member) => member.device_id === session?.user.id);
      if (session && currentMember) {
        setCurrentMemberId(currentMember.id);
        const reelData = await listBoardReels(session, id, currentMember.id);
        setReels(reelData);
      }

      await fetchProfile(id);
    };
    load();
  }, [id, session, fetchBoardMembers, fetchProfile]);

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

  // Real-time member updates
  useRealtime({
    table: "members",
    filter: `board_id=eq.${id}`,
    onInsert: () => fetchBoardMembers(id!),
    onDelete: () => fetchBoardMembers(id!),
  });

  const handleShareInvite = async () => {
    if (!activeBoard) return;
    await Share.share({
      message: `Join "${activeBoard.name}" on Sendit! Code: ${activeBoard.join_code}`,
    });
  };

  const handleCopyCode = async () => {
    if (!activeBoard) return;
    await Clipboard.setStringAsync(activeBoard.join_code);
    // Visual feedback handled by UI
  };

  const handleBlobPress = useCallback((category: string, _categoryReels: Reel[]) => {
    router.push({
      pathname: "/flashcards/[category]",
      params: { category, boardId: id },
    });
  }, [id]);

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      {/* Header */}
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} style={styles.backButton}>
          <FontAwesome name="chevron-left" size={16} color={theme.colors.text} />
        </Pressable>

        <View style={styles.headerCenter}>
          <Text style={styles.boardName} numberOfLines={1}>
            {activeBoard?.name ?? "Board"}
          </Text>
          <Text style={styles.memberCount}>
            {activeBoardMembers.length} member{activeBoardMembers.length !== 1 ? "s" : ""}
            {" \u00B7 "}
            {reels.length} reel{reels.length !== 1 ? "s" : ""}
          </Text>
        </View>

        <View style={styles.headerActions}>
          <Pressable onPress={handleCopyCode} style={styles.headerIconButton}>
            <FontAwesome name="link" size={15} color={theme.colors.text} />
          </Pressable>
          <Pressable onPress={handleShareInvite} style={styles.headerIconButton}>
            <FontAwesome name="user-plus" size={14} color={theme.colors.text} />
          </Pressable>
        </View>
      </View>

      {/* Blob Graph View */}
      <BlobGraphView reels={reels} onBlobPress={handleBlobPress} />

      {/* URL Input — glowing, pinned to bottom */}
      {id && currentMemberId && (
        <View style={styles.urlInputContainer}>
          <UrlInput
            boardId={id}
            memberId={currentMemberId}
            onReelAdded={(reel) => setReels((prev) => [reel, ...prev])}
          />
        </View>
      )}
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#000",
  },

  // Header
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingTop: 56,
    paddingBottom: 8,
    backgroundColor: "#000",
  },
  backButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "rgba(255,255,255,0.08)",
    alignItems: "center",
    justifyContent: "center",
  },
  headerCenter: {
    flex: 1,
    marginHorizontal: 12,
  },
  boardName: {
    fontSize: 18,
    fontFamily: theme.fonts.bold,
    color: theme.colors.text,
  },
  memberCount: {
    fontSize: 12,
    fontFamily: theme.fonts.regular,
    color: "#888",
    marginTop: 2,
  },
  headerActions: {
    flexDirection: "row",
    gap: 8,
  },
  headerIconButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "rgba(255,255,255,0.08)",
    alignItems: "center",
    justifyContent: "center",
  },

  // URL Input container
  urlInputContainer: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
  },
});
