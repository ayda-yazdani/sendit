import { View, Text, StyleSheet, Pressable, Alert } from "react-native";
import { useAuthStore } from "@/lib/stores/auth-store";
import { theme } from "@/constants/Theme";

export default function ProfileScreen() {
  const { session, signOut } = useAuthStore();
  const displayName =
    (session?.user.user_metadata?.display_name as string | undefined) || "User";
  const email = session?.user.email || "";

  const handleSignOut = () => {
    Alert.alert("Sign Out", "Are you sure?", [
      { text: "Cancel", style: "cancel" },
      { text: "Sign Out", style: "destructive", onPress: signOut },
    ]);
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Profile</Text>

      <Text style={styles.label}>Name</Text>
      <Text style={styles.value}>{displayName}</Text>

      <Text style={styles.label}>Email</Text>
      <Text style={styles.value}>{email}</Text>

      <Pressable style={styles.signOutButton} onPress={handleSignOut}>
        <Text style={styles.signOutText}>Sign Out</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, paddingTop: 60, backgroundColor: theme.colors.bg },
  title: { fontSize: 28, fontWeight: "bold", marginBottom: 24, color: theme.colors.text, fontFamily: theme.fonts.bold },
  label: { fontSize: 12, color: theme.colors.textMuted, textTransform: "uppercase", marginTop: 16, marginBottom: 4, fontFamily: theme.fonts.semibold, letterSpacing: 1 },
  value: { fontSize: 16, color: theme.colors.text, fontFamily: theme.fonts.regular },
  signOutButton: { marginTop: 40, paddingVertical: 14, borderRadius: theme.borderRadius.md, borderWidth: 1, borderColor: theme.colors.error, alignItems: "center" },
  signOutText: { color: theme.colors.error, fontFamily: theme.fonts.semibold, fontSize: 15 },
});
