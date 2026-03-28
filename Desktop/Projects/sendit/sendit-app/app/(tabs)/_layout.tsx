import React from "react";
import FontAwesome from "@expo/vector-icons/FontAwesome";
import { Tabs } from "expo-router";
import Colors from "@/constants/Colors";
import { useColorScheme } from "@/components/useColorScheme";

export default function TabLayout() {
  const colorScheme = useColorScheme();
  return (
    <Tabs screenOptions={{ tabBarActiveTintColor: "#d4562a", tabBarInactiveTintColor: Colors[colorScheme ?? "light"].tabIconDefault, headerShown: false }}>
      <Tabs.Screen name="index" options={{ title: "Boards", tabBarIcon: ({ color }) => <FontAwesome name="th-large" size={22} color={color} /> }} />
      <Tabs.Screen name="profile" options={{ title: "Profile", tabBarIcon: ({ color }) => <FontAwesome name="user" size={22} color={color} /> }} />
      <Tabs.Screen name="board/[id]" options={{ href: null }} />
      <Tabs.Screen name="suggestion/[id]" options={{ href: null }} />
    </Tabs>
  );
}
