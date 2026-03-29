import { View, Text, StyleSheet } from "react-native";
import { Member } from "@/lib/stores/board-store";
import { theme } from "@/constants/Theme";

interface Commitment {
  id: string;
  suggestion_id: string;
  member_id: string;
  status: "in" | "maybe" | "out";
  receipt_url: string | null;
}

interface CommitmentTallyProps {
  commitments: Commitment[];
  members: Member[];
}

const AVATAR_COLORS = ["#9b1b4a", "#4d8a8a", "#a3b899", "#c9917a"];

function getColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

const STATUS_RING: Record<string, string> = {
  in: "#4d8a8a",
  maybe: "#c9917a",
  out: "#5a7094",
};

export function CommitmentTally({ commitments, members }: CommitmentTallyProps) {
  const inCount = commitments.filter(c => c.status === "in").length;
  const maybeCount = commitments.filter(c => c.status === "maybe").length;
  const outCount = commitments.filter(c => c.status === "out").length;
  const pendingCount = members.length - commitments.length;

  const commitmentMap = new Map(commitments.map(c => [c.member_id, c]));

  return (
    <View style={styles.container}>
      {/* Tally counts */}
      <View style={styles.tallyRow}>
        <View style={styles.tallyItem}>
          <Text style={[styles.tallyCount, { color: theme.colors.secondary }]}>{inCount}</Text>
          <Text style={styles.tallyLabel}>In</Text>
        </View>
        <View style={styles.tallyItem}>
          <Text style={[styles.tallyCount, { color: theme.colors.warm }]}>{maybeCount}</Text>
          <Text style={styles.tallyLabel}>Maybe</Text>
        </View>
        <View style={styles.tallyItem}>
          <Text style={[styles.tallyCount, { color: theme.colors.textMuted }]}>{outCount}</Text>
          <Text style={styles.tallyLabel}>Out</Text>
        </View>
        {pendingCount > 0 && (
          <View style={styles.tallyItem}>
            <Text style={[styles.tallyCount, { color: theme.colors.border }]}>{pendingCount}</Text>
            <Text style={styles.tallyLabel}>Pending</Text>
          </View>
        )}
      </View>

      {/* Member avatars with status rings */}
      <View style={styles.avatarRow}>
        {members.map(member => {
          const commitment = commitmentMap.get(member.id);
          const ringColor = commitment ? STATUS_RING[commitment.status] : theme.colors.border;
          const initial = (member.display_name || "?")[0].toUpperCase();
          const bgColor = getColor(member.display_name);

          return (
            <View key={member.id} style={styles.avatarContainer}>
              <View style={[styles.avatarRing, { borderColor: ringColor }]}>
                <View style={[styles.avatar, { backgroundColor: bgColor }]}>
                  <Text style={styles.avatarText}>{initial}</Text>
                </View>
              </View>
              <Text style={styles.avatarName} numberOfLines={1}>
                {member.display_name.split(" ")[0]}
              </Text>
            </View>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginTop: 16 },
  tallyRow: { flexDirection: "row", justifyContent: "center", gap: 24, marginBottom: 16 },
  tallyItem: { alignItems: "center" },
  tallyCount: { fontSize: 24, fontWeight: "bold", fontFamily: theme.fonts.bold },
  tallyLabel: { fontSize: 11, color: theme.colors.textMuted, marginTop: 2, fontFamily: theme.fonts.regular },
  avatarRow: { flexDirection: "row", flexWrap: "wrap", gap: 12, justifyContent: "center" },
  avatarContainer: { alignItems: "center", width: 52 },
  avatarRing: { width: 44, height: 44, borderRadius: 22, borderWidth: 3, alignItems: "center", justifyContent: "center" },
  avatar: { width: 34, height: 34, borderRadius: 17, alignItems: "center", justifyContent: "center" },
  avatarText: { color: "#fff", fontSize: 14, fontWeight: "600", fontFamily: theme.fonts.semibold },
  avatarName: { fontSize: 10, color: theme.colors.textSecondary, marginTop: 4, textAlign: "center", fontFamily: theme.fonts.regular },
});
