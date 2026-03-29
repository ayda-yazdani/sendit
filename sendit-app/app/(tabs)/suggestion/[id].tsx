import { View, Text, StyleSheet } from "react-native";

import { theme } from "@/constants/Theme";

export default function SuggestionScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Suggestions</Text>
      <Text style={styles.body}>
        The current mobile app now uses the FastAPI backend. The older
        suggestion commitment flow on this screen still needs matching backend
        endpoints, so it has been temporarily disabled.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    padding: 24,
    backgroundColor: theme.colors.bg,
  },
  title: {
    fontSize: 28,
    color: theme.colors.text,
    fontFamily: theme.fonts.bold,
    marginBottom: 12,
  },
  body: {
    fontSize: 15,
    lineHeight: 22,
    color: theme.colors.textSecondary,
    fontFamily: theme.fonts.regular,
  },
});
