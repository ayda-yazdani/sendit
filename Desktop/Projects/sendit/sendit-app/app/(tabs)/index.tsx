import { useState, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  Pressable,
  Modal,
  RefreshControl,
} from "react-native";
import { router } from "expo-router";
import { useAuthStore } from "@/lib/stores/auth-store";
import { useBoardStore, Board } from "@/lib/stores/board-store";
import { CreateBoardModal } from "@/components/board/CreateBoardModal";
import { JoinCodeDisplay } from "@/components/board/JoinCodeDisplay";
import { Button } from "@/components/shared/Button";
import { Input } from "@/components/shared/Input";

export default function BoardListScreen() {
  const { deviceId, isInitialized } = useAuthStore();
  const { boards, isLoading, fetchBoards } = useBoardStore();

  const [showCreate, setShowCreate] = useState(false);
  const [showJoin, setShowJoin] = useState(false);
  const [createdBoard, setCreatedBoard] = useState<Board | null>(null);
  const [joinCode, setJoinCode] = useState("");
  const [joinName, setJoinName] = useState("");
  const [isJoining, setIsJoining] = useState(false);

  useEffect(() => {
    if (isInitialized) fetchBoards();
  }, [isInitialized]);

  const handleBoardCreated = (board: Board) => {
    setShowCreate(false);
    setCreatedBoard(board);
  };

  const handleDone = () => {
    if (createdBoard) {
      router.push(`/board/${createdBoard.id}`);
    }
    setCreatedBoard(null);
  };

  const handleJoin = async () => {
    if (!joinCode.trim()) return;
    setIsJoining(true);
    try {
      const board = await useBoardStore.getState().joinBoard(joinCode, joinName);
      setShowJoin(false);
      setJoinCode("");
      setJoinName("");
      router.push(`/board/${board.id}`);
    } catch {
      // Error handled in store
    } finally {
      setIsJoining(false);
    }
  };

  if (!isInitialized) {
    return (
      <View style={styles.container}>
        <Text style={styles.loading}>Loading...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>sendit</Text>
      <Text style={styles.subtitle}>
        {boards.length > 0
          ? `${boards.length} board${boards.length !== 1 ? "s" : ""}`
          : "Your boards will appear here"}
      </Text>

      {boards.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyIcon}>📋</Text>
          <Text style={styles.emptyText}>No boards yet</Text>
          <Text style={styles.emptyHint}>
            Create a board and share the code with your friends
          </Text>
        </View>
      ) : (
        <FlatList
          data={boards}
          keyExtractor={(item) => item.id}
          style={styles.list}
          refreshControl={
            <RefreshControl refreshing={isLoading} onRefresh={fetchBoards} />
          }
          renderItem={({ item }) => (
            <Pressable
              style={styles.boardCard}
              onPress={() => {
                useBoardStore.getState().setActiveBoard(item);
                router.push(`/board/${item.id}`);
              }}
            >
              <Text style={styles.boardName}>{item.name}</Text>
              <Text style={styles.boardCode}>Code: {item.join_code}</Text>
            </Pressable>
          )}
        />
      )}

      <View style={styles.buttons}>
        <Button title="Create Board" onPress={() => setShowCreate(true)} />
        <Button
          title="Join with Code"
          onPress={() => setShowJoin(true)}
          variant="secondary"
          style={{ marginTop: 8 }}
        />
      </View>

      <CreateBoardModal
        visible={showCreate}
        onClose={() => setShowCreate(false)}
        onCreated={handleBoardCreated}
      />

      {/* Join Code Success Display */}
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
      <Modal visible={showJoin} animationType="slide" transparent>
        <View style={styles.overlay}>
          <View style={styles.sheet}>
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
            <Button
              title="Join Board"
              onPress={handleJoin}
              disabled={joinCode.trim().length < 3}
              loading={isJoining}
            />
            <Pressable
              onPress={() => {
                setShowJoin(false);
                setJoinCode("");
                setJoinName("");
              }}
              style={styles.cancelButton}
            >
              <Text style={styles.cancelText}>Cancel</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, paddingTop: 60, backgroundColor: "#fff" },
  loading: { fontSize: 16, color: "#999", textAlign: "center", marginTop: 100 },
  title: { fontSize: 32, fontWeight: "bold", color: "#d4562a", marginBottom: 4 },
  subtitle: { fontSize: 14, color: "#999", marginBottom: 16 },
  emptyState: { alignItems: "center", marginVertical: 40 },
  emptyIcon: { fontSize: 48, marginBottom: 12 },
  emptyText: { fontSize: 18, fontWeight: "600", color: "#333", marginBottom: 8 },
  emptyHint: { fontSize: 14, color: "#999", textAlign: "center", maxWidth: 260 },
  list: { flex: 1, marginBottom: 16 },
  boardCard: {
    backgroundColor: "#f9f7f5",
    borderRadius: 12,
    padding: 16,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: "#eee",
  },
  boardName: { fontSize: 17, fontWeight: "600", color: "#333", marginBottom: 4 },
  boardCode: { fontSize: 13, color: "#999" },
  buttons: { paddingBottom: 16 },
  overlay: {
    flex: 1,
    justifyContent: "flex-end",
    backgroundColor: "rgba(0,0,0,0.4)",
  },
  sheet: {
    backgroundColor: "#fff",
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 24,
    paddingBottom: 40,
  },
  handle: {
    width: 36,
    height: 4,
    backgroundColor: "#ddd",
    borderRadius: 2,
    alignSelf: "center",
    marginBottom: 20,
  },
  sheetTitle: { fontSize: 22, fontWeight: "bold", color: "#333", marginBottom: 20 },
  cancelButton: { alignItems: "center", marginTop: 12, padding: 8 },
  cancelText: { fontSize: 15, color: "#999" },
});
