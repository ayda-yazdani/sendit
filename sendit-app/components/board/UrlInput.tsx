import { useState } from "react";
import {
  View,
  TextInput,
  Text,
  StyleSheet,
  Pressable,
  ActivityIndicator,
  Keyboard,
} from "react-native";
import { detectPlatform, isValidUrl, PLATFORM_DISPLAY } from "@/lib/utils/platform-detect";
import { addBoardReel } from "@/lib/api/boards";
import { invokeExtraction } from "@/lib/ai/extraction";
import { theme } from "@/constants/Theme";
import { useAuthStore } from "@/lib/stores/auth-store";

interface UrlInputProps {
  boardId: string;
  memberId: string;
  onReelAdded?: (reel: any) => void;
}

export function UrlInput({ boardId, memberId, onReelAdded }: UrlInputProps) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const session = useAuthStore((state) => state.session);

  const trimmedUrl = url.trim();

  const handleSubmit = async () => {
    setError(null);

    if (!trimmedUrl) return;

    if (!isValidUrl(trimmedUrl)) {
      setError("Please paste a valid URL");
      return;
    }

    setIsSubmitting(true);
    Keyboard.dismiss();

    try {
      if (!session) {
        setError("Please log in again.");
        return;
      }

      const platform = detectPlatform(trimmedUrl);
      const reel = await addBoardReel(session, boardId, memberId, {
        url: trimmedUrl,
        platform,
      });

      setUrl("");
      onReelAdded?.(reel);

      void invokeExtraction(reel.id, trimmedUrl, boardId);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Show platform hint as user types
  const detectedPlatform = trimmedUrl ? detectPlatform(trimmedUrl) : null;
  const platformInfo = detectedPlatform ? PLATFORM_DISPLAY[detectedPlatform] : null;

  return (
    <View style={styles.container}>
      {error && <Text style={styles.error}>{error}</Text>}
      <View style={styles.inputRow}>
        {platformInfo && trimmedUrl.length > 10 && (
          <Text style={styles.platformHint}>{platformInfo.emoji}</Text>
        )}
        <TextInput
          style={styles.input}
          value={url}
          onChangeText={(t) => {
            setUrl(t);
            setError(null);
          }}
          placeholder="Paste a link..."
          placeholderTextColor={theme.colors.textMuted}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="url"
          returnKeyType="send"
          onSubmitEditing={handleSubmit}
          editable={!isSubmitting}
        />
        <Pressable
          style={[styles.sendButton, (!trimmedUrl || isSubmitting) && styles.sendDisabled]}
          onPress={handleSubmit}
          disabled={!trimmedUrl || isSubmitting}
        >
          {isSubmitting ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <Text style={styles.sendText}>↑</Text>
          )}
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { paddingHorizontal: 16, paddingBottom: 8, backgroundColor: theme.colors.bgDark, borderTopWidth: 1, borderTopColor: theme.colors.borderLight },
  inputRow: { flexDirection: "row", alignItems: "center", gap: 8, paddingTop: 8 },
  platformHint: { fontSize: 20 },
  input: { flex: 1, backgroundColor: theme.colors.bgInput, borderRadius: 20, paddingHorizontal: 16, paddingVertical: 10, fontSize: 15, color: theme.colors.text },
  sendButton: { width: 36, height: 36, borderRadius: 18, backgroundColor: theme.colors.primary, alignItems: "center", justifyContent: "center" },
  sendDisabled: { opacity: 0.4 },
  sendText: { color: "#fff", fontSize: 18, fontWeight: "bold" },
  error: { fontSize: 12, color: theme.colors.warm, paddingTop: 8, paddingBottom: 2 },
});
