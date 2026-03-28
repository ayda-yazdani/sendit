import FontAwesome from "@expo/vector-icons/FontAwesome";
import { DarkTheme, DefaultTheme, ThemeProvider } from "@react-navigation/native";
import { useFonts } from "expo-font";
import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { useEffect } from "react";
import "react-native-reanimated";

import { useColorScheme } from "@/components/useColorScheme";
import { useAuthStore } from "@/lib/stores/auth-store";

export { ErrorBoundary } from "expo-router";
export const unstable_settings = { initialRouteName: "(tabs)" };

SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  const [loaded, error] = useFonts({
    SpaceMono: require("../assets/fonts/SpaceMono-Regular.ttf"),
    ...FontAwesome.font,
  });
  const { isInitialized, initialize } = useAuthStore();

  useEffect(() => { if (error) throw error; }, [error]);
  useEffect(() => { initialize(); }, [initialize]);
  useEffect(() => { if (loaded && isInitialized) SplashScreen.hideAsync(); }, [loaded, isInitialized]);

  if (!loaded || !isInitialized) return null;
  return <RootLayoutNav />;
}

function RootLayoutNav() {
  const colorScheme = useColorScheme();
  return (
    <ThemeProvider value={colorScheme === "dark" ? DarkTheme : DefaultTheme}>
      <Stack>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="join/[code]" options={{ title: "Join Board", presentation: "modal" }} />
        <Stack.Screen name="modal" options={{ presentation: "modal" }} />
      </Stack>
    </ThemeProvider>
  );
}
