import { View, Text, StyleSheet } from "react-native";
import { useLocalSearchParams } from "expo-router";
import { theme } from "@/constants/Theme";

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
  container: { flex: 1, justifyContent: "center", alignItems: "center", padding: 20, backgroundColor: theme.colors.bg },
  title: { fontSize: 24, fontWeight: "bold", marginBottom: 8, color: theme.colors.text },
  subtitle: { fontSize: 18, color: theme.colors.warm, marginBottom: 16 },
  hint: { fontSize: 13, color: theme.colors.textSecondary, textAlign: "center" },
});
