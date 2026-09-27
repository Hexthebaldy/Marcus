import { useCallback } from "react";
import { Alert, Pressable, Text, View } from "react-native";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useInfiniteQuery } from "@tanstack/react-query";
import type { Editorial, Note, NoteDraft, Page } from "@marcus/api-client";
import { api } from "../src/session";
import {
  Screen,
  styles as s,
  Empty,
  Busy,
  ErrorMessage,
  Button,
  date,
  c,
} from "../src/ui";
import { EditorialCard, NoteCard } from "../src/cards";
type Bookmark = {
  content_type: "note" | "editorial";
  note?: Note;
  editorial?: Editorial;
  content?: Note | Editorial;
};
export default function Library() {
  const { type = "notes" } = useLocalSearchParams<{ type?: string }>();
  const path =
    type === "drafts"
      ? "/me/note-drafts"
      : type === "bookmarks"
        ? "/me/bookmarks"
        : "/me/notes";
  const query = useInfiniteQuery({
    queryKey: ["my-library", type],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) =>
      api.get<Page<Note | NoteDraft | Bookmark>>(path, { cursor: pageParam }),
    getNextPageParam: (page) => page.next_cursor ?? undefined,
  });
  const items = query.data?.pages.flatMap((page) => page.items) ?? [];
  const { refetch } = query;
  useFocusEffect(
    useCallback(() => {
      void refetch();
    }, [refetch]),
  );
  function remove(note: Note) {
    Alert.alert(
      "删除这篇笔记？",
      "删除后读者将无法访问，也不能通过迟到的审核重新发布。",
      [
        { text: "取消", style: "cancel" },
        {
          text: "删除",
          style: "destructive",
          onPress: () => {
            void api
              .delete(`/notes/${note.id}`, { expected_version: note.version })
              .then(() => query.refetch())
              .catch((e) => Alert.alert("未能删除", e.message));
          },
        },
      ],
    );
  }
  return (
    <Screen>
      <Text style={s.title}>
        {type === "drafts"
          ? "未完待续"
          : type === "bookmarks"
            ? "值得再去"
            : "我的城市笔记"}
      </Text>
      <ErrorMessage error={query.error} />
      {query.isLoading && <Busy />}
      {!query.isLoading && !items.length && (
        <Empty
          title="这里还是空白的一页"
          body="写下体验，或收藏一篇喜欢的内容。"
        />
      )}
      {items.map((item, index) => {
        if (type === "drafts") {
          const draft = item as NoteDraft;
          return (
            <Pressable
              key={draft.note_id}
              style={s.card}
              onPress={() =>
                router.push({
                  pathname: "/notes/edit",
                  params: { id: draft.note_id },
                })
              }
            >
              <Text style={s.heading}>{draft.title || "未命名笔记"}</Text>
              <Text numberOfLines={2} style={s.muted}>
                {draft.body_text}
              </Text>
              <Text style={s.muted}>
                {date(draft.updated_at)} ·{" "}
                {draft.latest_submission?.review_status === "pending"
                  ? "审核中"
                  : draft.latest_submission?.review_status === "rejected"
                    ? "未通过审核"
                    : draft.latest_submission?.review_status === "approved"
                      ? "已通过审核"
                      : "草稿"}
              </Text>
            </Pressable>
          );
        }
        if (type === "bookmarks") {
          const saved = item as Bookmark;
          return saved.content_type === "note" ? (
            <NoteCard
              key={index}
              item={(saved.note ?? saved.content) as Note}
            />
          ) : (
            <EditorialCard
              key={index}
              item={(saved.editorial ?? saved.content) as Editorial}
            />
          );
        }
        const note = item as Note;
        return (
          <View key={note.id}>
            <NoteCard item={note} />
            <View style={{ ...s.row, justifyContent: "flex-end" }}>
              <Pressable
                onPress={() =>
                  router.push({
                    pathname: "/notes/edit",
                    params: { id: note.id },
                  })
                }
              >
                <Text style={{ color: c.green }}>编辑</Text>
              </Pressable>
              <Pressable onPress={() => remove(note)}>
                <Text style={s.muted}>删除</Text>
              </Pressable>
            </View>
          </View>
        );
      })}
      {query.hasNextPage && (
        <Button
          secondary
          title="加载更多"
          loading={query.isFetchingNextPage}
          onPress={() => void query.fetchNextPage()}
        />
      )}
    </Screen>
  );
}
