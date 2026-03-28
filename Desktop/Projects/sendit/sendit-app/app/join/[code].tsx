import { View, Text, StyleSheet } from "react-native";
import { useLocalSearchParams } from "expo-router";

export default function JoinBoardScreen() {
  const { code } = useLocalSearchParams<{ code: string }>();
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Join Board</Text>
      <Text style={styles.subtitle}>Code: {code}</Text>
      <Text style={styles.hint}>You'll be prompted to enter your display name</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", alignItems: "center", padding: 20 },
  title: { fontSize: 24, fontWeight: "bold", marginBottom: 8 },
  subtitle: { fontSize: 18, color: "#d4562a", marginBottom: 16 },
  hint: { fontSize: 13, color: "#999", textAlign: "center" },
});
