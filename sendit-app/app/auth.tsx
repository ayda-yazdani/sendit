import { useState } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Alert,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { BlurView } from "expo-blur";
import { theme } from "@/constants/Theme";
import { supabase } from "@/lib/supabase";

export default function AuthScreen() {
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleAuth() {
    if (!email.trim() || !password.trim()) {
      Alert.alert("Missing fields", "Please enter email and password.");
      return;
    }
    if (isSignUp && !displayName.trim()) {
      Alert.alert("Missing name", "Please enter your display name.");
      return;
    }

    setLoading(true);
    try {
      if (isSignUp) {
        const { error } = await supabase.auth.signUp({
          email: email.trim(),
          password,
          options: { data: { display_name: displayName.trim() } },
        });
        if (error) throw error;
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email: email.trim(),
          password,
        });
        if (error) throw error;
      }
    } catch (error: any) {
      Alert.alert("Error", error.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <View style={styles.container}>
      {/* Background gradient blobs */}
      <View style={styles.blobContainer}>
        <LinearGradient
          colors={["#982649", "#D8A48F", "#3C6E71"]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={[styles.blob, styles.blob1]}
        />
        <LinearGradient
          colors={["#3C6E71", "#284B63", "#94C595"]}
          start={{ x: 0.2, y: 0 }}
          end={{ x: 0.8, y: 1 }}
          style={[styles.blob, styles.blob2]}
        />
        <LinearGradient
          colors={["#D8A48F", "#982649", "#284B63"]}
          start={{ x: 1, y: 0 }}
          end={{ x: 0, y: 1 }}
          style={[styles.blob, styles.blob3]}
        />
      </View>

      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        style={styles.content}
      >
        {/* Logo */}
        <Text style={styles.logo}>sendit</Text>
        <Text style={styles.tagline}>
          share reels. see your vibe. make plans.
        </Text>

        {/* Glassmorphism card */}
        <View style={styles.cardOuter}>
          <BlurView intensity={40} tint="dark" style={styles.card}>
            <View style={styles.cardInner}>
              <Text style={styles.cardTitle}>
                {isSignUp ? "Create Account" : "Welcome Back"}
              </Text>

              {isSignUp && (
                <View style={styles.inputContainer}>
                  <Text style={styles.inputLabel}>Display Name</Text>
                  <TextInput
                    style={styles.input}
                    placeholder="What should we call you?"
                    placeholderTextColor={theme.colors.textMuted}
                    value={displayName}
                    onChangeText={setDisplayName}
                    autoCapitalize="words"
                  />
                </View>
              )}

              <View style={styles.inputContainer}>
                <Text style={styles.inputLabel}>Email</Text>
                <TextInput
                  style={styles.input}
                  placeholder="your@email.com"
                  placeholderTextColor={theme.colors.textMuted}
                  value={email}
                  onChangeText={setEmail}
                  keyboardType="email-address"
                  autoCapitalize="none"
                  autoComplete="email"
                />
              </View>

              <View style={styles.inputContainer}>
                <Text style={styles.inputLabel}>Password</Text>
                <TextInput
                  style={styles.input}
                  placeholder="Min 8 characters"
                  placeholderTextColor={theme.colors.textMuted}
                  value={password}
                  onChangeText={setPassword}
                  secureTextEntry
                  autoComplete={isSignUp ? "new-password" : "current-password"}
                />
              </View>

              {/* CTA Button */}
              <Pressable
                style={({ pressed }) => [
                  styles.button,
                  pressed && styles.buttonPressed,
                  loading && styles.buttonDisabled,
                ]}
                onPress={handleAuth}
                disabled={loading}
              >
                <LinearGradient
                  colors={["#982649", "#b03058"]}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 0 }}
                  style={styles.buttonGradient}
                >
                  {loading ? (
                    <ActivityIndicator color={theme.colors.text} />
                  ) : (
                    <Text style={styles.buttonText}>
                      {isSignUp ? "Sign Up" : "Log In"}
                    </Text>
                  )}
                </LinearGradient>
              </Pressable>

              {/* Toggle */}
              <Pressable
                onPress={() => setIsSignUp(!isSignUp)}
                style={styles.toggleContainer}
              >
                <Text style={styles.toggleText}>
                  {isSignUp
                    ? "Already have an account? "
                    : "Don't have an account? "}
                  <Text style={styles.toggleHighlight}>
                    {isSignUp ? "Log In" : "Sign Up"}
                  </Text>
                </Text>
              </Pressable>
            </View>
          </BlurView>
        </View>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.bgDark,
  },

  // Background blobs
  blobContainer: {
    ...StyleSheet.absoluteFillObject,
    overflow: "hidden",
  },
  blob: {
    position: "absolute",
    borderRadius: 999,
    opacity: 0.35,
  },
  blob1: {
    width: 280,
    height: 280,
    top: -60,
    right: -40,
  },
  blob2: {
    width: 220,
    height: 220,
    top: 160,
    left: -60,
  },
  blob3: {
    width: 180,
    height: 180,
    bottom: 80,
    right: -30,
  },

  content: {
    flex: 1,
    justifyContent: "center",
    paddingHorizontal: 24,
  },

  // Logo
  logo: {
    fontFamily: theme.fonts.display,
    fontSize: 48,
    color: theme.colors.text,
    textAlign: "center",
    marginBottom: 8,
    textShadowColor: "rgba(152, 38, 73, 0.6)",
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 20,
  },
  tagline: {
    fontFamily: theme.fonts.regular,
    fontSize: 15,
    color: theme.colors.textSecondary,
    textAlign: "center",
    marginBottom: 40,
    letterSpacing: 0.5,
  },

  // Glassmorphism card
  cardOuter: {
    borderRadius: theme.borderRadius.xl,
    overflow: "hidden",
    // Glow shadow
    shadowColor: "#982649",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 20,
    elevation: 10,
  },
  card: {
    overflow: "hidden",
    borderRadius: theme.borderRadius.xl,
  },
  cardInner: {
    padding: 28,
    backgroundColor: "rgba(33, 61, 85, 0.45)",
    borderWidth: 1,
    borderColor: "rgba(240, 236, 230, 0.08)",
    borderRadius: theme.borderRadius.xl,
  },
  cardTitle: {
    fontFamily: theme.fonts.bold,
    fontSize: 22,
    color: theme.colors.text,
    marginBottom: 24,
    textAlign: "center",
  },

  // Inputs
  inputContainer: {
    marginBottom: 18,
  },
  inputLabel: {
    fontFamily: theme.fonts.semibold,
    fontSize: 13,
    color: theme.colors.textSecondary,
    marginBottom: 6,
    marginLeft: 4,
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  input: {
    backgroundColor: "rgba(26, 51, 71, 0.7)",
    borderWidth: 1,
    borderColor: "rgba(240, 236, 230, 0.1)",
    borderRadius: theme.borderRadius.md,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontFamily: theme.fonts.regular,
    fontSize: 16,
    color: theme.colors.text,
  },

  // Button
  button: {
    marginTop: 8,
    borderRadius: theme.borderRadius.md,
    overflow: "hidden",
    // Glow
    shadowColor: "#982649",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.5,
    shadowRadius: 12,
    elevation: 8,
  },
  buttonPressed: {
    opacity: 0.85,
    transform: [{ scale: 0.98 }],
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonGradient: {
    paddingVertical: 16,
    alignItems: "center",
    justifyContent: "center",
  },
  buttonText: {
    fontFamily: theme.fonts.bold,
    fontSize: 17,
    color: theme.colors.text,
    letterSpacing: 0.5,
  },

  // Toggle
  toggleContainer: {
    marginTop: 20,
    alignItems: "center",
  },
  toggleText: {
    fontFamily: theme.fonts.regular,
    fontSize: 14,
    color: theme.colors.textSecondary,
  },
  toggleHighlight: {
    color: theme.colors.warm,
    fontFamily: theme.fonts.semibold,
  },
});
