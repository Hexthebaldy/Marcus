import * as ImagePicker from "expo-image-picker";
import { manipulateAsync, SaveFormat } from "expo-image-manipulator";
import { File } from "expo-file-system";
import { fetch as expoFetch } from "expo/fetch";
import * as Crypto from "expo-crypto";
import type { MediaAsset } from "@marcus/api-client";
import { api } from "./session";
export async function pickAndUpload(
  purpose: "note_image" | "avatar",
  limit = 1,
  onProgress?: (message: string) => void,
): Promise<MediaAsset[]> {
  const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
  if (!permission.granted)
    throw new Error("请在手机设置中允许访问选中的照片。");
  const result = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ["images"],
    allowsMultipleSelection: limit > 1,
    selectionLimit: limit,
    quality: 1,
  });
  if (result.canceled) return [];
  const uploaded: MediaAsset[] = [];
  for (const selected of result.assets.slice(0, limit)) {
    onProgress?.(`正在处理照片 ${uploaded.length + 1}/${result.assets.length}`);
    const image = await manipulateAsync(
      selected.uri,
      selected.width > 2400 ? [{ resize: { width: 2400 } }] : [],
      { compress: 0.9, format: SaveFormat.JPEG },
    );
    const file = new File(image.uri);
    const ticket = await api.post<{
      asset_id: string;
      upload_url: string;
      method: string;
      required_headers: Record<string, string>;
    }>(
      "/media/uploads",
      {
        kind: "image",
        purpose,
        file_name: "photo.jpg",
        mime_type: "image/jpeg",
        size_bytes: file.size,
      },
      { idempotencyKey: Crypto.randomUUID() },
    );
    const response = await expoFetch(ticket.upload_url, {
      method: ticket.method,
      headers: ticket.required_headers,
      body: file,
    });
    if (!response.ok) throw new Error("照片上传失败，请重试。");
    await api.post(`/media/${ticket.asset_id}/complete`);
    let asset = await api.get<MediaAsset>(`/media/${ticket.asset_id}`);
    for (
      let attempt = 0;
      attempt < 45 &&
      (asset.status === "pending" || asset.status === "processing");
      attempt++
    ) {
      onProgress?.("照片已上传，正在生成预览…");
      await new Promise((resolve) => setTimeout(resolve, 2000));
      asset = await api.get<MediaAsset>(`/media/${ticket.asset_id}`);
    }
    if (asset.status === "rejected" || asset.status === "deleted")
      throw new Error("这张照片无法使用，请换一张。");
    // A processing asset remains attached to the draft and can become ready later.
    uploaded.push(asset);
  }
  return uploaded;
}
