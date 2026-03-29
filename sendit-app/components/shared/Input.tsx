import { View, Text, TextInput, StyleSheet } from "react-native";
import { theme } from "@/constants/Theme";

interface InputProps {
  label?: string;
  value: string;
  onChangeText: (text: string) => void;
  placeholder?: string;
  maxLength?: number;
  error?: string;
  autoFocus?: boolean;
}

export function Input({ label, value, onChangeText, placeholder, maxLength, error, autoFocus }: InputProps) {
  return (
    <View style={styles.container}>
      {label && <Text style={styles.label}>{label}</Text>}
      <TextInput
        style={[styles.input, error && styles.inputError]}
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={theme.colors.textMuted}
        maxLength={maxLength}
        autoFocus={autoFocus}
      />
      {error && <Text style={styles.error}>{error}</Text>}
      {maxLength && <Text style={styles.counter}>{value.length}/{maxLength}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginBottom: 16 },
  label: { fontSize: 14, fontFamily: theme.fonts.semibold, color: theme.colors.textSecondary, marginBottom: 6 },
  input: { borderWidth: 1, borderColor: theme.colors.borderLight, borderRadius: 10, padding: 14, fontSize: 16, color: theme.colors.text, backgroundColor: theme.colors.bgInput, fontFamily: theme.fonts.regular },
  inputError: { borderColor: theme.colors.error },
  error: { fontSize: 12, color: theme.colors.error, marginTop: 4, fontFamily: theme.fonts.regular },
  counter: { fontSize: 11, color: theme.colors.textMuted, textAlign: "right", marginTop: 4, fontFamily: theme.fonts.regular },
});
