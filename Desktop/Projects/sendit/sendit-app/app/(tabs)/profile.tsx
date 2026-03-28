import { View, Text, StyleSheet } from "react-native";
import { useAuthStore } from "@/lib/stores/auth-store";

export default function ProfileScreen() {
  const { deviceId, googleId } = useAuthStore();

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Profile</Text>
      <Text style={styles.label}>Device ID</Text>
      <Text style={styles.value}>{deviceId ?? "Loading..."}</Text>
      <Text style={styles.label}>Google Account</Text>
      <Text style={styles.value}>{googleId ?? "Not connected"}</Text>
      <Text style={styles.hint}>Calendar integration will appear here</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, paddingTop: 60 },
  title: { fontSize: 28, fontWeight: "bold", marginBottom: 24 },
  label: { fontSize: 12, color: "#999", textTransform: "uppercase", marginTop: 16, marginBottom: 4 },
  value: { fontSize: 14, color: "#333", fontFamily: "SpaceMono" },
  hint: { fontSize: 13, color: "#999", marginTop: 32, textAlign: "center" },
});
