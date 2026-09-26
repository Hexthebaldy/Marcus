import { Stack, Redirect, useSegments } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SessionProvider, useSession } from "../src/session";
import { Screen, Busy, ErrorMessage, Button, c } from "../src/ui";
function Navigation() {
  const { user, loading, error, reload } = useSession();
  const segments = useSegments();
  if (loading)
    return (
      <Screen>
        <Busy />
      </Screen>
    );
  if (error && !user)
    return (
      <Screen>
        <ErrorMessage error={error} />
        <Button title="重新连接" onPress={() => void reload()} />
      </Screen>
    );
  if (!user && segments[0] !== "login") return <Redirect href="/login" />;
  if (user && segments[0] === "login") return <Redirect href="/" />;
  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: c.background },
        headerTintColor: c.green,
        headerShadowVisible: false,
        headerBackTitle: "返回",
        contentStyle: { backgroundColor: c.background },
      }}
    >
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      <Stack.Screen name="login" options={{ headerShown: false }} />
      <Stack.Screen name="notes/[id]" options={{ title: "城市笔记" }} />
      <Stack.Screen name="notes/edit" options={{ title: "记录一刻" }} />
      <Stack.Screen
        name="editorials/[id]"
        options={{ title: "MARCUS · 城市精选" }}
      />
      <Stack.Screen name="library" options={{ title: "我的内容" }} />
      <Stack.Screen name="settings" options={{ title: "个人资料" }} />
    </Stack>
  );
}
export default function RootLayout() {
  return (
    <SessionProvider>
      <StatusBar style="dark" />
      <Navigation />
    </SessionProvider>
  );
}
