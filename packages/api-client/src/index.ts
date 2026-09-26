export * from "./types";
export type { paths, components, operations } from "./generated";
export type Tokens = { access_token: string; refresh_token?: string };
export type TokenStore = {
  get(): Promise<Tokens | null>;
  set(tokens: Tokens): Promise<void>;
  clear(): Promise<void>;
};
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: unknown,
    public requestId?: string,
  ) {
    super(message);
  }
}
type Options = { idempotencyKey?: string; signal?: AbortSignal };
const messages: Record<string, string> = {
  version_conflict: "内容已在其他地方修改。请保留本机内容，重新读取后再保存。",
  invalid_code: "验证码不正确，请重新输入。",
  invalid_challenge: "验证码已失效，请重新获取。",
  resend_too_soon: "发送过于频繁，请稍后重试。",
  too_many_requests: "请求次数过多，请稍后再试。",
  media_not_ready: "图片或视频还未处理完成，请稍后提交。",
  media_not_usable: "你没有权限使用这份媒体。",
  login_required: "请先登录。",
  session_inactive: "登录已失效，请重新登录。",
  note_empty: "请填写正文或添加至少一张图片。",
  article_empty: "文章需要标题和正文。",
  invalid_document: "正文格式不符合要求，请检查排版和媒体。",
  not_found: "内容不存在，或暂时无法查看。",
  content_hidden: "这篇内容已被下架，请联系管理员处理。",
  rate_limiter_unavailable: "暂时无法发送验证码，请稍后再试。",
};
export class ApiClient {
  private refreshing?: Promise<boolean>;
  constructor(
    private config: {
      baseUrl: string;
      tokenStore: TokenStore;
      clientType: "mobile" | "editor_web";
      onUnauthorized?: () => void;
    },
  ) {}
  async refresh(): Promise<boolean> {
    if (!this.refreshing)
      this.refreshing = this.performRefresh().finally(() => {
        this.refreshing = undefined;
      });
    return this.refreshing;
  }
  private async performRefresh(): Promise<boolean> {
    const old = await this.config.tokenStore.get();
    if (this.config.clientType === "mobile" && !old?.refresh_token)
      return false;
    const response = await fetch(`${this.config.baseUrl}/auth/refresh`, {
      method: "POST",
      credentials: this.config.clientType === "editor_web" ? "include" : "omit",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "Marcus",
      },
      body: JSON.stringify(
        this.config.clientType === "mobile"
          ? { refresh_token: old?.refresh_token }
          : {},
      ),
    });
    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        await this.config.tokenStore.clear();
        this.config.onUnauthorized?.();
      }
      return false;
    }
    const tokens = (await response.json()) as Tokens;
    await this.config.tokenStore.set(tokens);
    return true;
  }
  async request<T>(
    method: string,
    path: string,
    body?: unknown,
    options: Options = {},
    retry = true,
  ): Promise<T> {
    const token = await this.config.tokenStore.get();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "X-Requested-With": "Marcus",
    };
    if (token) headers.Authorization = `Bearer ${token.access_token}`;
    if (options.idempotencyKey)
      headers["Idempotency-Key"] = options.idempotencyKey;
    const response = await fetch(`${this.config.baseUrl}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: options.signal,
      credentials: this.config.clientType === "editor_web" ? "include" : "omit",
    });
    if (response.status === 401 && retry && !path.startsWith("/auth/")) {
      if (await this.refresh())
        return this.request(method, path, body, options, false);
    }
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      const code = data.error?.code ?? "request_failed";
      const message =
        messages[code] ??
        (data.error?.message !== code ? data.error?.message : undefined) ??
        "操作未完成，请检查填写内容后重试。";
      throw new ApiError(
        response.status,
        code,
        message,
        data.error?.details,
        data.request_id,
      );
    }
    if (response.status === 204) return undefined as T;
    return response.json() as Promise<T>;
  }
  get<T>(
    path: string,
    params?: Record<string, string | number | undefined | null>,
    options?: Options,
  ): Promise<T> {
    const query = new URLSearchParams();
    Object.entries(params ?? {}).forEach(([key, value]) => {
      if (value != null) query.set(key, String(value));
    });
    return this.request(
      "GET",
      `${path}${query.size ? `?${query}` : ""}`,
      undefined,
      options,
    );
  }
  post<T>(path: string, body?: unknown, options?: Options) {
    return this.request<T>("POST", path, body, options);
  }
  patch<T>(path: string, body?: unknown, options?: Options) {
    return this.request<T>("PATCH", path, body, options);
  }
  put<T>(path: string, body?: unknown, options?: Options) {
    return this.request<T>("PUT", path, body, options);
  }
  delete<T>(path: string, body?: unknown, options?: Options) {
    return this.request<T>("DELETE", path, body, options);
  }
}
// Clients on React Native use expo-crypto for UUID creation instead of this browser helper.
export const uuid = () => globalThis.crypto.randomUUID();
