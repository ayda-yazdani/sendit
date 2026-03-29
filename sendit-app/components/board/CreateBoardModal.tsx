import { useState } from "react";
import { Modal, View, Text, StyleSheet, KeyboardAvoidingView, Platform, Alert, Pressable } from "react-native";
import { Button } from "../shared/Button";
import { Input } from "../shared/Input";
import { useBoardStore, Board } from "@/lib/stores/board-store";
import { theme } from "@/constants/Theme";

interface CreateBoardModalProps { visible: boolean; onClose: () => void; onCreated: (board: Board) => void; }

export function CreateBoardModal({ visible, onClose, onCreated }: CreateBoardModalProps) {
  const [boardName, setBoardName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const trimmedName = boardName.trim();
  const isValid = trimmedName.length >= 1 && trimmedName.length <= 50;

  const handleCreate = async () => {
    if (!isValid) return;
    setIsSubmitting(true);
    try {
      const board = await useBoardStore.getState().createBoard(boardName, displayName);
      setBoardName(""); setDisplayName("");
      onCreated(board);
    } catch (error) { Alert.alert("Error", (error as Error).message); }
    finally { setIsSubmitting(false); }
  };

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <KeyboardAvoidingView style={styles.overlay} behavior={Platform.OS === "ios" ? "padding" : "height"}>
        <Pressable
          style={StyleSheet.absoluteFill}
          onPress={() => { setBoardName(""); setDisplayName(""); onClose(); }}
        />
        <View style={styles.sheet}>
          <View style={styles.handle} />
          <Text style={styles.title}>Create Board</Text>
          <Text style={styles.subtitle}>Name your group and invite friends with a code</Text>
          <Input label="Board Name" value={boardName} onChangeText={setBoardName} placeholder="e.g. Summer Friends" maxLength={50} autoFocus />
          <Input label="Your Display Name" value={displayName} onChangeText={setDisplayName} placeholder="e.g. Priya (optional)" maxLength={30} />
          <Button title="Create Board" onPress={handleCreate} disabled={!isValid} loading={isSubmitting} />
          <Pressable onPress={() => { setBoardName(""); setDisplayName(""); onClose(); }} style={styles.cancelButton}>
            <Text style={styles.cancelText}>Cancel</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: { flex: 1, justifyContent: "flex-end", backgroundColor: theme.colors.overlay },
  sheet: { backgroundColor: theme.colors.bg, borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 24, paddingBottom: 40 },
  handle: { width: 36, height: 4, backgroundColor: theme.colors.borderLight, borderRadius: 2, alignSelf: "center", marginBottom: 20 },
  title: { fontSize: 22, fontFamily: theme.fonts.bold, color: theme.colors.text, marginBottom: 4 },
  subtitle: { fontSize: 14, color: theme.colors.textSecondary, marginBottom: 24, fontFamily: theme.fonts.regular },
  cancelButton: { alignItems: "center", marginTop: 12, padding: 8 },
  cancelText: { fontSize: 15, color: theme.colors.textMuted, fontFamily: theme.fonts.regular },
});
