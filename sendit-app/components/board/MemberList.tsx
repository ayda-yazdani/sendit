import { View, Text, StyleSheet, FlatList } from "react-native";
import { Member } from "@/lib/stores/board-store";
import { useAuthStore } from "@/lib/stores/auth-store";
import { theme } from "@/constants/Theme";

const AVATAR_COLORS = ["#982649", "#3C6E71", "#94C595", "#D8A48F", "#284B63"];

function getAvatarColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

function MemberRow({ member, isYou }: { member: Member; isYou: boolean }) {
  const initial = (member.display_name || "?")[0].toUpperCase();
  const color = getAvatarColor(member.display_name);

  return (
    <View style={styles.row}>
      <View style={[styles.avatar, { backgroundColor: color }]}>
        <Text style={styles.avatarText}>{initial}</Text>
      </View>
      <Text style={styles.name}>
        {member.display_name}
        {isYou && <Text style={styles.youBadge}> (You)</Text>}
      </Text>
    </View>
  );
}

interface MemberListProps {
  members: Member[];
}

export function MemberList({ members }: MemberListProps) {
  const { session } = useAuthStore();
  const userId = session?.user.id;
  const sorted = [...members].sort((a, b) => a.display_name.localeCompare(b.display_name));

  return (
    <FlatList
      data={sorted}
      keyExtractor={(item) => item.id}
      scrollEnabled={false}
      renderItem={({ item }) => (
        <MemberRow member={item} isYou={item.user_id === userId} />
      )}
      ListEmptyComponent={
        <Text style={styles.empty}>No members yet</Text>
      }
    />
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", alignItems: "center", paddingVertical: 10 },
  avatar: { width: 36, height: 36, borderRadius: 18, alignItems: "center", justifyContent: "center", marginRight: 12 },
  avatarText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  name: { fontSize: 15, color: "#333", fontWeight: "500" },
  youBadge: { fontSize: 13, color: "#999", fontWeight: "400" },
  empty: { fontSize: 14, color: "#999", textAlign: "center", paddingVertical: 20 },
});
