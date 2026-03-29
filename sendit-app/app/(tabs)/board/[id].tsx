import { useEffect, useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  Share,
  KeyboardAvoidingView,
  Platform,
  LayoutChangeEvent,
  Modal,
} from "react-native";
import { useLocalSearchParams, router } from "expo-router";
import { useFocusEffect } from "@react-navigation/native";
import FontAwesome from "@expo/vector-icons/FontAwesome";
import { useBoardStore } from "@/lib/stores/board-store";
import { useAuthStore } from "@/lib/stores/auth-store";
import { useRealtime } from "@/lib/hooks/use-realtime";
import { UrlInput } from "@/components/board/UrlInput";
import { JoinCodeDisplay } from "@/components/board/JoinCodeDisplay";
import { BlobGraphView } from "@/components/board/BlobGraphView";
import { useTasteStore } from "@/lib/stores/taste-store";
import { theme } from "@/constants/Theme";
import { listBoardReels } from "@/lib/api/boards";
import { loadReactedReelIds } from "@/lib/utils/reel-reactions";

interface Reel {
  id: string;
  url: string;
  platform: string;
  extraction_data: any;
  classification: string | null;
  created_at: string;
}

export default function BoardDetailScreen() {
  const { id: rawId } = useLocalSearchParams<{ id?: string | string[] }>();
  const id = Array.isArray(rawId) ? rawId[0] : rawId;
  const { activeBoard, activeBoardMembers, fetchBoardMembers, setActiveBoard } = useBoardStore();
  const { session } = useAuthStore();
  const [reels, setReels] = useState<Reel[]>([]);
  const [currentMemberId, setCurrentMemberId] = useState<string | null>(null);
  const [graphSize, setGraphSize] = useState<{ width: number; height: number } | null>(null);
  const [reactedReelIds, setReactedReelIds] = useState<Set<string> | null>(null);
  const [showInvite, setShowInvite] = useState(false);
  const { fetchProfile } = useTasteStore();

  const refreshReactedReels = useCallback(async () => {
    if (!id) return;
    const reelIds = await loadReactedReelIds(id);
    setReactedReelIds(reelIds);
  }, [id]);

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

  useEffect(() => {
    void refreshReactedReels();
  }, [refreshReactedReels]);

  useFocusEffect(
    useCallback(() => {
      void refreshReactedReels();
    }, [refreshReactedReels])
  );

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

  const handleShowInvite = () => {
    if (!activeBoard) return;
    setShowInvite(true);
  };

  const handleBlobPress = useCallback((category: string, _categoryReels: Reel[]) => {
    router.push({
      pathname: "/flashcards/[category]",
      params: { category, boardId: id },
    });
  }, [id]);

  const handleGraphLayout = (event: LayoutChangeEvent) => {
    const { width, height } = event.nativeEvent.layout;
    if (!graphSize || graphSize.width !== width || graphSize.height !== height) {
      setGraphSize({ width, height });
    }
  };

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
          <Pressable onPress={handleShareInvite} style={styles.headerIconButton}>
            <FontAwesome name="link" size={15} color={theme.colors.text} />
          </Pressable>
          <Pressable onPress={handleShowInvite} style={styles.headerIconButton}>
            <FontAwesome name="user-plus" size={14} color={theme.colors.text} />
          </Pressable>
        </View>
      </View>

      {/* Blob Graph View */}
      <View style={styles.blobContainer} onLayout={handleGraphLayout}>
        <BlobGraphView
          reels={reels}
          onBlobPress={handleBlobPress}
          width={graphSize?.width}
          height={graphSize?.height}
          reactedReelIds={reactedReelIds}
        />
      </View>

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

      <Modal visible={showInvite} animationType="slide" transparent>
        <View style={styles.overlay}>
          <View style={styles.sheet}>
            {activeBoard && (
              <JoinCodeDisplay
                board={activeBoard}
                onDone={() => setShowInvite(false)}
                variant="invite"
              />
            )}
          </View>
        </View>
      </Modal>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.bgDark,
  },

  // Header
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingTop: 56,
    paddingBottom: 8,
    backgroundColor: theme.colors.bgDark,
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
    color: theme.colors.textMuted,
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

  // Blob graph fills remaining space
  blobContainer: {
    flex: 1,
  },

  // URL Input container
  urlInputContainer: {
  },

  overlay: {
    flex: 1,
    justifyContent: "flex-end",
    backgroundColor: "rgba(0,0,0,0.7)",
  },
  sheet: {
    backgroundColor: theme.colors.bg,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 24,
    paddingBottom: 40,
  },
});
