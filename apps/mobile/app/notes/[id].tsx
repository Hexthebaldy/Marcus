import { Image, Pressable, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { mediaUrl, type Note } from "@marcus/api-client";
import { api, useSession } from "../../src/session";
import { Screen, Busy, styles as s, c, ErrorMessage, date } from "../../src/ui";
import { PlaceInfo, EventInfo } from "../../src/place-info";
import { ContentActions } from "../../src/content-actions";
export default function NoteDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user } = useSession();
  const query = useQuery({
    queryKey: ["notes", id],
    queryFn: () => api.get<Note>(`/notes/${id}`),
    refetchInterval: 240_000,
  });
  const note = query.data;
  return (
    <Screen>
      <ErrorMessage error={query.error} />
      {query.isLoading && <Busy />}
      {note && (
        <>
          <View style={{ ...s.row, justifyContent: "space-between" }}>
            <Text style={s.muted}>
              {note.author.display_name} · {date(note.published_at)}
            </Text>
            {note.author.id === user?.id && (
              <Pressable
                onPress={() =>
                  router.push({ pathname: "/notes/edit", params: { id } })
                }
              >
                <Text style={{ color: c.green }}>编辑</Text>
              </Pressable>
            )}
          </View>
          {note.images.map((image) => (
            <Image
              key={image.id}
              source={{ uri: mediaUrl(image, "detail") }}
              style={{
                width: "100%",
                aspectRatio: (image.width ?? 1) / (image.height ?? 1),
                borderRadius: 5,
              }}
              resizeMode="contain"
            />
          ))}
          {!!note.title && <Text style={s.title}>{note.title}</Text>}
          {!!note.body_text && (
            <Text selectable style={s.body}>
              {note.body_text}
            </Text>
          )}
          {note.event && <EventInfo event={note.event} />}
          {note.place && <PlaceInfo place={note.place} />}
          <ContentActions
            kind="notes"
            id={id}
            versionId={note.published_submission_id}
            reactions={note.reactions}
            authorId={note.author.id !== user?.id ? note.author.id : undefined}
            onBlocked={() => router.back()}
          />
        </>
      )}
    </Screen>
  );
}
