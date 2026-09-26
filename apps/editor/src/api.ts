import {
  ApiClient,
  mediaUrl,
  uuid,
  type Tokens,
  type MediaAsset,
} from "@marcus/api-client";
import type { EditorialMedia } from "@marcus/editorial-editor";
let credentials: Tokens | null = null;
export const tokenStore = {
  get: async () => credentials,
  set: async (tokens: Tokens) => {
    credentials = tokens;
  },
  clear: async () => {
    credentials = null;
  },
};
export const api = new ApiClient({
  baseUrl: import.meta.env.VITE_API_URL ?? "http://localhost:8000/v1",
  tokenStore,
  clientType: "editor_web",
  onUnauthorized: () => window.dispatchEvent(new Event("marcus:unauthorized")),
});
export const asEditorMedia = (asset: MediaAsset): EditorialMedia => ({
  id: asset.id,
  kind: asset.kind,
  url: asset.kind === "video" ? asset.playback?.url : mediaUrl(asset, "detail"),
  poster: asset.poster?.url,
  status: asset.status,
});
export async function uploadMedia(
  file: File,
  purpose: "editorial_media" | "place_image" = "editorial_media",
): Promise<MediaAsset> {
  const kind = file.type.startsWith("video/") ? "video" : "image";
  if (
    ![
      "image/jpeg",
      "image/png",
      "image/webp",
      "video/mp4",
      "video/quicktime",
    ].includes(file.type)
  )
    throw new Error("请选择 JPEG、PNG、WebP 图片或 MP4、MOV 视频。");
  if (file.size > (kind === "image" ? 20 : 200) * 1024 * 1024)
    throw new Error(
      kind === "image" ? "图片不能超过20MB。" : "视频不能超过200MB。",
    );
  const ticket = await api.post<{
    asset_id: string;
    upload_url: string;
    method: string;
    required_headers: Record<string, string>;
  }>(
    "/media/uploads",
    {
      kind,
      purpose,
      file_name: file.name,
      mime_type: file.type,
      size_bytes: file.size,
    },
    { idempotencyKey: uuid() },
  );
  const response = await fetch(ticket.upload_url, {
    method: ticket.method,
    headers: ticket.required_headers,
    body: file,
  });
  if (!response.ok) throw new Error("文件上传失败，请重新选择文件。");
  await api.post(`/media/${ticket.asset_id}/complete`);
  const until = Date.now() + 10 * 60 * 1000;
  while (Date.now() < until) {
    const asset = await api.get<MediaAsset>(`/media/${ticket.asset_id}`);
    if (asset.status === "ready") return asset;
    if (asset.status === "rejected" || asset.status === "deleted")
      throw new Error(`媒体处理失败：${asset.error_code ?? asset.status}`);
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  throw new Error("媒体仍在后台处理，请稍后重试。");
}
export const errorMessage = (error: unknown) =>
  error instanceof Error
    ? error.message
    : typeof error === "string"
      ? error
      : "操作失败，请稍后重试。";
