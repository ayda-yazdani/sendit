import { View, Text, StyleSheet } from "react-native";
import { Member } from "@/lib/stores/board-store";

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

const AVATAR_COLORS = ["#d4562a", "#1a9e76", "#c49a2e", "#6e6963", "#3b82f6", "#8b5cf6", "#ec4899"];

function getColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

const STATUS_RING: Record<string, string> = {
  in: "#1a9e76",
  maybe: "#c49a2e",
  out: "#999",
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
          <Text style={[styles.tallyCount, { color: "#1a9e76" }]}>{inCount}</Text>
          <Text style={styles.tallyLabel}>In</Text>
        </View>
        <View style={styles.tallyItem}>
          <Text style={[styles.tallyCount, { color: "#c49a2e" }]}>{maybeCount}</Text>
          <Text style={styles.tallyLabel}>Maybe</Text>
        </View>
        <View style={styles.tallyItem}>
          <Text style={[styles.tallyCount, { color: "#999" }]}>{outCount}</Text>
          <Text style={styles.tallyLabel}>Out</Text>
        </View>
        {pendingCount > 0 && (
          <View style={styles.tallyItem}>
            <Text style={[styles.tallyCount, { color: "#ddd" }]}>{pendingCount}</Text>
            <Text style={styles.tallyLabel}>Pending</Text>
          </View>
        )}
      </View>

      {/* Member avatars with status rings */}
      <View style={styles.avatarRow}>
        {members.map(member => {
          const commitment = commitmentMap.get(member.id);
          const ringColor = commitment ? STATUS_RING[commitment.status] : "#ddd";
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
  tallyCount: { fontSize: 24, fontWeight: "bold" },
  tallyLabel: { fontSize: 11, color: "#999", marginTop: 2 },
  avatarRow: { flexDirection: "row", flexWrap: "wrap", gap: 12, justifyContent: "center" },
  avatarContainer: { alignItems: "center", width: 52 },
  avatarRing: { width: 44, height: 44, borderRadius: 22, borderWidth: 3, alignItems: "center", justifyContent: "center" },
  avatar: { width: 34, height: 34, borderRadius: 17, alignItems: "center", justifyContent: "center" },
  avatarText: { color: "#fff", fontSize: 14, fontWeight: "600" },
  avatarName: { fontSize: 10, color: "#666", marginTop: 4, textAlign: "center" },
});
