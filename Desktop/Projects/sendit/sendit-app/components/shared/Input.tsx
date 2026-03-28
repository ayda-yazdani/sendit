import { View, Text, TextInput, StyleSheet } from "react-native";

interface InputProps {
  label?: string;
  value: string;
  onChangeText: (text: string) => void;
  placeholder?: string;
  maxLength?: number;
  error?: string;
  autoFocus?: boolean;
}

export function Input({
  label,
  value,
  onChangeText,
  placeholder,
  maxLength,
  error,
  autoFocus,
}: InputProps) {
  return (
    <View style={styles.container}>
      {label && <Text style={styles.label}>{label}</Text>}
      <TextInput
        style={[styles.input, error && styles.inputError]}
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor="#999"
        maxLength={maxLength}
        autoFocus={autoFocus}
      />
      {error && <Text style={styles.error}>{error}</Text>}
      {maxLength && (
        <Text style={styles.counter}>
          {value.length}/{maxLength}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginBottom: 16 },
  label: { fontSize: 14, fontWeight: "600", color: "#333", marginBottom: 6 },
  input: {
    borderWidth: 1,
    borderColor: "#ddd",
    borderRadius: 10,
    padding: 14,
    fontSize: 16,
    color: "#333",
    backgroundColor: "#f9f9f9",
  },
  inputError: { borderColor: "#e74c3c" },
  error: { fontSize: 12, color: "#e74c3c", marginTop: 4 },
  counter: { fontSize: 11, color: "#999", textAlign: "right", marginTop: 4 },
});
