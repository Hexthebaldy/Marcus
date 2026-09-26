import { Image, Text, View } from "react-native";
import { useLocalSearchParams } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { mediaUrl, type Editorial } from "@marcus/api-client";
import { api } from "../../src/session";
import { Screen, styles as s, Busy, ErrorMessage, date } from "../../src/ui";
import { ArticleBody } from "../../src/article-body";
import { ContentActions } from "../../src/content-actions";
import { EventInfo, PlaceInfo } from "../../src/place-info";
export default function EditorialDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const query = useQuery({
    queryKey: ["editorials", id],
    queryFn: () => api.get<Editorial>(`/editorials/${id}`),
    refetchInterval: 240_000,
  });
  const article = query.data;
  return (
    <Screen>
      <ErrorMessage error={query.error} />
      {query.isLoading && <Busy />}
      {article && (
        <>
          <Text style={s.eyebrow}>
            {article.focus_type === "event" ? "WHAT’S ON" : "PLACES TO GO"} ·{" "}
            {article.city?.name} {article.district?.name}
          </Text>
          <Text style={s.title}>{article.title}</Text>
          {!!article.subtitle && (
            <Text style={s.heading}>{article.subtitle}</Text>
          )}
          <Text style={s.muted}>
            {article.editor.display_name} / {date(article.published_at)}
          </Text>
          <View style={s.rule} />
          {mediaUrl(article.cover) && (
            <Image
              source={{ uri: mediaUrl(article.cover, "detail") }}
              style={{
                width: "100%",
                aspectRatio:
                  (article.cover?.width ?? 4) / (article.cover?.height ?? 3),
              }}
            />
          )}
          {article.focus_type === "event" && article.event && (
            <EventInfo event={article.event} />
          )}
          <ArticleBody document={article.document} media={article.media} />
          {article.place && <PlaceInfo place={article.place} />}
          <Text style={s.muted}>
            {article.tags.map((tag) => `#${tag.name}`).join("  ")}
          </Text>
          <ContentActions
            kind="editorials"
            id={id}
            versionId={article.revision_id}
            reactions={article.reactions}
          />
        </>
      )}
    </Screen>
  );
}
