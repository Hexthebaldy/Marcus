import { createContext, useContext, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import type { City, District, Page, User } from "@marcus/api-client";
import { api, errorMessage } from "./api";
export const SessionContext = createContext<{ user: User; city: City }>(
  {} as { user: User; city: City },
);
export const useSession = () => useContext(SessionContext);
export const useDistricts = (cityId: string) =>
  useQuery({
    queryKey: ["districts", cityId],
    queryFn: () =>
      api
        .get<Page<District>>(`/cities/${cityId}/districts`)
        .then((result) => result.items),
  });
export function ErrorBox({ error }: { error?: unknown }) {
  return error ? (
    <div className="error" role="alert">
      {errorMessage(error)}
    </div>
  ) : null;
}
export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}
export function PageHeading({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: string;
  children?: ReactNode;
}) {
  return (
    <header className="page-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
      </div>
      {children}
    </header>
  );
}
export const statusName = (status?: string) =>
  ({
    draft: "草稿",
    pending: "待审核",
    published: "已公开",
    approved: "已批准",
    rejected: "已拒绝",
    hidden: "已下架",
    active: "公开",
    closed: "已关闭",
    cancelled: "已取消",
    ended: "已结束",
    resolved: "已处理",
    dismissed: "已驳回",
    open: "待处理",
    scheduled: "正常",
    sold_out: "售罄",
  })[status ?? ""] ??
  status ??
  "—";
export function Status({ value }: { value?: string }) {
  return <span className={`status status-${value}`}>{statusName(value)}</span>;
}
export function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="empty">
      <span>✳</span>
      <p>{children}</p>
    </div>
  );
}
export const dateText = (value?: string | null) =>
  value
    ? new Date(value).toLocaleString("zh-CN", {
        timeZone: "Asia/Shanghai",
        hour12: false,
      })
    : "—";
