import { useEffect, useRef, useState } from "react";
import { Alert, Image, Pressable, Text, View } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Crypto from "expo-crypto";
import { router, useLocalSearchParams } from "expo-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  mediaUrl,
  type City,
  type CityEvent,
  type MediaAsset,
  type NoteDraft,
  type Page,
  type Place,
  type Publication,
} from "@marcus/api-client";
import { api, useSession } from "../../src/session";
import { pickAndUpload } from "../../src/upload";
import {
  Screen,
  styles as s,
  Button,
  Field,
  ErrorMessage,
  Busy,
  c,
} from "../../src/ui";
type Fields = Pick<
  NoteDraft,
  "title" | "body_text" | "image_ids" | "place_id" | "event_id"
>;
type Local = {
  fields: Fields;
  version: number;
  savedAt: number;
  createKey: string;
  publishKey?: string;
  publishVersion?: number;
};
const blank: Fields = {
  title: "",
  body_text: "",
  image_ids: [],
  place_id: null,
  event_id: null,
};
export default function NoteEdit() {
  const params = useLocalSearchParams<{ id?: string }>();
  const { user } = useSession();
  const qc = useQueryClient();
  const [id, setId] = useState(params.id);
  const [fields, setFields] = useState<Fields>(blank);
  const [version, setVersion] = useState(1);
  const [ready, setReady] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const [notice, setNotice] = useState("");
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [choose, setChoose] = useState<"places" | "events" | null>(null);
  const [search, setSearch] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const createKey = useRef(Crypto.randomUUID());
  const publish = useRef<{ version: number; key: string } | null>(null);
  const localKey = `marcus.draft.${user!.id}.${id ?? "new"}`;
  const cities = useQuery({
    queryKey: ["cities"],
    queryFn: () => api.get<Page<City>>("/cities"),
  });
  const city = cities.data?.items[0];
  useEffect(() => {
    const timer = setTimeout(() => setSearchQuery(search), 350);
    return () => clearTimeout(timer);
  }, [search]);
  const choices = useQuery({
    queryKey: ["note-association", choose, city?.id, searchQuery],
    queryFn: () =>
      api.get<Page<Place | CityEvent>>(`/${choose}`, {
        city_id: city!.id,
        q: searchQuery,
        limit: 20,
      }),
    enabled: !!choose && !!city,
  });
  const publication = useQuery({
    queryKey: ["note-publication", id],
    queryFn: () => api.get<Publication>(`/notes/${id}/publication`),
    enabled: !!id && ready,
    refetchInterval: (query) =>
      query.state.data?.review_status === "pending" ? 4000 : false,
  });
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const stored = await AsyncStorage.getItem(
          `marcus.draft.${user!.id}.${params.id ?? "new"}`,
        );
        const local: Local | null = stored ? JSON.parse(stored) : null;
        const remote = params.id
          ? await api.get<NoteDraft>(`/notes/${params.id}/draft`)
          : null;
        if (cancelled) return;
        if (local) {
          setFields(local.fields);
          setVersion(local.version);
          setDirty(true);
          createKey.current = local.createKey;
          if (local.publishKey && local.publishVersion)
            publish.current = {
              version: local.publishVersion,
              key: local.publishKey,
            };
          setNotice(
            remote && local.version !== remote.edit_version
              ? "已恢复本机内容，但服务器已有新版本。请保留本机文字并选择重新读取，不会自动覆盖。"
              : "已恢复本机未提交内容。",
          );
        } else if (remote) {
          setFields({
            title: remote.title,
            body_text: remote.body_text,
            image_ids: remote.image_ids,
            place_id: remote.place_id,
            event_id: remote.event_id,
          });
          setVersion(remote.edit_version);
        }
      } catch (e) {
        if (!cancelled) setError(e);
      } finally {
        if (!cancelled) setReady(true);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [params.id, user?.id]);
  useEffect(() => {
    if (!ready || !dirty) return;
    const local: Local = {
      fields,
      version,
      savedAt: Date.now(),
      createKey: createKey.current,
      publishKey: publish.current?.key,
      publishVersion: publish.current?.version,
    };
    void AsyncStorage.setItem(localKey, JSON.stringify(local)).catch(setError);
  }, [fields, version, ready, dirty, localKey]);
  useEffect(() => {
    let stopped = false;
    async function loadAssets() {
      try {
        const values = await Promise.all(
          fields.image_ids.map((assetId) =>
            api.get<MediaAsset>(`/media/${assetId}`),
          ),
        );
        if (!stopped) setAssets(values);
      } catch (e) {
        if (!stopped) setError(e);
      }
    }
    if (fields.image_ids.length) void loadAssets();
    else setAssets([]);
    const timer = setInterval(() => {
      if (fields.image_ids.length) void loadAssets();
    }, 10_000);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, [fields.image_ids]);
  function update(patch: Partial<Fields>) {
    setFields((old) => ({ ...old, ...patch }));
    setDirty(true);
    setNotice("修改已保存在本机，点击保存可同步到服务器。");
  }
  async function save() {
    if (!city) throw new Error("城市资料尚未加载，请稍后重试。");
    let target = id;
    if (!target) {
      const result = await api.post<{ note_id: string; edit_version?: number }>(
        "/notes",
        { city_id: city.id },
        { idempotencyKey: createKey.current },
      );
      target = result.note_id;
      setId(target);
      await AsyncStorage.setItem(
        `marcus.draft.${user!.id}.${target}`,
        JSON.stringify({
          fields,
          version,
          createKey: createKey.current,
          savedAt: Date.now(),
        }),
      );
      await AsyncStorage.removeItem(`marcus.draft.${user!.id}.new`);
    }
    if (dirty || !id) {
      const saved = await api.patch<NoteDraft>(`/notes/${target}/draft`, {
        expected_version: version,
        ...fields,
      });
      setVersion(saved.edit_version);
      setFields({
        title: saved.title,
        body_text: saved.body_text,
        image_ids: saved.image_ids,
        place_id: saved.place_id,
        event_id: saved.event_id,
      });
      setDirty(false);
      await AsyncStorage.removeItem(`marcus.draft.${user!.id}.${target}`);
      await qc.invalidateQueries({ queryKey: ["my-library"] });
      return { id: target, version: saved.edit_version };
    }
    return { id: target, version };
  }
  async function action(shouldPublish: boolean) {
    setBusy(true);
    setError(undefined);
    try {
      const saved = await save();
      if (shouldPublish) {
        if (publish.current?.version !== saved.version)
          publish.current = {
            version: saved.version,
            key: Crypto.randomUUID(),
          };
        await api.post(
          `/notes/${saved.id}/publish`,
          { expected_edit_version: saved.version },
          { idempotencyKey: publish.current.key },
        );
        setNotice("已提交审核，通过后会出现在 Notes 中。");
        await qc.invalidateQueries({ queryKey: ["note-publication"] });
      } else setNotice("草稿已保存到服务器。");
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function photos() {
    setBusy(true);
    setError(undefined);
    try {
      const values = await pickAndUpload(
        "note_image",
        9 - fields.image_ids.length,
        setNotice,
      );
      setAssets((old) => [...old, ...values]);
      update({
        image_ids: [...fields.image_ids, ...values.map((asset) => asset.id)],
      });
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  function reorder(index: number, delta: number) {
    const next = [...fields.image_ids];
    [next[index], next[index + delta]] = [next[index + delta], next[index]];
    update({ image_ids: next });
  }
  function reloadRemote() {
    Alert.alert(
      "重新读取服务器草稿？",
      "这会丢弃本机尚未同步的内容。请先复制需要保留的文字。",
      [
        { text: "取消", style: "cancel" },
        {
          text: "读取",
          onPress: () => {
            void api
              .get<NoteDraft>(`/notes/${id}/draft`)
              .then(async (draft) => {
                setFields({
                  title: draft.title,
                  body_text: draft.body_text,
                  image_ids: draft.image_ids,
                  place_id: draft.place_id,
                  event_id: draft.event_id,
                });
                setVersion(draft.edit_version);
                setDirty(false);
                await AsyncStorage.removeItem(localKey);
                setError(undefined);
                setNotice("已读取服务器草稿。");
              })
              .catch(setError);
          },
        },
      ],
    );
  }
  function removeDraft() {
    Alert.alert("删除这篇笔记？", "草稿和已公开的内容都会停止展示。", [
      { text: "取消", style: "cancel" },
      {
        text: "删除",
        style: "destructive",
        onPress: () => {
          setBusy(true);
          void (async () => {
            if (id) {
              const current = await api.get<NoteDraft>(`/notes/${id}/draft`);
              await api.delete(`/notes/${id}`, {
                expected_version: current.version,
              });
            }
            await AsyncStorage.removeItem(localKey);
            await qc.invalidateQueries();
            router.back();
          })()
            .catch(setError)
            .finally(() => setBusy(false));
        },
      },
    ]);
  }
  return (
    <Screen>
      {!ready ? (
        <Busy />
      ) : (
        <>
          <Text style={s.eyebrow}>YOUR CITY, YOUR STORY</Text>
          <Field
            editable={!busy}
            value={fields.title}
            onChangeText={(title) => update({ title })}
            maxLength={100}
            placeholder="标题（选填）"
          />
          <Field
            editable={!busy}
            multiline
            textAlignVertical="top"
            value={fields.body_text}
            onChangeText={(body_text) => update({ body_text })}
            maxLength={5000}
            placeholder="今天看了什么、遇见了什么？记录你的城市体验…"
            style={{ minHeight: 240, lineHeight: 27 }}
          />
          <Text style={s.muted}>
            {fields.body_text.length} / 5000 · {fields.image_ids.length} / 9
            张图片
          </Text>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 12 }}>
            {fields.image_ids.map((assetId, i) => {
              const asset = assets.find((value) => value.id === assetId);
              return (
                <View key={assetId} style={{ width: "46%", gap: 8 }}>
                  {mediaUrl(asset) ? (
                    <Image
                      source={{ uri: mediaUrl(asset) }}
                      style={{ width: "100%", aspectRatio: 1, borderRadius: 8 }}
                    />
                  ) : (
                    <View
                      style={{
                        height: 80,
                        backgroundColor: c.khaki,
                        justifyContent: "center",
                        padding: 10,
                      }}
                    >
                      <Text>
                        {asset?.status === "rejected"
                          ? "处理失败，请移除"
                          : "正在处理图片"}
                      </Text>
                    </View>
                  )}
                  <View style={s.row}>
                    <Pressable
                      disabled={busy || i === 0}
                      onPress={() => reorder(i, -1)}
                    >
                      <Text style={{ color: i ? c.green : c.line }}>←</Text>
                    </Pressable>
                    <Pressable
                      disabled={busy || i === fields.image_ids.length - 1}
                      onPress={() => reorder(i, 1)}
                    >
                      <Text style={{ color: c.green }}>→</Text>
                    </Pressable>
                    <Pressable
                      disabled={busy}
                      onPress={() =>
                        update({
                          image_ids: fields.image_ids.filter(
                            (value) => value !== assetId,
                          ),
                        })
                      }
                    >
                      <Text style={s.muted}>移除</Text>
                    </Pressable>
                  </View>
                </View>
              );
            })}
          </View>
          <Button
            secondary
            title="添加照片"
            disabled={busy || fields.image_ids.length >= 9}
            onPress={() => void photos()}
          />
          <Text style={s.muted}>
            {fields.event_id
              ? "已关联活动"
              : fields.place_id
                ? "已关联地点"
                : "地点与活动可选，不填写也能发布。"}
          </Text>
          <View style={s.row}>
            <Button
              secondary
              title="选择地点"
              disabled={busy}
              onPress={() => setChoose(choose === "places" ? null : "places")}
              style={{ flex: 1 }}
            />
            <Button
              secondary
              title="选择活动"
              disabled={busy}
              onPress={() => setChoose(choose === "events" ? null : "events")}
              style={{ flex: 1 }}
            />
          </View>
          {(fields.place_id || fields.event_id) && (
            <Pressable
              onPress={() => update({ place_id: null, event_id: null })}
            >
              <Text style={s.muted}>清除关联</Text>
            </Pressable>
          )}
          {choose && (
            <View style={s.card}>
              <Field
                placeholder="按名称查找"
                value={search}
                onChangeText={setSearch}
              />
              <ErrorMessage error={choices.error} />
              {choices.isLoading && <Busy />}
              {choices.data?.items.map((item) => (
                <Pressable
                  key={item.id}
                  onPress={() => {
                    update(
                      choose === "places"
                        ? { place_id: item.id, event_id: null }
                        : { event_id: item.id, place_id: null },
                    );
                    setChoose(null);
                  }}
                >
                  <Text style={s.body}>
                    {"name" in item ? item.name : item.title}
                  </Text>
                </Pressable>
              ))}
              {choices.data?.items.length === 0 && (
                <Text style={s.muted}>没有找到相关资料，可以先不关联。</Text>
              )}
            </View>
          )}
          <ErrorMessage error={error} />
          {!!notice && <Text style={s.muted}>{notice}</Text>}
          {publication.data?.review_status && (
            <Text style={s.muted}>
              {publication.data.review_status === "pending"
                ? "最新提交正在审核"
                : publication.data.review_status === "rejected"
                  ? `审核未通过：${publication.data.reason_code ?? "请检查内容"}`
                  : publication.data.is_current_published
                    ? "最新提交已公开"
                    : "提交已审核"}
              。修改草稿不影响已公开的内容。
            </Text>
          )}
          <View style={s.row}>
            <Button
              secondary
              title="保存草稿"
              disabled={busy}
              onPress={() => void action(false)}
              style={{ flex: 1 }}
            />
            <Button
              title="提交发布"
              loading={busy}
              disabled={!fields.body_text.trim() && !fields.image_ids.length}
              onPress={() => void action(true)}
              style={{ flex: 1 }}
            />
          </View>
          {id && (
            <Pressable onPress={reloadRemote}>
              <Text style={s.muted}>重新读取服务器草稿</Text>
            </Pressable>
          )}
          <Pressable disabled={busy} onPress={removeDraft}>
            <Text style={{ color: c.error }}>删除笔记和草稿</Text>
          </Pressable>
        </>
      )}
    </Screen>
  );
}
