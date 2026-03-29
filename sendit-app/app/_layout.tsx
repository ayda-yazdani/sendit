import FontAwesome from "@expo/vector-icons/FontAwesome";
import { DarkTheme, ThemeProvider } from "@react-navigation/native";
import { useFonts } from "expo-font";
import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { useEffect } from "react";
import "react-native-reanimated";
import {
  Nunito_300Light,
  Nunito_400Regular,
  Nunito_600SemiBold,
  Nunito_700Bold,
  Nunito_800ExtraBold,
  Nunito_900Black,
} from "@expo-google-fonts/nunito";
import { RubikBubbles_400Regular } from "@expo-google-fonts/rubik-bubbles";

import { useAuthStore } from "@/lib/stores/auth-store";
import AuthScreen from "./auth";
import SurveyScreen from "./survey";

export { ErrorBoundary } from "expo-router";
export const unstable_settings = { initialRouteName: "(tabs)" };

SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  const [loaded, error] = useFonts({
    SpaceMono: require("../assets/fonts/SpaceMono-Regular.ttf"),
    ...FontAwesome.font,
    Nunito_300Light,
    Nunito_400Regular,
    Nunito_600SemiBold,
    Nunito_700Bold,
    Nunito_800ExtraBold,
    Nunito_900Black,
    RubikBubbles_400Regular,
  });
  const { isInitialized, session, surveyCompleted, initialize } = useAuthStore();

  useEffect(() => { if (error) throw error; }, [error]);
  useEffect(() => { initialize(); }, [initialize]);
  useEffect(() => { if (loaded && isInitialized) SplashScreen.hideAsync(); }, [loaded, isInitialized]);

  if (!loaded || !isInitialized) return null;
  if (!session) return <AuthScreen />;

  // Show survey if user hasn't completed it
  if (!surveyCompleted) return <SurveyScreen />;

  return <RootLayoutNav />;
}

function RootLayoutNav() {
  return (
    <ThemeProvider value={DarkTheme}>
      <Stack>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="join/[code]" options={{ title: "Join Board", presentation: "modal" }} />
        <Stack.Screen name="modal" options={{ presentation: "modal" }} />
      </Stack>
    </ThemeProvider>
  );
}
