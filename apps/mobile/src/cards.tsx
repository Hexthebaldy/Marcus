import { Image, Pressable, Text, View } from "react-native";
import { router } from "expo-router";
import { mediaUrl, type Editorial, type Note } from "@marcus/api-client";
import { styles as s, c } from "./ui";
export function EditorialCard({
  item,
  index = 0,
}: {
  item: Editorial;
  index?: number;
}) {
  const cover = mediaUrl(item.cover);
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={item.title}
      onPress={() =>
        router.push({ pathname: "/editorials/[id]", params: { id: item.id } })
      }
      style={{ marginBottom: 28 }}
    >
      {cover && (
        <Image
          source={{ uri: cover }}
          style={{
            width: "100%",
            aspectRatio: index === 0 ? 1.15 : 1.5,
            borderRadius: 4,
          }}
        />
      )}
      <View style={{ paddingVertical: 16, gap: 9 }}>
        <Text style={s.eyebrow}>
          {item.focus_type === "event" ? "WHAT’S ON" : "PLACES TO GO"} ·{" "}
          {item.district?.name ?? item.city?.name ?? "上海"}
        </Text>
        <Text
          style={{
            ...s.title,
            fontSize: index === 0 ? 30 : 24,
            lineHeight: index === 0 ? 39 : 33,
          }}
        >
          {item.title}
        </Text>
        <Text numberOfLines={3} style={s.muted}>
          {item.summary}
        </Text>
        <View style={s.row}>
          {item.tags?.slice(0, 3).map((tag) => (
            <Text key={tag.id} style={{ color: c.green, fontSize: 11 }}>
              #{tag.name}
            </Text>
          ))}
          <Text style={{ color: c.green, marginLeft: "auto" }}>阅读 ↗</Text>
        </View>
      </View>
      <View style={s.rule} />
    </Pressable>
  );
}
export function NoteCard({ item }: { item: Note }) {
  const cover = mediaUrl(item.cover);
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={item.title || item.body_text?.slice(0, 40)}
      onPress={() =>
        router.push({ pathname: "/notes/[id]", params: { id: item.id } })
      }
      style={{
        backgroundColor: c.paper,
        borderRadius: 10,
        overflow: "hidden",
        marginBottom: 12,
      }}
    >
      {cover && (
        <Image
          source={{ uri: cover }}
          style={{
            width: "100%",
            aspectRatio: Math.max(
              0.65,
              Math.min(
                1.4,
                (item.cover?.width ?? 1) / (item.cover?.height ?? 1),
              ),
            ),
          }}
        />
      )}
      <View style={{ padding: 12, gap: 9 }}>
        {item.title ? (
          <Text
            numberOfLines={3}
            style={{
              color: c.ink,
              fontSize: 15,
              lineHeight: 22,
              fontWeight: "600",
            }}
          >
            {item.title}
          </Text>
        ) : null}
        {(!cover || !item.title) && (
          <Text
            numberOfLines={cover ? 3 : 8}
            style={{ color: c.ink, fontSize: 14, lineHeight: 23 }}
          >
            {item.body_text}
          </Text>
        )}
        <Text numberOfLines={1} style={{ color: c.muted, fontSize: 11 }}>
          {item.author?.display_name ?? "城市漫游者"}{" "}
          <Text> · ♡ {item.reactions?.like_count ?? 0}</Text>
        </Text>
      </View>
    </Pressable>
  );
}
export function NoteGrid({ items }: { items: Note[] }) {
  const columns: Note[][] = [[], []];
  const heights = [0, 0];
  for (const item of items) {
    const column = heights[0] <= heights[1] ? 0 : 1;
    columns[column].push(item);
    heights[column] += item.cover
      ? 160 /
          Math.max(
            0.65,
            Math.min(1.4, (item.cover.width ?? 1) / (item.cover.height ?? 1)),
          ) +
        90
      : 180;
  }
  return (
    <View style={{ flexDirection: "row", gap: 12, alignItems: "flex-start" }}>
      {columns.map((items, i) => (
        <View key={i} style={{ flex: 1 }}>
          {items.map((item) => (
            <NoteCard key={item.id} item={item} />
          ))}
        </View>
      ))}
    </View>
  );
}
