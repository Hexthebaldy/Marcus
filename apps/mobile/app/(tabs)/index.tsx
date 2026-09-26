import { useState } from "react";
import {
  Pressable,
  RefreshControl,
  ScrollView,
  Text,
  View,
} from "react-native";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import type { City, District, Editorial, Note, Page } from "@marcus/api-client";
import { api } from "../../src/session";
import {
  Screen,
  styles as s,
  c,
  Empty,
  ErrorMessage,
  Busy,
  Button,
} from "../../src/ui";
import { EditorialCard, NoteGrid } from "../../src/cards";
export default function Discover() {
  const [tab, setTab] = useState<"editorials" | "notes">("editorials");
  const [district, setDistrict] = useState<string>();
  const cities = useQuery({
    queryKey: ["cities"],
    queryFn: () => api.get<Page<City>>("/cities"),
  });
  const city = cities.data?.items[0];
  const districts = useQuery({
    queryKey: ["districts", city?.id],
    queryFn: () => api.get<Page<District>>(`/cities/${city!.id}/districts`),
    enabled: !!city,
  });
  const feed = useInfiniteQuery({
    queryKey: [
      "discover",
      tab,
      city?.id,
      tab === "editorials" ? district : undefined,
    ],
    enabled: !!city,
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) =>
      api.get<Page<Editorial | Note>>(`/discover/${tab}`, {
        city_id: city!.id,
        district_id: tab === "editorials" ? district : undefined,
        cursor: pageParam,
        limit: 20,
      }),
    getNextPageParam: (page) => page.next_cursor ?? undefined,
    refetchInterval: 240_000,
  });
  const items = Array.from(
    new Map(
      feed.data?.pages
        .flatMap((page) => page.items)
        .map((item) => [item.id, item]),
    ).values(),
  );
  return (
    <Screen scroll={false}>
      <ScrollView
        contentContainerStyle={{ padding: 22, paddingBottom: 100 }}
        refreshControl={
          <RefreshControl
            tintColor={c.green}
            refreshing={feed.isRefetching}
            onRefresh={() => void feed.refetch()}
          />
        }
        onScroll={({
          nativeEvent: { layoutMeasurement, contentOffset, contentSize },
        }) => {
          if (
            layoutMeasurement.height + contentOffset.y >=
              contentSize.height - 500 &&
            feed.hasNextPage &&
            !feed.isFetching
          )
            void feed.fetchNextPage();
        }}
        scrollEventThrottle={200}
      >
        <View
          style={{
            ...s.row,
            justifyContent: "space-between",
            marginBottom: 30,
          }}
        >
          <Text
            style={{
              fontSize: 33,
              letterSpacing: -2,
              fontWeight: "800",
              color: c.green,
            }}
          >
            marcus.
          </Text>
          <Text style={s.muted}>{city?.name ?? "上海"} ↗</Text>
        </View>
        <Text style={s.eyebrow}>THE CITY IS YOURS</Text>
        <Text style={{ ...s.title, marginTop: 9, marginBottom: 26 }}>
          日常之外，城市之中。
        </Text>
        <View style={{ ...s.row, gap: 27, marginBottom: 18 }}>
          {(["editorials", "notes"] as const).map((value) => (
            <Pressable
              key={value}
              onPress={() => setTab(value)}
              accessibilityRole="tab"
              accessibilityState={{ selected: tab === value }}
              style={{
                paddingVertical: 8,
                borderBottomWidth: 3,
                borderColor: tab === value ? c.green : "transparent",
              }}
            >
              <Text
                style={{
                  fontSize: 20,
                  fontWeight: tab === value ? "700" : "400",
                  color: tab === value ? c.green : c.muted,
                }}
              >
                {value === "editorials" ? "活动" : "Notes"}
              </Text>
            </Pressable>
          ))}
        </View>
        {tab === "editorials" && (
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            style={{ marginBottom: 24 }}
          >
            <View style={s.row}>
              {[
                { id: "", name: "全上海" },
                ...(districts.data?.items ?? []),
              ].map((item) => (
                <Pressable
                  key={item.id}
                  onPress={() => setDistrict(item.id || undefined)}
                  style={{
                    paddingHorizontal: 14,
                    paddingVertical: 9,
                    backgroundColor:
                      (district ?? "") === item.id ? c.green : c.khaki,
                    borderRadius: 30,
                  }}
                >
                  <Text
                    style={{
                      fontSize: 12,
                      color: (district ?? "") === item.id ? c.paper : c.green,
                    }}
                  >
                    {item.name}
                  </Text>
                </Pressable>
              ))}
            </View>
          </ScrollView>
        )}
        <ErrorMessage error={cities.error || feed.error || districts.error} />
        {feed.isLoading || cities.isLoading ? (
          <Busy />
        ) : items.length === 0 ? (
          <Empty
            title="好内容，值得等待"
            body={
              tab === "notes"
                ? "写下你的第一篇城市笔记，让探索从这里开始。"
                : "编辑正在寻找这座城市的新鲜去处。稍后回来看看。"
            }
          />
        ) : tab === "notes" ? (
          <NoteGrid items={items as Note[]} />
        ) : (
          (items as Editorial[]).map((item, index) => (
            <EditorialCard key={item.id} item={item} index={index} />
          ))
        )}
        {feed.hasNextPage && (
          <Button
            secondary
            title="继续发现"
            loading={feed.isFetchingNextPage}
            onPress={() => void feed.fetchNextPage()}
          />
        )}
      </ScrollView>
      <Pressable
        accessibilityLabel="发布笔记"
        accessibilityRole="button"
        onPress={() => router.push("/notes/edit")}
        style={{
          position: "absolute",
          right: 22,
          bottom: 22,
          width: 56,
          height: 56,
          borderRadius: 28,
          backgroundColor: c.green,
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <Ionicons name="add" size={28} color={c.paper} />
      </Pressable>
    </Screen>
  );
}
