import { useEffect, useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { mediaUrl, type MediaAsset, type Page } from "@marcus/api-client";
import { EditorialPreview } from "@marcus/editorial-editor";
import type { EditorialDocument } from "@marcus/editorial-schema";
import { api, asEditorMedia } from "./api";
import {
  dateText,
  Empty,
  ErrorBox,
  Field,
  PageHeading,
  Status,
} from "./shared";
interface Content {
  title?: string;
  subtitle?: string;
  body_text?: string;
  document?: EditorialDocument;
  note_id?: string;
  article_id?: string;
}
interface ReviewItem extends Content {
  id: string;
  status?: string;
  created_at?: string;
  reason?: string;
  description?: string;
  review_version?: number;
  version?: number;
  revision?: Content;
  submission?: ReviewItem;
  review?: ReviewItem;
  media?: MediaAsset[];
}
export function Moderation({ mode }: { mode: "reviews" | "reports" }) {
  const [kind, setKind] = useState<"editorial" | "note">("editorial");
  const [selected, setSelected] = useState<string>();
  const [cursor, setCursor] = useState<string>();
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");
  const [notice, setNotice] = useState("");
  const client = useQueryClient();
  const path = `/admin/${kind}-${mode === "reports" ? "reports" : kind === "editorial" ? "reviews" : "submissions"}`;
  const query = useQuery({
    queryKey: [path, "list", cursor],
    queryFn: () =>
      api.get<Page<ReviewItem>>(path, {
        cursor,
        status: mode === "reports" ? "open" : "pending",
      }),
  });
  const detail = useQuery({
    queryKey: [path, "detail", selected],
    queryFn: () => api.get<ReviewItem>(`${path}/${selected}`),
    enabled: Boolean(selected),
  });
  useEffect(() => {
    setSelected(undefined);
    setCursor(undefined);
    setError(undefined);
    setNotice("");
  }, [mode, kind]);
  const decide = async (
    decision: "approve" | "reject" | "resolved" | "dismissed",
  ) => {
    if (!selected || !detail.data) return;
    setBusy(true);
    setError(undefined);
    try {
      if (mode === "reviews") {
        if (decision === "reject" && !reason.trim())
          throw new Error("拒绝前请填写原因代码。");
        await api.post(`${path}/${selected}/decision`, {
          decision,
          expected_review_version:
            kind === "note" ? detail.data.review_version : detail.data.version,
          reason_code: reason || null,
          note: note || null,
        });
      } else {
        if (!note.trim()) throw new Error("请填写处理说明。");
        await api.patch(`${path}/${selected}`, {
          status: decision,
          resolution_note: note,
        });
      }
      await client.invalidateQueries({ queryKey: [path] });
      setSelected(undefined);
      setNotice(
        mode === "reviews"
          ? "审核结果已记录。公开状态由服务器根据提交先后与当前内容状态决定。"
          : "举报处理结果已保存。",
      );
      setReason("");
      setNote("");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };
  const review =
    mode === "reviews"
      ? detail.data
      : kind === "editorial"
        ? detail.data?.review
        : detail.data?.submission;
  const content = kind === "editorial" ? review?.revision : review;
  const media = review?.media ?? [];
  const hide = async () => {
    const targetId =
      kind === "editorial" ? content?.article_id : content?.note_id;
    if (!targetId || !note.trim()) {
      setError(new Error("请填写下架说明。"));
      return;
    }
    setBusy(true);
    try {
      const target = await api.get<{ version: number }>(
        `/admin/${kind === "note" ? "notes" : "editorials"}/${targetId}`,
      );
      await api.post(
        `/admin/${kind === "note" ? "notes" : "editorials"}/${targetId}/hide`,
        { expected_version: target.version, reason: note },
      );
      setNotice("内容已下架；你可以继续保存举报处理结果。");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <PageHeading
        eyebrow={mode === "reviews" ? "REVIEW DESK" : "COMMUNITY CARE"}
        title={mode === "reviews" ? "内容审核" : "用户举报"}
      />
      <ContentStatusControls kind={kind} />
      <div className="tab-strip">
        <button
          aria-pressed={kind === "editorial"}
          onClick={() => setKind("editorial")}
        >
          Editor 文章
        </button>
        <button aria-pressed={kind === "note"} onClick={() => setKind("note")}>
          用户 Notes
        </button>
        <button onClick={() => void query.refetch()}>刷新</button>
      </div>
      <ErrorBox error={error ?? query.error ?? detail.error} />
      {notice && <p className="notice">{notice}</p>}
      <div className="review-layout">
        <section className="data-list">
          {query.data?.items.map((item) => (
            <button
              className={`data-row ${selected === item.id ? "selected" : ""}`}
              key={item.id}
              onClick={() => {
                setSelected(item.id);
                setReason("");
                setNote("");
                setNotice("");
              }}
            >
              <div>
                <strong>
                  {item.title ||
                    item.revision?.title ||
                    item.reason ||
                    `待处理内容 ${item.id.slice(0, 8)}`}
                </strong>
                <small>{dateText(item.created_at)}</small>
              </div>
              <Status value={item.status} />
            </button>
          ))}
          {!query.isPending && !query.data?.items.length && (
            <Empty>暂时没有待处理的内容。</Empty>
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
        {selected && detail.data && (
          <section className="panel review-detail">
            <p className="eyebrow">固定提交内容 · 不随作者草稿变化</p>
            {mode === "reports" && (
              <div className="report-reason">
                <strong>举报原因：{detail.data.reason}</strong>
                <p>{detail.data.description}</p>
              </div>
            )}
            <h2>{content?.title || "无标题笔记"}</h2>
            {content?.subtitle && (
              <p className="subtitle">{content.subtitle}</p>
            )}
            {content?.document ? (
              <EditorialPreview
                document={content.document}
                media={media.map(asEditorMedia)}
              />
            ) : (
              <>
                <p className="note-text">{content?.body_text}</p>
                <div className="review-images">
                  {media.map((asset) => (
                    <img
                      key={asset.id}
                      src={mediaUrl(asset, "detail")}
                      alt="用户提交图片"
                    />
                  ))}
                </div>
              </>
            )}
            <div className="review-actions">
              {mode === "reviews" && (
                <Field
                  label="拒绝原因代码"
                  hint="例如：inaccurate、copyright、spam。批准时可留空。"
                >
                  <input
                    value={reason}
                    onChange={(event) => setReason(event.target.value)}
                    maxLength={80}
                  />
                </Field>
              )}
              <Field
                label={
                  mode === "reviews" ? "审核说明（可选）" : "处理说明（必填）"
                }
              >
                <textarea
                  rows={4}
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  maxLength={5000}
                />
              </Field>
              <div className="inline">
                {mode === "reviews" ? (
                  <>
                    <button
                      className="primary"
                      disabled={busy}
                      onClick={() => void decide("approve")}
                    >
                      批准此提交
                    </button>
                    <button
                      disabled={busy || !reason.trim()}
                      onClick={() => void decide("reject")}
                    >
                      拒绝
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      className="primary"
                      disabled={busy || !note.trim()}
                      onClick={() => void decide("resolved")}
                    >
                      标记已处理
                    </button>
                    <button
                      disabled={busy || !note.trim()}
                      onClick={() => void decide("dismissed")}
                    >
                      驳回举报
                    </button>
                    <button
                      className="danger-link"
                      disabled={busy || !note.trim()}
                      onClick={() => void hide()}
                    >
                      下架相关内容
                    </button>
                  </>
                )}
              </div>
            </div>
          </section>
        )}
      </div>
    </>
  );
}
export function AccessManagement() {
  const [userId, setUserId] = useState("");
  const [role, setRole] = useState("editor");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const act = async (action: "grant" | "revoke" | "suspend") => {
    setBusy(true);
    setError(undefined);
    setNotice("");
    try {
      if (action === "grant")
        await api.put(`/admin/users/${userId}/roles/${role}`);
      if (action === "revoke")
        await api.delete(`/admin/users/${userId}/roles/${role}`);
      if (action === "suspend")
        await api.post(`/admin/users/${userId}/suspend`, { reason });
      setNotice("账户权限已更新。");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <PageHeading eyebrow="PEOPLE & PERMISSIONS" title="人员权限" />
      <section className="panel narrow">
        <p>通过用户编号授予编辑或审核权限。服务器会记录每次权限变更。</p>
        <Field label="用户编号">
          <input
            value={userId}
            onChange={(event) => setUserId(event.target.value)}
            placeholder="用户 UUID"
          />
        </Field>
        <Field label="角色">
          <select
            value={role}
            onChange={(event) => setRole(event.target.value)}
          >
            <option value="editor">编辑</option>
            <option value="moderator">审核员</option>
            <option value="admin">管理员</option>
          </select>
        </Field>
        <div className="inline">
          <button
            className="primary"
            disabled={busy || !userId}
            onClick={() => void act("grant")}
          >
            授予权限
          </button>
          <button disabled={busy || !userId} onClick={() => void act("revoke")}>
            撤销权限
          </button>
        </div>
        <hr />
        <Field label="停用原因">
          <textarea
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            maxLength={1000}
          />
        </Field>
        <button
          className="danger-link"
          disabled={busy || !userId || !reason}
          onClick={() => {
            if (window.confirm("停用后，此用户的所有登录都会失效。继续吗？"))
              void act("suspend");
          }}
        >
          停用账户
        </button>
        <ErrorBox error={error} />
        {notice && <p className="notice">{notice}</p>}
      </section>
    </>
  );
}

function ContentStatusControls({ kind }: { kind: "note" | "editorial" }) {
  const [id, setId] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<unknown>();
  const [result, setResult] = useState<{
    id: string;
    status: string;
    version: number;
  }>();
  const [busy, setBusy] = useState(false);
  const path = `/admin/${kind === "note" ? "notes" : "editorials"}/${id}`;
  useEffect(() => {
    setResult(undefined);
    setId("");
    setError(undefined);
  }, [kind]);
  const read = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(undefined);
    try {
      setResult(await api.get(path));
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };
  const change = async (action: "hide" | "restore") => {
    if (!result) return;
    setBusy(true);
    setError(undefined);
    try {
      await api.post(`${path}/${action}`, {
        expected_version: result.version,
        ...(action === "hide" ? { reason } : {}),
      });
      setResult(await api.get(path));
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };
  return (
    <details className="content-controls">
      <summary>按内容编号下架或恢复{kind === "note" ? "笔记" : "文章"}</summary>
      <form className="inline" onSubmit={read}>
        <input
          aria-label="内容编号"
          placeholder="内容 UUID"
          value={id}
          onChange={(event) => {
            setId(event.target.value);
            setResult(undefined);
          }}
          required
        />
        <button disabled={busy}>读取状态</button>
      </form>
      <ErrorBox error={error} />
      {result && (
        <div className="inline">
          <Status value={result.status} />
          <input
            aria-label="下架原因"
            placeholder="下架原因"
            value={reason}
            maxLength={1000}
            onChange={(event) => setReason(event.target.value)}
          />
          <button
            disabled={busy || !reason || result.status === "hidden"}
            onClick={() => void change("hide")}
          >
            下架
          </button>
          <button
            disabled={busy || result.status !== "hidden"}
            onClick={() => void change("restore")}
          >
            复核并恢复公开
          </button>
        </div>
      )}
    </details>
  );
}
