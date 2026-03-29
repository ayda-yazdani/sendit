import { useState, useEffect, useRef } from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  Pressable,
  Modal,
  RefreshControl,
  Image,
  KeyboardAvoidingView,
  Platform,
  Animated,
  PanResponder,
} from "react-native";
import { router } from "expo-router";
import { useAuthStore } from "@/lib/stores/auth-store";
import { useBoardStore, Board } from "@/lib/stores/board-store";
import { CreateBoardModal } from "@/components/board/CreateBoardModal";
import { JoinCodeDisplay } from "@/components/board/JoinCodeDisplay";
import { Input } from "@/components/shared/Input";
import { theme } from "@/constants/Theme";
import FontAwesome from "@expo/vector-icons/FontAwesome";

// Default cover images — random selection for boards without custom covers
const DEFAULT_COVERS = [
  "https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?w=600&h=300&fit=crop",
  "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=600&h=300&fit=crop",
  "https://images.unsplash.com/photo-1543007630-9710e4a00a20?w=600&h=300&fit=crop",
  "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=600&h=300&fit=crop",
  "https://images.unsplash.com/photo-1429962714451-bb934ecdc4ec?w=600&h=300&fit=crop",
  "https://images.unsplash.com/photo-1506157786151-b8491531f063?w=600&h=300&fit=crop",
];

function getCoverForBoard(boardId: string): string {
  let hash = 0;
  for (let i = 0; i < boardId.length; i++) hash = boardId.charCodeAt(i) + ((hash << 5) - hash);
  return DEFAULT_COVERS[Math.abs(hash) % DEFAULT_COVERS.length];
}

function BoardCard({
  board,
  onPress,
  onManage,
}: {
  board: Board;
  onPress: () => void;
  onManage: () => void;
}) {
  return (
    <View style={styles.cardWrapper}>
      <Pressable
        style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
        onPress={onPress}
      >
        <Image
          source={{ uri: getCoverForBoard(board.id) }}
          style={styles.cardImage}
          resizeMode="cover"
        />
        <View style={styles.cardContent}>
          <Text style={styles.cardTitle} numberOfLines={2}>
            {board.name}
          </Text>
          <View style={styles.cardMeta}>
            <Text style={styles.cardCode}>
              <FontAwesome name="key" size={11} color={theme.colors.textMuted} />
              {"  "}{board.join_code}
            </Text>
          </View>
        </View>
      </Pressable>
      <Pressable style={styles.cardAction} onPress={onManage}>
        <FontAwesome name="ellipsis-h" size={16} color={theme.colors.text} />
      </Pressable>
    </View>
  );
}

