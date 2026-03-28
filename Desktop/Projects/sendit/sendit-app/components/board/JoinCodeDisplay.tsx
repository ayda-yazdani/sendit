import { View, Text, StyleSheet, Share } from "react-native";
import * as Clipboard from "expo-clipboard";
import { Button } from "../shared/Button";
import { Board } from "@/lib/stores/board-store";
import { useState } from "react";

interface JoinCodeDisplayProps { board: Board; onDone: () => void; }

export function JoinCodeDisplay({ board, onDone }: JoinCodeDisplayProps) {
  const [copied, setCopied] = useState(false);

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
      <Text style={styles.emoji}>🎉</Text>
      <Text style={styles.title}>Board Created!</Text>
      <Text style={styles.boardName}>{board.name}</Text>
      <View style={styles.codeBox}>
        <Text style={styles.codeLabel}>Join Code</Text>
        <Text style={styles.code}>{board.join_code}</Text>
      </View>
      <Text style={styles.hint}>Share this code with your friends so they can join</Text>
      <Button title={copied ? "Copied!" : "Copy Code"} onPress={handleCopy} variant={copied ? "ghost" : "secondary"} style={styles.button} />
      <Button title="Share with Friends" onPress={handleShare} style={styles.button} />
      <Button title="Go to Board" onPress={onDone} variant="ghost" style={styles.button} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: "center", padding: 8 },
  emoji: { fontSize: 48, marginBottom: 12 },
  title: { fontSize: 24, fontWeight: "bold", color: "#333", marginBottom: 4 },
  boardName: { fontSize: 16, color: "#666", marginBottom: 24 },
  codeBox: { backgroundColor: "#f5f0eb", borderRadius: 16, padding: 24, alignItems: "center", marginBottom: 16, width: "100%" },
  codeLabel: { fontSize: 12, color: "#999", textTransform: "uppercase", marginBottom: 8 },
  code: { fontSize: 36, fontWeight: "bold", color: "#d4562a", letterSpacing: 6 },
  hint: { fontSize: 13, color: "#999", textAlign: "center", marginBottom: 24, maxWidth: 260 },
  button: { width: "100%", marginBottom: 8 },
});
