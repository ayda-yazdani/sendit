import { View, Text, StyleSheet, Share } from "react-native";
import * as Clipboard from "expo-clipboard";
import { Button } from "../shared/Button";
import { Board } from "@/lib/stores/board-store";
import { useState } from "react";
import { theme } from "@/constants/Theme";

interface JoinCodeDisplayProps {
  board: Board;
  onDone: () => void;
  variant?: "created" | "invite";
}

export function JoinCodeDisplay({ board, onDone, variant = "created" }: JoinCodeDisplayProps) {
  const [copied, setCopied] = useState(false);
  const isInvite = variant === "invite";
  const title = isInvite ? "Invite Friends" : "Board Created!";
  const emoji = isInvite ? "🔑" : "🎉";
  const hint = isInvite
    ? "Share this code with your friends so they can join"
    : "Share this code with your friends so they can join";
  const doneLabel = isInvite ? "Close" : "Go to Board";

  const handleCopy = async () => {
    await Clipboard.setStringAsync(board.join_code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleShare = async () => {
    await Share.share({ message: `Join my board "${board.name}" on Sendit! Use code ${board.join_code} or tap: senditapp://join/${board.join_code}` });
  };

  return (
    <View style={styles.container}>
      <Text style={styles.emoji}>{emoji}</Text>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.boardName}>{board.name}</Text>
      <View style={styles.codeBox}>
        <Text style={styles.codeLabel}>Join Code</Text>
        <Text style={styles.code}>{board.join_code}</Text>
      </View>
      <Text style={styles.hint}>{hint}</Text>
      <Button title={copied ? "Copied!" : "Copy Code"} onPress={handleCopy} variant={copied ? "ghost" : "secondary"} style={styles.button} />
      <Button title="Share with Friends" onPress={handleShare} style={styles.button} />
      <Button title={doneLabel} onPress={onDone} variant="ghost" style={styles.button} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: "center", padding: 8 },
  emoji: { fontSize: 48, marginBottom: 12 },
  title: { fontSize: 24, fontFamily: theme.fonts.bold, color: theme.colors.text, marginBottom: 4 },
  boardName: { fontSize: 16, fontFamily: theme.fonts.regular, color: theme.colors.textSecondary, marginBottom: 24 },
  codeBox: { backgroundColor: theme.colors.bgCardLight, borderRadius: 16, padding: 24, alignItems: "center", marginBottom: 16, width: "100%", borderWidth: 1, borderColor: theme.colors.borderLight },
  codeLabel: { fontSize: 12, color: theme.colors.textMuted, textTransform: "uppercase", marginBottom: 8, fontFamily: theme.fonts.semibold, letterSpacing: 1 },
  code: { fontSize: 36, fontFamily: theme.fonts.bold, color: theme.colors.warm, letterSpacing: 6 },
  hint: { fontSize: 13, color: theme.colors.textMuted, textAlign: "center", marginBottom: 24, maxWidth: 260, fontFamily: theme.fonts.regular },
  button: { width: "100%", marginBottom: 8 },
});
