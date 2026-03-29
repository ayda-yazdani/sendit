import React from "react";
import FontAwesome from "@expo/vector-icons/FontAwesome";
import { Tabs } from "expo-router";
import { theme } from "@/constants/Theme";

export default function TabLayout() {
  return (
    <Tabs screenOptions={{
      tabBarActiveTintColor: theme.colors.warm,
      tabBarInactiveTintColor: "#555",
      tabBarStyle: {
        backgroundColor: "#000",
        borderTopColor: "rgba(255,255,255,0.06)",
        borderTopWidth: 0.5,
        paddingTop: 4,
        height: 85,
      },
      tabBarLabelStyle: {
        fontFamily: theme.fonts.semibold,
        fontSize: 11,
        marginTop: 2,
      },
      headerShown: false,
    }}>
      <Tabs.Screen name="index" options={{
        title: "Boards",
        tabBarIcon: ({ color }) => <FontAwesome name="th-large" size={22} color={color} />,
      }} />
      <Tabs.Screen name="profile" options={{
        title: "Profile",
        tabBarIcon: ({ color }) => <FontAwesome name="user" size={22} color={color} />,
      }} />
      <Tabs.Screen name="board/[id]" options={{ href: null }} />
      <Tabs.Screen name="flashcards/[category]" options={{ href: null }} />
      <Tabs.Screen name="suggestion/[id]" options={{ href: null }} />
    </Tabs>
  );
}
