import { Image, Linking, Text, View, type TextStyle } from "react-native";
import { useVideoPlayer, VideoView } from "expo-video";
import {
  mediaUrl,
  type DocumentNode,
  type MediaAsset,
} from "@marcus/api-client";
import { c, styles as s } from "./ui";
function VideoBlock({ asset }: { asset: MediaAsset }) {
  const player = useVideoPlayer(asset.playback?.url ?? null);
  return (
    <VideoView
      player={player}
      nativeControls
      style={{
        width: "100%",
        aspectRatio: (asset.width ?? 16) / (asset.height ?? 9),
        backgroundColor: c.ink,
      }}
    />
  );
}
function Inline({ nodes }: { nodes: DocumentNode[] }) {
  return (
    <>
      {nodes.map((node, i) => {
        if (node.type === "hardBreak") return "\n";
        const style: TextStyle = {};
        let href: string | undefined;
        for (const mark of node.marks ?? []) {
          if (mark.type === "bold") style.fontWeight = "700";
          if (mark.type === "italic") style.fontStyle = "italic";
          if (mark.type === "strike") style.textDecorationLine = "line-through";
          if (
            mark.type === "link" &&
            typeof mark.attrs?.href === "string" &&
            /^https?:\/\//.test(mark.attrs.href)
          ) {
            href = mark.attrs.href;
            style.color = c.green;
            style.textDecorationLine = "underline";
          }
        }
        return (
          <Text
            key={i}
            style={style}
            accessibilityRole={href ? "link" : undefined}
            onPress={
              href
                ? () => void Linking.openURL(href!).catch(() => {})
                : undefined
            }
          >
            {node.text}
          </Text>
        );
      })}
    </>
  );
}
export function ArticleBody({
  document,
  media,
}: {
  document: DocumentNode;
  media: MediaAsset[];
}) {
  const assets = new Map(media.map((asset) => [asset.id, asset]));
  function render(node: DocumentNode, index: number): React.ReactNode {
    const attrs = node.attrs ?? {};
    const children = node.content ?? [];
    if (node.type === "paragraph" || node.type === "heading")
      return (
        <Text
          key={index}
          selectable
          style={[
            s.body,
            node.type === "heading" && {
              fontSize: attrs.level === 2 ? 25 : 21,
              lineHeight: 34,
              fontWeight: "700",
            },
            {
              textAlign: ["left", "center", "right"].includes(
                String(attrs.align),
              )
                ? (attrs.align as TextStyle["textAlign"])
                : "left",
              marginBottom: 18,
            },
          ]}
        >
          <Inline nodes={children} />
        </Text>
      );
    if (node.type === "blockquote" || node.type === "callout")
      return (
        <View
          key={index}
          style={{
            borderLeftWidth: 3,
            borderColor: c.green,
            padding: 16,
            backgroundColor: c.paper,
            marginBottom: 18,
          }}
        >
          {children.map(render)}
        </View>
      );
    if (node.type === "bulletList" || node.type === "orderedList")
      return (
        <View key={index} style={{ marginBottom: 18, gap: 6 }}>
          {children.map((child, i) => (
            <View key={i} style={{ flexDirection: "row", gap: 10 }}>
              <Text style={s.body}>
                {node.type === "bulletList"
                  ? "•"
                  : `${i + Number(attrs.start ?? 1)}.`}
              </Text>
              <View style={{ flex: 1 }}>{child.content?.map(render)}</View>
            </View>
          ))}
        </View>
      );
    if (node.type === "divider")
      return <View key={index} style={{ ...s.rule, marginVertical: 22 }} />;
    if (node.type === "gallery" && Array.isArray(attrs.items))
      return (
        <View key={index}>
          {attrs.items.map((item, i) =>
            render(
              {
                type: "image",
                attrs: {
                  width: attrs.width,
                  ...(item as Record<string, unknown>),
                },
              },
              i,
            ),
          )}
        </View>
      );
    if (node.type === "image" || node.type === "video") {
      const asset = assets.get(String(attrs.asset_id));
      if (!asset)
        return (
          <Text key={index} style={s.muted}>
            媒体暂时无法显示
          </Text>
        );
      return (
        <View
          key={index}
          style={{
            marginBottom: 22,
            gap: 6,
            marginHorizontal:
              attrs.width === "full" ? -22 : attrs.width === "wide" ? -11 : 0,
          }}
        >
          {node.type === "video" ? (
            <VideoBlock asset={asset} />
          ) : (
            <Image
              accessibilityLabel={String(attrs.alt ?? attrs.caption ?? "")}
              source={{ uri: mediaUrl(asset, "detail") }}
              style={{
                width: "100%",
                aspectRatio: (asset.width ?? 4) / (asset.height ?? 3),
              }}
            />
          )}
          {!!attrs.caption && (
            <Text style={s.muted}>{String(attrs.caption)}</Text>
          )}
          {!!attrs.credit && (
            <Text style={{ ...s.muted, fontSize: 11 }}>
              影像 / {String(attrs.credit)}
            </Text>
          )}
        </View>
      );
    }
    return null;
  }
  return <View>{document.content?.map(render)}</View>;
}
