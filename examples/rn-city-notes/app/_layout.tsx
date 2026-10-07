import { Stack } from "expo-router";
import { NotesProvider } from "../src/notes";

export default function RootLayout() {
  return (
    <NotesProvider>
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: "#E7DFC9" },
          headerTintColor: "#234536",
          contentStyle: { backgroundColor: "#E7DFC9" },
        }}
      >
        <Stack.Screen name="index" options={{ title: "城市笔记" }} />
        <Stack.Screen name="basics" options={{ title: "基础练习" }} />
        <Stack.Screen name="notes/[id]" options={{ title: "笔记详情" }} />
        <Stack.Screen name="compose" options={{ title: "写笔记" }} />
      </Stack>
    </NotesProvider>
  );
}
