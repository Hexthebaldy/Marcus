import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { uuid, type MediaAsset, type Page } from "@marcus/api-client";
import {
  EditorialEditor,
  EditorialPreview,
  type EditorialMedia,
} from "@marcus/editorial-editor";
import {
  validateDocument,
  type EditorialDocument,
} from "@marcus/editorial-schema";
import { api, asEditorMedia, uploadMedia } from "./api";
import {
  dateText,
  Empty,
  ErrorBox,
  Field,
  PageHeading,
  Status,
  statusName,
  useDistricts,
  useSession,
} from "./shared";
export interface Choice {
  id: string;
  name?: string;
  title?: string;
  status?: string;
  enabled?: boolean;
}
interface ArticleSummary {
  id: string;
  title: string;
  status: string;
  district?: { name: string };
  updated_at: string;
  editorial_rank: number;
  version: number;
}
interface Draft {
  article_id: string;
  title: string;
  subtitle: string;
  summary: string;
  focus_type: "place" | "event" | null;
  primary_place_id: string | null;
  primary_event_id: string | null;
  document: EditorialDocument;
  document_schema_version: number;
  cover_asset_id: string | null;
  tag_ids: string[];
  edit_version: number;
  media: MediaAsset[];
  latest_submission?: { review_status: string; reason_code?: string };
}
interface Publication {
  review_status: string;
  is_current_published: boolean;
  reason_code?: string;
}
export function ArticleList() {
  const { city } = useSession();
  const navigate = useNavigate();
  const [district, setDistrict] = useState("");
  const [cursor, setCursor] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const districts = useDistricts(city.id);
  const createKey = useRef(uuid());
  const query = useQuery({
    queryKey: ["articles", city.id, district, cursor],
    queryFn: () =>
      api.get<Page<ArticleSummary>>("/admin/editorials", {
        city_id: city.id,
        district_id: district || undefined,
        cursor,
      }),
  });
  const create = async () => {
    setBusy(true);
    setError(undefined);
    try {
      const article = await api.post<Draft>(
        "/admin/editorials",
        { city_id: city.id, ...(district ? { district_id: district } : {}) },
        { idempotencyKey: createKey.current },
      );
      createKey.current = uuid();
      navigate(`/articles/${article.article_id}`);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <PageHeading eyebrow="THE EDITORIAL DESK" title="让城市值得被看见">
        <button
          className="primary"
          onClick={() => void create()}
          disabled={busy}
        >
          ＋ 新建文章
        </button>
      </PageHeading>
      <div className="section-intro">
        <p>
          一个地方，一种性格。
          <br />
          一次活动，一段值得出发的体验。
        </p>
        <span>
          SHANGHAI
          <br />
          EDITORIAL COLLECTION
        </span>
      </div>
      <div className="filters">
        <select
          aria-label="按区筛选"
          value={district}
          onChange={(event) => {
            setDistrict(event.target.value);
            setCursor(undefined);
          }}
        >
          <option value="">上海 · 全部区域</option>
          {districts.data?.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
        <button
          onClick={() => {
            setCursor(undefined);
            void query.refetch();
          }}
        >
          刷新列表
        </button>
      </div>
      <ErrorBox error={error ?? query.error} />
      <div className="article-grid">
        {query.data?.items.map((article, index) => (
          <Link
            to={`/articles/${article.id}`}
            className="article-card"
            key={article.id}
          >
            <div className="article-number">
              {String(index + 1).padStart(2, "0")}
              <Status value={article.status} />
            </div>
            <h2>{article.title || "未命名文章"}</h2>
            <p>{article.district?.name ?? "区域待确认"}</p>
            <footer>
              <span>{dateText(article.updated_at)}</span>
              <span>打开文章 ↗</span>
            </footer>
          </Link>
        ))}
      </div>
      {!query.isPending && !query.data?.items.length && (
        <Empty>还没有文章，从一个喜欢的地方开始。</Empty>
      )}
      <div className="pagination">
        <button disabled={!cursor} onClick={() => setCursor(undefined)}>
          回到第一页
        </button>
        <button
          disabled={!query.data?.next_cursor}
          onClick={() => setCursor(query.data?.next_cursor ?? undefined)}
        >
          下一页
        </button>
      </div>
    </>
  );
}
export function ArticleEditor() {
  const { id = "" } = useParams();
  const { city, user } = useSession();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<Draft>();
  const [media, setMedia] = useState<EditorialMedia[]>([]);
  const [error, setError] = useState<unknown>();
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [preview, setPreview] = useState(false);
  const [phone, setPhone] = useState(true);
  const publishKey = useRef<{ version: number; key: string } | undefined>(
    undefined,
  );
  const query = useQuery({
    queryKey: ["editorial-draft", id],
    queryFn: () => api.get<Draft>(`/admin/editorials/${id}/draft`),
  });
  const places = useQuery({
    queryKey: ["place-choices", city.id],
    queryFn: () => allChoices("places", city.id),
  });
  const events = useQuery({
    queryKey: ["event-choices", city.id],
    queryFn: () => allChoices("events", city.id),
  });
  const tags = useQuery({
    queryKey: ["tag-choices"],
    queryFn: () => allChoices("tags", city.id),
  });
  const publication = useQuery({
    queryKey: ["editorial-publication", id],
    queryFn: () => api.get<Publication>(`/admin/editorials/${id}/publication`),
    enabled: Boolean(draft),
    refetchInterval: (query) =>
      query.state.data?.review_status === "pending" ? 5000 : false,
  });
  useEffect(() => {
    setDraft(undefined);
    setDirty(false);
    setMedia([]);
    setError(undefined);
  }, [id]);
  useEffect(() => {
    if (query.data && !draft) {
      setDraft(query.data);
      setMedia(query.data.media.map(asEditorMedia));
    }
  }, [query.data, draft]);
  useEffect(() => {
    const beforeUnload = (event: BeforeUnloadEvent) => {
      if (dirty) {
        event.preventDefault();
        event.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", beforeUnload);
    return () => window.removeEventListener("beforeunload", beforeUnload);
  }, [dirty]);
  const change = (patch: Partial<Draft>) => {
    setDraft((current) => (current ? { ...current, ...patch } : current));
    setDirty(true);
    setNotice("");
  };
  const upload = async (file: File) => {
    setBusy(true);
    try {
      const asset = asEditorMedia(await uploadMedia(file));
      setMedia((current) => [
        ...current.filter((item) => item.id !== asset.id),
        asset,
      ]);
      return asset;
    } finally {
      setBusy(false);
    }
  };
  const save = async (draft: Draft): Promise<Draft> => {
    const saved = await api.patch<Draft>(`/admin/editorials/${id}/draft`, {
      expected_version: draft.edit_version,
      title: draft.title,
      subtitle: draft.subtitle,
      summary: draft.summary,
      focus_type: draft.focus_type,
      primary_place_id: draft.primary_place_id,
      primary_event_id: draft.primary_event_id,
      document: draft.document,
      document_schema_version: 1,
      cover_asset_id: draft.cover_asset_id,
      tag_ids: draft.tag_ids,
    });
    setDraft(saved);
    setDirty(false);
    void queryClient.invalidateQueries({ queryKey: ["articles"] });
    return saved;
  };
  const runSave = async (submit = false) => {
    setBusy(true);
    setError(undefined);
    setNotice("");
    try {
      if (!draft) return;
      const problems = validateDocument(draft.document, submit);
      if (submit) {
        if (!draft.title.trim()) problems.push("请填写文章标题。");
        if (
          !draft.focus_type ||
          !(draft.primary_place_id || draft.primary_event_id)
        )
          problems.push("请选择文章重心和一个主要对象。");
      }
      if (problems.length) throw new Error(problems.join("\n"));
      const saved = dirty ? await save(draft) : draft;
      if (submit) {
        if (publishKey.current?.version !== saved.edit_version)
          publishKey.current = { version: saved.edit_version, key: uuid() };
        await api.post(
          `/admin/editorials/${id}/publish`,
          { expected_edit_version: saved.edit_version },
          { idempotencyKey: publishKey.current.key },
        );
        await publication.refetch();
        setNotice("已提交审核。审核通过前，原有公开内容保持不变。");
      } else setNotice("草稿已保存。");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };
  if (!draft)
    return (
      <>
        <p>正在加载文章…</p>
        <ErrorBox error={query.error} />
      </>
    );
  const choices = draft.focus_type === "event" ? events.data : places.data;
  return (
    <>
      <PageHeading eyebrow="EDITORIAL / WORKING DRAFT" title="文章编辑">
        <div className="inline">
          <Link
            to="/articles"
            onClick={(event) => {
              if (dirty && !window.confirm("有尚未保存的修改，仍要离开吗？"))
                event.preventDefault();
            }}
          >
            返回列表
          </Link>
          <button onClick={() => setPreview((value) => !value)}>
            {preview ? "继续编辑" : "阅读预览"}
          </button>
          <button disabled={busy} onClick={() => void runSave()}>
            保存草稿
          </button>
          <button
            className="primary"
            disabled={busy}
            onClick={() => void runSave(true)}
          >
            提交审核 ↗
          </button>
        </div>
      </PageHeading>
      <div className="draft-state">
        <span>
          {dirty
            ? "● 有未保存修改"
            : `已保存 · 第 ${draft.edit_version} 次修改`}
        </span>
        {publication.data && (
          <>
            <Status value={publication.data.review_status} />
            <span>
              {publication.data.is_current_published
                ? "当前公开版本"
                : (publication.data.reason_code ?? "")}
            </span>
          </>
        )}
      </div>
      <ErrorBox error={error ?? places.error ?? events.error ?? tags.error} />
      {notice && (
        <p className="notice" role="status">
          {notice}
        </p>
      )}
      {error && (
        <p className="hint">
          如发生版本冲突，本地文字仍保留。请复制需要保留的内容，再
          <button
            className="text-button"
            onClick={() => {
              if (window.confirm("重新载入会放弃当前未保存的修改。继续吗？")) {
                setDraft(undefined);
                setDirty(false);
                void query.refetch();
              }
            }}
          >
            重新载入服务器草稿
          </button>
          。
        </p>
      )}
      {preview ? (
        <>
          <div className="preview-switch">
            <button aria-pressed={phone} onClick={() => setPhone(true)}>
              手机阅读
            </button>
            <button aria-pressed={!phone} onClick={() => setPhone(false)}>
              桌面阅读
            </button>
          </div>
          <article
            className={`article-preview ${phone ? "phone-preview" : ""}`}
          >
            <p className="eyebrow">MARCUS · SHANGHAI</p>
            {draft.cover_asset_id &&
              media.find((item) => item.id === draft.cover_asset_id)?.url && (
                <img
                  className="article-cover"
                  src={
                    media.find((item) => item.id === draft.cover_asset_id)?.url
                  }
                  alt="文章封面"
                />
              )}
            <h1>{draft.title || "文章标题"}</h1>
            {draft.subtitle && <p className="subtitle">{draft.subtitle}</p>}
            <p className="article-byline">
              文 / {user.display_name} ·{" "}
              {draft.focus_type === "event" ? "活动" : "地点"} ·{" "}
              {choices?.find(
                (item) =>
                  item.id ===
                  (draft.primary_event_id ?? draft.primary_place_id),
              )?.name ??
                choices?.find((item) => item.id === draft.primary_event_id)
                  ?.title ??
                "尚未选择主要对象"}
            </p>
            <EditorialPreview document={draft.document} media={media} />
          </article>
        </>
      ) : (
        <fieldset disabled={busy} className="editing-grid">
          <section className="writing-surface">
            <input
              className="title-input"
              aria-label="文章标题"
              placeholder="给这次发现一个标题"
              value={draft.title}
              maxLength={150}
              onChange={(event) => change({ title: event.target.value })}
            />
            <input
              className="subtitle-input"
              aria-label="文章副标题"
              placeholder="副标题（可选）"
              value={draft.subtitle}
              maxLength={200}
              onChange={(event) => change({ subtitle: event.target.value })}
            />
            <EditorialEditor
              disabled={busy}
              value={draft.document}
              onChange={(document) => change({ document })}
              media={media}
              upload={upload}
              onError={setError}
            />
          </section>
          <aside className="article-settings">
            <h3>文章资料</h3>
            <Field label="文章重心">
              <select
                value={draft.focus_type ?? ""}
                onChange={(event) =>
                  change({
                    focus_type: (event.target.value ||
                      null) as Draft["focus_type"],
                    primary_event_id: null,
                    primary_place_id: null,
                  })
                }
              >
                <option value="">请选择</option>
                <option value="place">一个地点</option>
                <option value="event">一项活动</option>
              </select>
            </Field>
            <Field
              label={draft.focus_type === "event" ? "主要活动" : "主要地点"}
              hint="所属区将在公开时随主要地点或活动举办地确定。"
            >
              <select
                disabled={!draft.focus_type}
                value={draft.primary_event_id ?? draft.primary_place_id ?? ""}
                onChange={(event) =>
                  change(
                    draft.focus_type === "event"
                      ? {
                          primary_event_id: event.target.value || null,
                          primary_place_id: null,
                        }
                      : {
                          primary_place_id: event.target.value || null,
                          primary_event_id: null,
                        },
                  )
                }
              >
                <option value="">请选择</option>
                {choices?.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name ?? item.title} · {statusName(item.status)}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="列表摘要（可选）" hint="留空时，发布时从正文提取。">
              <textarea
                rows={5}
                maxLength={500}
                value={draft.summary}
                onChange={(event) => change({ summary: event.target.value })}
              />
            </Field>
            <Field label="封面（可选）">
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                disabled={busy}
                onChange={async (event) => {
                  const file = event.target.files?.[0];
                  if (!file) return;
                  setBusy(true);
                  try {
                    const asset = await upload(file);
                    change({ cover_asset_id: asset.id });
                  } catch (err) {
                    setError(err);
                  } finally {
                    setBusy(false);
                  }
                }}
              />
            </Field>
            {draft.cover_asset_id && (
              <>
                <img
                  className="cover-preview"
                  src={
                    media.find((item) => item.id === draft.cover_asset_id)?.url
                  }
                  alt="文章封面"
                />
                <button onClick={() => change({ cover_asset_id: null })}>
                  移除封面
                </button>
              </>
            )}
            <fieldset className="tag-picker">
              <legend>标签 · {draft.tag_ids.length}/10</legend>
              {tags.data?.map((tag) => (
                <label key={tag.id} className="checkbox">
                  <input
                    type="checkbox"
                    checked={draft.tag_ids.includes(tag.id)}
                    disabled={
                      !draft.tag_ids.includes(tag.id) &&
                      (draft.tag_ids.length >= 10 || tag.enabled === false)
                    }
                    onChange={(event) =>
                      change({
                        tag_ids: event.target.checked
                          ? [...draft.tag_ids, tag.id]
                          : draft.tag_ids.filter((value) => value !== tag.id),
                      })
                    }
                  />
                  {tag.name}
                  {tag.enabled === false ? "（已停用）" : ""}
                </label>
              ))}
            </fieldset>
            <p className="hint">
              文章可以没有封面。图片、视频需要处理完成后才能提交。发布并不要求地点文章关联活动。
            </p>
          </aside>
        </fieldset>
      )}
    </>
  );
}
export async function allChoices(
  kind: "places" | "events" | "tags",
  cityId: string,
): Promise<Choice[]> {
  const items: Choice[] = [];
  let cursor: string | null = null;
  do {
    const page: Page<Choice> = await api.get(`/admin/${kind}`, {
      city_id: kind === "tags" ? undefined : cityId,
      limit: 50,
      cursor,
    });
    items.push(...page.items);
    cursor = page.next_cursor;
  } while (cursor);
  return items;
}
