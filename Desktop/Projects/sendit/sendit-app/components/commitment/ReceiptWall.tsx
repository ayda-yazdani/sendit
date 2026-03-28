import { useState } from "react";
import { View, Text, StyleSheet, Image, Pressable, Alert } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { supabase } from "@/lib/supabase";
import { Member } from "@/lib/stores/board-store";

interface Commitment {
  id: string;
  suggestion_id: string;
  member_id: string;
  status: "in" | "maybe" | "out";
  receipt_url: string | null;
}

interface ReceiptWallProps {
  commitments: Commitment[];
  members: Member[];
  currentMemberId: string | null;
  suggestionId: string;
}

const AVATAR_COLORS = ["#d4562a", "#1a9e76", "#c49a2e", "#6e6963", "#3b82f6", "#8b5cf6", "#ec4899"];

function getColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

export function ReceiptWall({ commitments, members, currentMemberId, suggestionId }: ReceiptWallProps) {
  const [uploading, setUploading] = useState(false);

  const inCommitments = commitments.filter(c => c.status === "in");
  const myCommitment = commitments.find(c => c.member_id === currentMemberId);
  const canUpload = myCommitment?.status === "in" && !myCommitment?.receipt_url;

  const handleUploadReceipt = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      quality: 0.7,
      allowsEditing: true,
    });

    if (result.canceled || !result.assets?.[0]) return;

    setUploading(true);
    try {
      const asset = result.assets[0];
      const ext = asset.uri.split(".").pop() || "jpg";
      const fileName = `${suggestionId}/${currentMemberId}.${ext}`;

      const response = await fetch(asset.uri);
      const blob = await response.blob();

      const { error: uploadError } = await supabase.storage
        .from("receipts")
        .upload(fileName, blob, { contentType: `image/${ext}`, upsert: true });

      if (uploadError) {
        Alert.alert("Upload failed", uploadError.message);
        return;
      }

      const { data: { publicUrl } } = supabase.storage
        .from("receipts")
        .getPublicUrl(fileName);

      await supabase
        .from("commitments")
        .update({ receipt_url: publicUrl })
        .eq("id", myCommitment!.id);

    } catch (err) {
      Alert.alert("Error", (err as Error).message);
    } finally {
      setUploading(false);
    }
  };

  if (inCommitments.length === 0) return null;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Receipt Wall</Text>
      <Text style={styles.subtitle}>Who's got their tickets?</Text>

      <View style={styles.wall}>
        {inCommitments.map(commitment => {
          const member = members.find(m => m.id === commitment.member_id);
          if (!member) return null;

          const initial = (member.display_name || "?")[0].toUpperCase();
          const bgColor = getColor(member.display_name);
          const hasReceipt = !!commitment.receipt_url;

          return (
            <View key={commitment.id} style={styles.receiptItem}>
              <View style={[styles.avatarRing, { borderColor: hasReceipt ? "#1a9e76" : "#ddd" }]}>
                <View style={[styles.avatar, { backgroundColor: bgColor }]}>
                  <Text style={styles.avatarText}>{initial}</Text>
                </View>
                {hasReceipt && (
                  <View style={styles.checkmark}>
                    <Text style={styles.checkmarkText}>✓</Text>
                  </View>
                )}
              </View>
              <Text style={styles.memberName} numberOfLines={1}>
                {member.display_name.split(" ")[0]}
              </Text>
              <Text style={[styles.receiptStatus, { color: hasReceipt ? "#1a9e76" : "#ccc" }]}>
                {hasReceipt ? "Confirmed" : "Pending"}
              </Text>
            </View>
          );
        })}
      </View>

      {canUpload && (
        <Pressable style={styles.uploadButton} onPress={handleUploadReceipt} disabled={uploading}>
          <Text style={styles.uploadText}>
            {uploading ? "Uploading..." : "📸 Upload Ticket Screenshot"}
          </Text>
        </Pressable>
      )}

      {myCommitment?.receipt_url && (
        <View style={styles.myReceipt}>
          <Image source={{ uri: myCommitment.receipt_url }} style={styles.receiptImage} />
          <Text style={styles.receiptConfirmed}>Your ticket confirmed ✓</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginTop: 8 },
  title: { fontSize: 16, fontWeight: "700", color: "#333", marginBottom: 4 },
  subtitle: { fontSize: 13, color: "#999", marginBottom: 16 },
  wall: { flexDirection: "row", flexWrap: "wrap", gap: 16, justifyContent: "center", marginBottom: 16 },
  receiptItem: { alignItems: "center", width: 64 },
  avatarRing: { width: 50, height: 50, borderRadius: 25, borderWidth: 3, alignItems: "center", justifyContent: "center", position: "relative" },
  avatar: { width: 40, height: 40, borderRadius: 20, alignItems: "center", justifyContent: "center" },
  avatarText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  checkmark: { position: "absolute", bottom: -2, right: -2, backgroundColor: "#1a9e76", borderRadius: 8, width: 16, height: 16, alignItems: "center", justifyContent: "center" },
  checkmarkText: { color: "#fff", fontSize: 10, fontWeight: "bold" },
  memberName: { fontSize: 11, color: "#666", marginTop: 6, textAlign: "center" },
  receiptStatus: { fontSize: 9, fontWeight: "600", marginTop: 2 },
  uploadButton: { backgroundColor: "#f5f0eb", borderRadius: 12, padding: 14, alignItems: "center", borderWidth: 1, borderColor: "#e0d9d0", borderStyle: "dashed" },
  uploadText: { fontSize: 14, color: "#d4562a", fontWeight: "600" },
  myReceipt: { marginTop: 12, alignItems: "center" },
  receiptImage: { width: 200, height: 120, borderRadius: 10, backgroundColor: "#f0f0f0" },
  receiptConfirmed: { fontSize: 12, color: "#1a9e76", marginTop: 8, fontWeight: "500" },
});