export default function BoardListScreen() {
  const { session } = useAuthStore();
  const { boards, isLoading, fetchBoards, renameBoard, removeBoard } = useBoardStore();
  const [showCreate, setShowCreate] = useState(false);
  const [showJoin, setShowJoin] = useState(false);
  const [createdBoard, setCreatedBoard] = useState<Board | null>(null);
  const [joinCode, setJoinCode] = useState("");
  const [joinName, setJoinName] = useState("");
  const [isJoining, setIsJoining] = useState(false);
  const [manageBoard, setManageBoard] = useState<Board | null>(null);
  const [showManage, setShowManage] = useState(false);
  const [showRename, setShowRename] = useState(false);
  const [showDelete, setShowDelete] = useState(false);
  const [renameValue, setRenameValue] = useState("");
  const [isRenaming, setIsRenaming] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const joinSheetTranslateY = useRef(new Animated.Value(0)).current;

  const closeJoin = () => {
    setShowJoin(false);
    setJoinCode("");
    setJoinName("");
    joinSheetTranslateY.setValue(0);
  };

  const joinPanResponder = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponder: (_, gesture) =>
        Math.abs(gesture.dy) > 6 && Math.abs(gesture.dy) > Math.abs(gesture.dx),
      onPanResponderMove: (_, gesture) => {
        if (gesture.dy > 0) {
          joinSheetTranslateY.setValue(gesture.dy);
        }
      },
      onPanResponderRelease: (_, gesture) => {
        if (gesture.dy > 120 || gesture.vy > 0.9) {
          Animated.timing(joinSheetTranslateY, {
            toValue: 420,
            duration: 200,
            useNativeDriver: true,
          }).start(() => closeJoin());
        } else {
          Animated.spring(joinSheetTranslateY, {
            toValue: 0,
            useNativeDriver: true,
            damping: 20,
            stiffness: 220,
          }).start();
        }
      },
    })
  ).current;

  useEffect(() => { if (session) fetchBoards(); }, [session]);

  const handleBoardCreated = (board: Board) => {
    setShowCreate(false);
    setCreatedBoard(board);
  };

  const handleDone = () => {
    if (createdBoard) router.push(`/board/${createdBoard.id}`);
    setCreatedBoard(null);
  };

  const handleJoin = async () => {
    if (!joinCode.trim()) return;
    setIsJoining(true);
    try {
      const board = await useBoardStore.getState().joinBoard(joinCode, joinName);
      closeJoin();
      router.push(`/board/${board.id}`);
    } catch {} finally {
      setIsJoining(false);
    }
  };

  const openManage = (board: Board) => {
    setManageBoard(board);
    setRenameValue(board.name);
    setShowManage(true);
  };

  const handleRename = async () => {
    if (!manageBoard) return;
    const nextName = renameValue.trim();
    if (!nextName) return;
    setIsRenaming(true);
    try {
      await renameBoard(manageBoard.id, nextName);
      setShowRename(false);
      setShowManage(false);
    } catch {} finally {
      setIsRenaming(false);
    }
  };

  const handleDelete = async () => {
    if (!manageBoard) return;
    setIsDeleting(true);
    try {
      await removeBoard(manageBoard.id);
      setShowDelete(false);
      setShowManage(false);
      setManageBoard(null);
    } catch {} finally {
      setIsDeleting(false);
    }
  };

  const navigateToBoard = (board: Board) => {
    useBoardStore.getState().setActiveBoard(board);
    router.push(`/board/${board.id}`);
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.logo}>sendit</Text>
        <View style={styles.headerActions}>
          <Pressable
            style={styles.headerButton}
            onPress={() => setShowJoin(true)}
          >
            <FontAwesome name="sign-in" size={18} color={theme.colors.text} />
          </Pressable>
          <Pressable
            style={styles.addButton}
            onPress={() => setShowCreate(true)}
          >
            <FontAwesome name="plus" size={16} color={theme.colors.text} />
          </Pressable>
        </View>
      </View>

      {/* Board List */}
      {boards.length === 0 ? (
        <View style={styles.emptyState}>
          <View style={styles.emptyIconContainer}>
            <FontAwesome name="users" size={32} color={theme.colors.textMuted} />
          </View>
          <Text style={styles.emptyText}>No boards yet</Text>
          <Text style={styles.emptyHint}>
            Create a board and share the code{"\n"}with your friends
          </Text>
          <Pressable
            style={styles.emptyCreateButton}
            onPress={() => setShowCreate(true)}
          >
            <Text style={styles.emptyCreateText}>Create Your First Board</Text>
          </Pressable>
        </View>
      ) : (
        <FlatList
          data={boards}
          keyExtractor={(item) => item.id}
          style={styles.list}
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl
              refreshing={isLoading}
              onRefresh={fetchBoards}
              tintColor={theme.colors.warm}
            />
          }
          renderItem={({ item }) => (
            <BoardCard
              board={item}
              onPress={() => navigateToBoard(item)}
              onManage={() => openManage(item)}
            />
          )}
        />
      )}

      {/* Create Board Modal */}
      <CreateBoardModal
        visible={showCreate}
        onClose={() => setShowCreate(false)}
        onCreated={handleBoardCreated}
      />

      {/* Join Code Display (after creation) */}
      <Modal visible={!!createdBoard} animationType="slide" transparent>
        <View style={styles.overlay}>
          <View style={styles.sheet}>
            {createdBoard && (
              <JoinCodeDisplay board={createdBoard} onDone={handleDone} />
            )}
          </View>
        </View>
      </Modal>

      {/* Join Board Modal */}
      <Modal visible={showJoin} animationType="slide" transparent onRequestClose={closeJoin}>
        <KeyboardAvoidingView
          style={styles.overlay}
          behavior={Platform.OS === "ios" ? "padding" : "height"}
        >
          <Pressable
            style={StyleSheet.absoluteFill}
            onPress={closeJoin}
          />
          <Animated.View
            style={[styles.sheet, { transform: [{ translateY: joinSheetTranslateY }] }]}
            {...joinPanResponder.panHandlers}
          >
            <View style={styles.handle} />
            <Text style={styles.sheetTitle}>Join Board</Text>
            <Input
              label="Join Code"
              value={joinCode}
              onChangeText={(t) => setJoinCode(t.toUpperCase())}
              placeholder="e.g. ABC123"
              maxLength={6}
              autoFocus
            />
            <Input
              label="Your Display Name"
              value={joinName}
              onChangeText={setJoinName}
              placeholder="e.g. Tom (optional)"
              maxLength={30}
            />
            <Pressable
              style={[
                styles.joinButton,
                joinCode.trim().length < 3 && styles.joinButtonDisabled,
              ]}
              onPress={handleJoin}
              disabled={joinCode.trim().length < 3 || isJoining}
            >
              <Text style={styles.joinButtonText}>
                {isJoining ? "Joining..." : "Join Board"}
              </Text>
            </Pressable>
            <Pressable
              onPress={closeJoin}
              style={styles.cancelButton}
            >
              <Text style={styles.cancelText}>Cancel</Text>
            </Pressable>
          </Animated.View>
        </KeyboardAvoidingView>
      </Modal>

      {/* Manage Board Modal */}
      <Modal visible={showManage} animationType="slide" transparent>
        <View style={styles.overlay}>
          <View style={styles.sheet}>
            <View style={styles.handle} />
            <Text style={styles.sheetTitle}>Manage Board</Text>
            <Pressable
              style={styles.manageButton}
              onPress={() => { setShowManage(false); setShowRename(true); }}
            >
              <Text style={styles.manageText}>Rename Board</Text>
            </Pressable>
            <Pressable
              style={styles.manageButton}
              onPress={() => { setShowManage(false); setShowDelete(true); }}
            >
              <Text style={[styles.manageText, styles.manageDangerText]}>Delete Board</Text>
            </Pressable>
            <Pressable onPress={() => setShowManage(false)} style={styles.cancelButton}>
              <Text style={styles.cancelText}>Cancel</Text>
            </Pressable>
          </View>
        </View>
      </Modal>

      {/* Rename Board Modal */}
      <Modal visible={showRename} animationType="slide" transparent>
        <View style={styles.overlay}>
          <View style={styles.sheet}>
            <View style={styles.handle} />
            <Text style={styles.sheetTitle}>Rename Board</Text>
            <Input
              label="Board Name"
              value={renameValue}
              onChangeText={setRenameValue}
              placeholder="e.g. Weekend Crew"
              maxLength={40}
              autoFocus
            />
            <Pressable
              style={[
                styles.joinButton,
                (!renameValue.trim() || isRenaming) && styles.joinButtonDisabled,
              ]}
              onPress={handleRename}
              disabled={!renameValue.trim() || isRenaming}
            >
              <Text style={styles.joinButtonText}>
                {isRenaming ? "Saving..." : "Save Name"}
              </Text>
            </Pressable>
            <Pressable onPress={() => setShowRename(false)} style={styles.cancelButton}>
              <Text style={styles.cancelText}>Cancel</Text>
            </Pressable>
          </View>
        </View>
      </Modal>

      {/* Delete Board Modal */}
      <Modal visible={showDelete} animationType="slide" transparent>
        <View style={styles.overlay}>
          <View style={styles.sheet}>
            <View style={styles.handle} />
            <Text style={styles.sheetTitle}>Delete Board?</Text>
            <Text style={styles.deleteHint}>
              This removes the board and all its reels for everyone.
            </Text>
            <Pressable
              style={[styles.deleteButton, isDeleting && styles.joinButtonDisabled]}
              onPress={handleDelete}
              disabled={isDeleting}
            >
              <Text style={styles.deleteButtonText}>
                {isDeleting ? "Deleting..." : "Delete Board"}
              </Text>
            </Pressable>
            <Pressable onPress={() => setShowDelete(false)} style={styles.cancelButton}>
              <Text style={styles.cancelText}>Cancel</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    </View>
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
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingTop: 60,
    paddingBottom: 12,
    backgroundColor: "#000",
  },
  logo: {
    fontFamily: theme.fonts.display,
    fontSize: 32,
    color: theme.colors.text,
    textShadowColor: "rgba(152, 38, 73, 0.5)",
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 12,
  },
  headerActions: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  headerButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "rgba(255,255,255,0.08)",
    alignItems: "center",
    justifyContent: "center",
  },
  addButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: theme.colors.primary,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: theme.colors.primary,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.5,
    shadowRadius: 8,
    elevation: 6,
  },

  // Card (news-tab style)
  cardWrapper: {
    marginHorizontal: 16,
    marginBottom: 16,
    position: "relative",
  },
  card: {
    backgroundColor: "#1a1a1a",
    borderRadius: 16,
    overflow: "hidden",
  },
  cardPressed: {
    opacity: 0.85,
    transform: [{ scale: 0.98 }],
  },
  cardAction: {
    position: "absolute",
    top: 10,
    right: 10,
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "rgba(0,0,0,0.45)",
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.14)",
  },
  cardImage: {
    width: "100%",
    height: 120,
    backgroundColor: "#2a2a2a",
  },
  cardContent: {
    padding: 16,
  },
  cardTitle: {
    color: "#ffffff",
    fontSize: 18,
    fontFamily: theme.fonts.bold,
    lineHeight: 24,
    marginBottom: 8,
  },
  cardMeta: {
    flexDirection: "row",
    alignItems: "center",
    gap: 16,
  },
  cardCode: {
    color: "#888",
    fontSize: 13,
    fontFamily: theme.fonts.regular,
  },

  // Empty state
  emptyState: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 40,
  },
  emptyIconContainer: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: "rgba(255,255,255,0.05)",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 20,
  },
  emptyText: {
    fontSize: 20,
    fontFamily: theme.fonts.semibold,
    color: theme.colors.text,
    marginBottom: 8,
  },
  emptyHint: {
    fontSize: 14,
    fontFamily: theme.fonts.regular,
    color: "#888",
    textAlign: "center",
    lineHeight: 20,
    marginBottom: 28,
  },
  emptyCreateButton: {
    backgroundColor: theme.colors.primary,
    paddingHorizontal: 28,
    paddingVertical: 14,
    borderRadius: theme.borderRadius.md,
    shadowColor: theme.colors.primary,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.5,
    shadowRadius: 10,
    elevation: 6,
  },
  emptyCreateText: {
    color: theme.colors.text,
    fontFamily: theme.fonts.bold,
    fontSize: 15,
  },

  // List
  list: {
    flex: 1,
  },
  listContent: {
    paddingTop: 8,
    paddingBottom: 20,
  },

  // Bottom sheet modals
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
  handle: {
    width: 36,
    height: 4,
    backgroundColor: "rgba(255,255,255,0.15)",
    borderRadius: 2,
    alignSelf: "center",
    marginBottom: 20,
  },
  sheetTitle: {
    fontSize: 22,
    fontFamily: theme.fonts.bold,
    color: theme.colors.text,
    marginBottom: 20,
  },
  joinButton: {
    backgroundColor: theme.colors.primary,
    paddingVertical: 16,
    borderRadius: theme.borderRadius.md,
    alignItems: "center",
    marginTop: 8,
    shadowColor: theme.colors.primary,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.4,
    shadowRadius: 8,
  },
  joinButtonDisabled: {
    opacity: 0.4,
  },
  joinButtonText: {
    color: theme.colors.text,
    fontFamily: theme.fonts.bold,
    fontSize: 16,
  },
  manageButton: {
    backgroundColor: "rgba(255,255,255,0.05)",
    borderRadius: theme.borderRadius.md,
    borderWidth: 1,
    borderColor: theme.colors.borderLight,
    paddingVertical: 14,
    paddingHorizontal: 16,
    marginBottom: 12,
  },
  manageText: {
    fontSize: 15,
    fontFamily: theme.fonts.semibold,
    color: theme.colors.text,
  },
  manageDangerText: {
    color: theme.colors.error,
  },
  deleteHint: {
    fontSize: 13,
    color: theme.colors.textSecondary,
    fontFamily: theme.fonts.regular,
    marginBottom: 16,
  },
  deleteButton: {
    backgroundColor: theme.colors.error,
    paddingVertical: 16,
    borderRadius: theme.borderRadius.md,
    alignItems: "center",
    marginTop: 4,
    shadowColor: theme.colors.error,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.4,
    shadowRadius: 8,
  },
  deleteButtonText: {
    color: theme.colors.text,
    fontFamily: theme.fonts.bold,
    fontSize: 16,
  },
  cancelButton: {
    alignItems: "center",
    marginTop: 12,
    padding: 8,
  },
  cancelText: {
    fontSize: 15,
    color: "#888",
    fontFamily: theme.fonts.regular,
  },
});
