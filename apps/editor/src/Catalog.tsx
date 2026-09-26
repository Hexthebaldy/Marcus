import { useEffect, useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { mediaUrl, type MediaAsset, type Page } from "@marcus/api-client";
import { allChoices } from "./Articles";
import { api, uploadMedia } from "./api";
import {
  dateText,
  Empty,
  ErrorBox,
  Field,
  PageHeading,
  Status,
  useDistricts,
  useSession,
} from "./shared";
type Kind = "places" | "events" | "tags";
interface CatalogRow {
  id: string;
  name?: string;
  title?: string;
  status?: string;
  enabled?: boolean;
  version: number;
  district?: { id: string; name: string };
  district_id?: string;
  address?: string;
  gallery?: MediaAsset[];
  cover_asset_id?: string | null;
  price_min_fen?: number | null;
  price_max_fen?: number | null;
  [key: string]: unknown;
}
interface Session {
  id: string;
  starts_at: string;
  ends_at: string;
  entry_note: string;
  status: string;
  version: number;
}
type Values = Record<string, string | boolean>;
const kindNames = { places: "地点", events: "活动", tags: "标签" };
const initial = (kind: Kind): Values =>
  kind === "places"
    ? {
        name: "",
        district_id: "",
        address: "",
        summary: "",
        opening_hours_text: "",
        transport_notes: "",
        latitude: "",
        longitude: "",
        source_url: "",
        status: "draft",
        confirm_verified: false,
      }
    : kind === "events"
      ? {
          title: "",
          description: "",
          organizer: "",
          booking_url: "",
          source_url: "",
          place_id: "",
          price_status: "unknown",
          price_min_yuan: "",
          price_max_yuan: "",
          status: "draft",
          confirm_verified: false,
        }
      : { slug: "", name: "", category: "general", enabled: true };
export function Catalog({ kind }: { kind: Kind }) {
  const { city } = useSession();
  const client = useQueryClient();
  const [cursor, setCursor] = useState<string>();
  const [selected, setSelected] = useState<string | null>(null);
  const [values, setValues] = useState<Values>(initial(kind));
  const [version, setVersion] = useState(1);
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [images, setImages] = useState<MediaAsset[]>([]);
  const [coverId, setCoverId] = useState<string | null>(null);
  const districts = useDistricts(city.id);
  const query = useQuery({
    queryKey: ["catalog", kind, cursor],
    queryFn: () =>
      api.get<Page<CatalogRow>>(`/admin/${kind}`, {
        city_id: kind === "tags" ? undefined : city.id,
        cursor,
      }),
  });
  const places = useQuery({
    queryKey: ["place-choices", city.id],
    queryFn: () => allChoices("places", city.id),
    enabled: kind === "events",
  });
  useEffect(() => {
    setSelected(null);
    setCursor(undefined);
    setError(undefined);
    setNotice("");
  }, [kind]);
  const edit = async (id: string) => {
    setError(undefined);
    setNotice("");
    setSelected(id);
    if (id === "new") {
      setValues(initial(kind));
      setImages([]);
      setCoverId(null);
      setVersion(1);
      return;
    }
    try {
      const item =
        kind === "tags"
          ? query.data?.items.find((row) => row.id === id)
          : await api.get<CatalogRow>(`/admin/${kind}/${id}`);
      if (!item) return;
      const next = initial(kind);
      for (const key of Object.keys(next)) {
        const value = item[key];
        if (typeof value === "string" || typeof value === "boolean")
          next[key] = value;
        else if (typeof value === "number") next[key] = String(value);
      }
      if (kind === "places") {
        setImages(item.gallery ?? []);
        setCoverId(item.cover_asset_id ?? null);
      }
      if (kind === "events") {
        next.price_min_yuan = String((item.price_min_fen ?? 0) / 100);
        next.price_max_yuan = String((item.price_max_fen ?? 0) / 100);
      }
      setVersion(item.version);
      setValues(next);
    } catch (err) {
      setError(err);
    }
  };
  const save = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(undefined);
    try {
      const payload: Record<string, unknown> = { ...values };
      if (kind === "places") {
        payload.latitude =
          values.latitude === "" ? null : Number(values.latitude);
        payload.longitude =
          values.longitude === "" ? null : Number(values.longitude);
        payload.cover_asset_id = coverId;
        payload.source_url = values.source_url || null;
      }
      if (kind === "events") {
        payload.place_id = values.place_id || null;
        payload.organizer = values.organizer || null;
        payload.booking_url = values.booking_url || null;
        payload.source_url = values.source_url || null;
        payload.price_min_fen =
          values.price_status === "unknown"
            ? null
            : values.price_status === "free"
              ? 0
              : Math.round(Number(values.price_min_yuan) * 100);
        payload.price_max_fen =
          values.price_status === "unknown"
            ? null
            : values.price_status === "free"
              ? 0
              : Math.round(Number(values.price_max_yuan) * 100);
        delete payload.price_min_yuan;
        delete payload.price_max_yuan;
      }
      if (selected === "new") {
        if (kind !== "tags") payload.city_id = city.id;
        const created = await api.post<CatalogRow>(`/admin/${kind}`, payload);
        setSelected(created.id);
        setVersion(created.version);
        if (kind === "places" && images.length) {
          const updated = await api.put<CatalogRow>(
            `/admin/places/${created.id}/images`,
            {
              expected_version: created.version,
              asset_ids: images.map((image) => image.id),
            },
          );
          setVersion(updated.version);
        }
      } else {
        if (kind === "tags") delete payload.slug;
        else payload.expected_version = version;
        const updated = await api.patch<CatalogRow>(
          `/admin/${kind}/${selected}`,
          payload,
        );
        setVersion(updated.version);
        if (kind === "places") {
          const withImages = await api.put<CatalogRow>(
            `/admin/places/${selected}/images`,
            {
              expected_version: updated.version,
              asset_ids: images.map((image) => image.id),
            },
          );
          setVersion(withImages.version);
        }
      }
      await client.invalidateQueries({ queryKey: ["catalog", kind] });
      await client.invalidateQueries({
        queryKey: [
          kind === "places"
            ? "place-choices"
            : kind === "events"
              ? "event-choices"
              : "tag-choices",
        ],
      });
      setNotice("资料已保存。");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };
  const field = (
    key: string,
    label: string,
    options: {
      multiline?: boolean;
      required?: boolean;
      type?: string;
      max?: number;
    } = {},
  ) => (
    <Field label={label} key={key}>
      {options.multiline ? (
        <textarea
          rows={key === "description" ? 8 : 3}
          value={String(values[key] ?? "")}
          maxLength={options.max}
          required={options.required}
          onChange={(event) =>
            setValues((current) => ({ ...current, [key]: event.target.value }))
          }
        />
      ) : (
        <input
          type={options.type ?? "text"}
          value={String(values[key] ?? "")}
          maxLength={options.max}
          step={options.type === "number" ? "any" : undefined}
          required={options.required}
          onChange={(event) =>
            setValues((current) => ({ ...current, [key]: event.target.value }))
          }
        />
      )}
    </Field>
  );
  const select = (
    key: string,
    label: string,
    choices: [string, string][],
    required = false,
  ) => (
    <Field label={label}>
      <select
        required={required}
        value={String(values[key])}
        onChange={(event) =>
          setValues((current) => ({ ...current, [key]: event.target.value }))
        }
      >
        {choices.map(([value, text]) => (
          <option key={value} value={value}>
            {text}
          </option>
        ))}
      </select>
    </Field>
  );
  return (
    <>
      <PageHeading
        eyebrow={`CITY ATLAS / ${kind.toUpperCase()}`}
        title={`${kindNames[kind]}资料`}
      >
        <button className="primary" onClick={() => void edit("new")}>
          ＋ 新建{kindNames[kind]}
        </button>
      </PageHeading>
      <ErrorBox error={error ?? query.error} />
      {notice && <p className="notice">{notice}</p>}
      <div className={`catalog-layout ${selected ? "with-detail" : ""}`}>
        <section>
          <div className="data-list">
            {query.data?.items.map((item) => (
              <button
                className={`data-row ${selected === item.id ? "selected" : ""}`}
                key={item.id}
                onClick={() => void edit(item.id)}
              >
                <div>
                  <strong>{item.name ?? item.title}</strong>
                  <small>
                    {item.district?.name ??
                      (kind === "tags"
                        ? String(item.category ?? "")
                        : (item.address ?? ""))}
                  </small>
                </div>
                <Status
                  value={
                    kind === "tags"
                      ? item.enabled
                        ? "active"
                        : "closed"
                      : item.status
                  }
                />
              </button>
            ))}
          </div>
          {!query.isPending && !query.data?.items.length && (
            <Empty>还没有{kindNames[kind]}资料。</Empty>
          )}
          <div className="pagination">
            <button disabled={!cursor} onClick={() => setCursor(undefined)}>
              第一页
            </button>
            <button
              disabled={!query.data?.next_cursor}
              onClick={() => setCursor(query.data?.next_cursor ?? undefined)}
            >
              下一页
            </button>
          </div>
        </section>
        {selected && (
          <section className="panel catalog-form">
            <div className="inline between">
              <h2>
                {selected === "new" ? "新建" : "编辑"}
                {kindNames[kind]}
              </h2>
              <button onClick={() => setSelected(null)}>关闭</button>
            </div>
            <form onSubmit={save}>
              {kind === "places" ? (
                <>
                  {field("name", "地点名称", { required: true, max: 200 })}
                  {select(
                    "district_id",
                    "所在区",
                    [
                      ["", "请选择"],
                      ...(districts.data?.map(
                        (item) => [item.id, item.name] as [string, string],
                      ) ?? []),
                    ],
                    true,
                  )}
                  {field("address", "详细地址", {
                    required: values.status !== "draft",
                    max: 500,
                  })}
                  {field("summary", "地点介绍", { multiline: true, max: 500 })}
                  {field("opening_hours_text", "营业时间", {
                    multiline: true,
                    max: 1000,
                  })}
                  {field("transport_notes", "交通与入口", {
                    multiline: true,
                    max: 1000,
                  })}
                  <div className="two-fields">
                    {field("latitude", "纬度（可选）", { type: "number" })}
                    {field("longitude", "经度（可选）", { type: "number" })}
                  </div>
                  {select("status", "公开状态", [
                    ["draft", "草稿"],
                    ["active", "公开"],
                    ["closed", "已关闭"],
                  ])}
                  <Field label="地点图片（可选）">
                    <input
                      type="file"
                      multiple
                      accept="image/jpeg,image/png,image/webp"
                      disabled={busy}
                      onChange={async (event) => {
                        const files = Array.from(event.target.files ?? []);
                        if (files.length + images.length > 20) {
                          setError(new Error("最多20张地点图片。"));
                          return;
                        }
                        setBusy(true);
                        try {
                          for (const file of files) {
                            const asset = await uploadMedia(
                              file,
                              "place_image",
                            );
                            setImages((current) => [...current, asset]);
                          }
                        } catch (err) {
                          setError(err);
                        } finally {
                          setBusy(false);
                        }
                      }}
                    />
                  </Field>
                  <div className="image-strip">
                    {images.map((image, index) => (
                      <figure key={image.id}>
                        <img src={mediaUrl(image)} alt="地点图片" />
                        <div className="inline">
                          <button
                            type="button"
                            disabled={index === 0}
                            onClick={() =>
                              setImages((current) => {
                                const next = [...current];
                                [next[index - 1], next[index]] = [
                                  next[index]!,
                                  next[index - 1]!,
                                ];
                                return next;
                              })
                            }
                          >
                            前移
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setImages((current) =>
                                current.filter(
                                  (asset) => asset.id !== image.id,
                                ),
                              );
                              if (coverId === image.id) setCoverId(null);
                            }}
                          >
                            移除
                          </button>
                        </div>
                        <button
                          type="button"
                          aria-pressed={coverId === image.id}
                          onClick={() =>
                            setCoverId(coverId === image.id ? null : image.id)
                          }
                        >
                          {coverId === image.id ? "取消封面" : "设为封面"}
                        </button>
                      </figure>
                    ))}
                  </div>
                </>
              ) : kind === "events" ? (
                <>
                  {field("title", "活动名称", { required: true, max: 200 })}
                  {field("description", "活动介绍", {
                    multiline: true,
                    max: 20000,
                  })}
                  {field("organizer", "主办方", { max: 200 })}
                  {select("place_id", "举办地点", [
                    ["", "场地待确认"],
                    ...(places.data?.map(
                      (item) => [item.id, item.name ?? ""] as [string, string],
                    ) ?? []),
                  ])}
                  {select("price_status", "费用", [
                    ["unknown", "尚未确认"],
                    ["free", "免费"],
                    ["known", "已知票价"],
                  ])}
                  {values.price_status === "known" && (
                    <div className="two-fields">
                      {field("price_min_yuan", "最低价格（元）", {
                        type: "number",
                        required: true,
                      })}
                      {field("price_max_yuan", "最高价格（元）", {
                        type: "number",
                        required: true,
                      })}
                    </div>
                  )}
                  {field("booking_url", "预约 / 购票链接", {
                    type: "url",
                    max: 2048,
                  })}
                  {select("status", "活动状态", [
                    ["draft", "草稿"],
                    ["published", "公开"],
                    ["cancelled", "已取消"],
                    ["ended", "已结束"],
                  ])}
                </>
              ) : (
                <>
                  {selected === "new" &&
                    field("slug", "英文标识（字母、数字、下划线或短横线）", {
                      required: true,
                      max: 64,
                    })}
                  {field("name", "标签名称", { required: true, max: 40 })}
                  {field("category", "分类", { required: true, max: 30 })}
                  <label className="checkbox">
                    <input
                      type="checkbox"
                      checked={Boolean(values.enabled)}
                      onChange={(event) =>
                        setValues((current) => ({
                          ...current,
                          enabled: event.target.checked,
                        }))
                      }
                    />
                    允许新文章使用此标签
                  </label>
                </>
              )}
              {kind !== "tags" && (
                <>
                  {field("source_url", "资料来源链接（可选）", {
                    type: "url",
                    max: 2048,
                  })}
                  <label className="checkbox">
                    <input
                      type="checkbox"
                      checked={Boolean(values.confirm_verified)}
                      onChange={(event) =>
                        setValues((current) => ({
                          ...current,
                          confirm_verified: event.target.checked,
                        }))
                      }
                    />
                    已核实本次地点 / 活动资料
                  </label>
                </>
              )}
              <button className="primary" disabled={busy}>
                {busy ? "处理中…" : "保存资料"}
              </button>
            </form>
            {kind === "events" && selected !== "new" && (
              <Sessions eventId={selected} />
            )}
          </section>
        )}
      </div>
    </>
  );
}
function Sessions({ eventId }: { eventId: string }) {
  const client = useQueryClient();
  const [cursor, setCursor] = useState<string>();
  const [selected, setSelected] = useState<Session>();
  const [starts, setStarts] = useState("");
  const [ends, setEnds] = useState("");
  const [note, setNote] = useState("");
  const [status, setStatus] = useState("scheduled");
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const query = useQuery({
    queryKey: ["sessions", eventId, cursor],
    queryFn: () =>
      api.get<Page<Session>>(`/admin/events/${eventId}/sessions`, { cursor }),
  });
  useEffect(() => {
    setSelected(undefined);
    setStarts("");
    setEnds("");
    setNote("");
    setStatus("scheduled");
    setCursor(undefined);
  }, [eventId]);
  const localValue = (value: string) => {
    const date = new Date(value);
    return new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
      .toISOString()
      .slice(0, 16);
  };
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(undefined);
    try {
      const body = {
        starts_at: new Date(starts).toISOString(),
        ends_at: new Date(ends).toISOString(),
        entry_note: note,
        status,
      };
      if (selected)
        await api.patch(`/admin/events/${eventId}/sessions/${selected.id}`, {
          ...body,
          expected_version: selected.version,
        });
      else await api.post(`/admin/events/${eventId}/sessions`, body);
      await client.invalidateQueries({ queryKey: ["sessions", eventId] });
      setSelected(undefined);
      setStarts("");
      setEnds("");
      setNote("");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="session-editor">
      <h3>活动场次</h3>
      <ErrorBox error={error ?? query.error} />
      {query.data?.items.map((session) => (
        <button
          className="data-row"
          key={session.id}
          onClick={() => {
            setSelected(session);
            setStarts(localValue(session.starts_at));
            setEnds(localValue(session.ends_at));
            setNote(session.entry_note);
            setStatus(session.status);
          }}
        >
          <div>
            <strong>{dateText(session.starts_at)}</strong>
            <small>{session.entry_note}</small>
          </div>
          <Status value={session.status} />
        </button>
      ))}
      {query.data?.next_cursor && (
        <button onClick={() => setCursor(query.data?.next_cursor ?? undefined)}>
          更多场次
        </button>
      )}
      <form onSubmit={submit}>
        <Field label="开始时间（当前电脑时区）">
          <input
            type="datetime-local"
            value={starts}
            required
            onChange={(event) => setStarts(event.target.value)}
          />
        </Field>
        <Field label="结束时间">
          <input
            type="datetime-local"
            value={ends}
            required
            onChange={(event) => setEnds(event.target.value)}
          />
        </Field>
        <Field label="入场说明">
          <input
            value={note}
            maxLength={500}
            onChange={(event) => setNote(event.target.value)}
          />
        </Field>
        <Field label="场次状态">
          <select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="scheduled">正常</option>
            <option value="cancelled">已取消</option>
            <option value="sold_out">售罄</option>
          </select>
        </Field>
        <div className="inline">
          <button disabled={busy}>{selected ? "保存场次" : "添加场次"}</button>
          {selected && (
            <button
              type="button"
              onClick={() => {
                setSelected(undefined);
                setStarts("");
                setEnds("");
                setNote("");
              }}
            >
              取消编辑
            </button>
          )}
        </div>
      </form>
    </section>
  );
}
