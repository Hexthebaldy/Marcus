import { useState } from "react";
import { Image, Pressable, Text, View } from "react-native";
import { router } from "expo-router";
import { mediaUrl } from "@marcus/api-client";
import { useSession } from "../../src/session";
import { Screen, styles as s, Button, ErrorMessage, c } from "../../src/ui";
export default function Profile() {
  const { user, logout } = useSession();
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  async function leave() {
    setBusy(true);
    try {
      await logout();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Screen>
      <Text style={s.eyebrow}>A LIFE WELL EXPLORED</Text>
      <View style={{ ...s.row, marginVertical: 24 }}>
        {mediaUrl(user?.avatar) ? (
          <Image
            source={{ uri: mediaUrl(user?.avatar) }}
            style={{ width: 70, height: 70, borderRadius: 35 }}
          />
        ) : (
          <View
            style={{
              width: 70,
              height: 70,
              borderRadius: 35,
              backgroundColor: c.khaki,
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            <Text style={{ color: c.green, fontSize: 26 }}>
              {user?.display_name.slice(0, 1)}
            </Text>
          </View>
        )}
        <View style={{ flex: 1 }}>
          <Text style={s.heading}>{user?.display_name}</Text>
          <Text style={s.muted}>{user?.city?.name ?? "上海"} · 城市漫游者</Text>
        </View>
      </View>
      <Text style={s.body}>
        {user?.bio || "用一篇笔记，留下你的城市记忆。"}
      </Text>
      <Button title="写一篇笔记" onPress={() => router.push("/notes/edit")} />
      {(
        [
          { type: "notes", title: "我的笔记" },
          { type: "drafts", title: "草稿与审核进度" },
          { type: "bookmarks", title: "我的收藏" },
        ] as const
      ).map((item) => (
        <Pressable
          key={item.type}
          onPress={() =>
            router.push({ pathname: "/library", params: { type: item.type } })
          }
          style={{
            ...s.card,
            flexDirection: "row",
            justifyContent: "space-between",
          }}
        >
          <Text style={s.body}>{item.title}</Text>
          <Text style={{ color: c.green }}>↗</Text>
        </Pressable>
      ))}
      <Button
        secondary
        title="编辑个人资料"
        onPress={() => router.push("/settings")}
      />
      <Button
        secondary
        title="退出登录"
        loading={busy}
        onPress={() => void leave()}
      />
      <ErrorMessage error={error} />
    </Screen>
  );
}
