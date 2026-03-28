import { View, Text, StyleSheet, Pressable } from "react-native";
import { useAuthStore } from "@/lib/stores/auth-store";

export default function BoardListScreen() {
  const { deviceId, isInitialized } = useAuthStore();

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
      <Text style={styles.subtitle}>Your boards will appear here</Text>

      <View style={styles.emptyState}>
        <Text style={styles.emptyIcon}>📋</Text>
        <Text style={styles.emptyText}>No boards yet</Text>
        <Text style={styles.emptyHint}>
          Create a board and share the code with your friends
        </Text>
      </View>

      <Pressable style={styles.createButton}>
        <Text style={styles.createButtonText}>Create Board</Text>
      </Pressable>

      <Pressable style={styles.joinButton}>
        <Text style={styles.joinButtonText}>Join with Code</Text>
      </Pressable>

      <Text style={styles.deviceId}>Device: {deviceId?.slice(0, 8)}...</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, paddingTop: 60 },
  loading: { fontSize: 16, color: "#999", textAlign: "center", marginTop: 100 },
  title: { fontSize: 32, fontWeight: "bold", color: "#d4562a", marginBottom: 4 },
  subtitle: { fontSize: 14, color: "#999", marginBottom: 32 },
  emptyState: { alignItems: "center", marginVertical: 40 },
  emptyIcon: { fontSize: 48, marginBottom: 12 },
  emptyText: { fontSize: 18, fontWeight: "600", color: "#333", marginBottom: 8 },
  emptyHint: { fontSize: 14, color: "#999", textAlign: "center", maxWidth: 260 },
  createButton: {
    backgroundColor: "#d4562a",
    borderRadius: 12,
    padding: 16,
    alignItems: "center",
    marginBottom: 12,
  },
  createButtonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  joinButton: {
    borderWidth: 1.5,
    borderColor: "#d4562a",
    borderRadius: 12,
    padding: 16,
    alignItems: "center",
  },
  joinButtonText: { color: "#d4562a", fontSize: 16, fontWeight: "600" },
  deviceId: { fontSize: 11, color: "#ccc", textAlign: "center", marginTop: 24 },
});
