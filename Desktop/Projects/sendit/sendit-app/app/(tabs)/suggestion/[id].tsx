import { View, Text, StyleSheet } from "react-native";
import { useLocalSearchParams } from "expo-router";

export default function SuggestionScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Suggestion</Text>
      <Text style={styles.subtitle}>Suggestion ID: {id}</Text>
      <Text style={styles.hint}>Plan suggestion and commitment board will appear here</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", alignItems: "center", padding: 20 },
  title: { fontSize: 24, fontWeight: "bold", marginBottom: 8 },
  subtitle: { fontSize: 14, color: "#666", marginBottom: 16 },
  hint: { fontSize: 13, color: "#999", textAlign: "center" },
});
