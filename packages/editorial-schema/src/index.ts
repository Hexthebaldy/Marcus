export type MediaWidth = "content" | "wide" | "full";
export type Mark =
  | { type: "bold" | "italic" | "strike" }
  | { type: "link"; attrs: { href: string } };
export interface GalleryItem {
  asset_id: string;
  alt: string;
  caption: string;
  credit: string;
}
export interface EditorialNode {
  type:
    | "paragraph"
    | "heading"
    | "blockquote"
    | "bulletList"
    | "orderedList"
    | "listItem"
    | "image"
    | "video"
    | "gallery"
    | "callout"
    | "divider"
    | "text"
    | "hardBreak";
  text?: string;
  marks?: Mark[];
  attrs?: {
    align?: "left" | "center" | "right";
    level?: 2 | 3;
    asset_id?: string;
    alt?: string;
    caption?: string;
    credit?: string;
    width?: MediaWidth;
    items?: GalleryItem[];
    layout?: "single" | "two_column";
    tone?: "info" | "warning";
  };
  content?: EditorialNode[];
}
export interface EditorialDocument {
  type: "doc";
  content: EditorialNode[];
}
export const emptyDocument = (): EditorialDocument => ({
  type: "doc",
  content: [{ type: "paragraph" }],
});
export const safeHref = (href: string): boolean => {
  try {
    return (
      href.length <= 2048 &&
      ["https:", "http:"].includes(new URL(href).protocol)
    );
  } catch {
    return false;
  }
};
export function documentText(document: EditorialDocument): string {
  const text = (node: EditorialNode): string =>
    node.type === "text"
      ? (node.text ?? "")
      : (node.content ?? [])
          .map(text)
          .join(node.type === "paragraph" ? "" : "\n");
  return document.content.map(text).join("\n");
}
export function documentAssetIds(document: EditorialDocument): string[] {
  const ids = new Set<string>();
  const visit = (node: EditorialNode) => {
    if (node.attrs?.asset_id) ids.add(node.attrs.asset_id);
    for (const item of node.attrs?.items ?? []) ids.add(item.asset_id);
    node.content?.forEach(visit);
  };
  document.content.forEach(visit);
  return [...ids];
}
/** Removes editor-only attributes; the API remains the final authority for document validation. */
export function normalizeDocument(raw: {
  type?: string;
  content?: unknown[];
}): EditorialDocument {
  const normalize = (value: unknown): EditorialNode => {
    const node = value as EditorialNode;
    const output: EditorialNode = { type: node.type };
    if (node.type === "text") {
      output.text = node.text;
      if (node.marks?.length)
        output.marks = node.marks.map((mark) =>
          mark.type === "link"
            ? { type: "link", attrs: { href: mark.attrs.href } }
            : { type: mark.type },
        );
    }
    if (node.content?.length) output.content = node.content.map(normalize);
    if (node.type === "paragraph")
      output.attrs = { align: node.attrs?.align ?? "left" };
    if (node.type === "heading")
      output.attrs = { level: node.attrs?.level ?? 2 };
    if (node.type === "image" || node.type === "video")
      output.attrs = {
        asset_id: node.attrs?.asset_id,
        caption: node.attrs?.caption ?? "",
        credit: node.attrs?.credit ?? "",
        width: node.attrs?.width ?? "content",
        ...(node.type === "image" ? { alt: node.attrs?.alt ?? "" } : {}),
      };
    if (node.type === "gallery")
      output.attrs = {
        items: node.attrs?.items ?? [],
        layout: node.attrs?.layout ?? "two_column",
        width: node.attrs?.width ?? "wide",
      };
    if (node.type === "callout")
      output.attrs = { tone: node.attrs?.tone ?? "info" };
    return output;
  };
  return { type: "doc", content: (raw.content ?? []).map(normalize) };
}
export function validateDocument(
  document: EditorialDocument,
  publishing = false,
): string[] {
  const errors: string[] = [];
  let count = 0;
  let letters = 0;
  const images = new Set<string>();
  const videos = new Set<string>();
  const visit = (node: EditorialNode, depth: number) => {
    count += 1;
    if (depth > 6) errors.push("正文层级不能超过6层。");
    if (node.type === "text") letters += node.text?.length ?? 0;
    for (const mark of node.marks ?? [])
      if (mark.type === "link" && !safeHref(mark.attrs.href))
        errors.push("链接必须是完整的 http 或 https 地址。");
    if (node.type === "image" && node.attrs?.asset_id)
      images.add(node.attrs.asset_id);
    if (node.type === "video" && node.attrs?.asset_id)
      videos.add(node.attrs.asset_id);
    for (const item of node.attrs?.items ?? []) images.add(item.asset_id);
    node.content?.forEach((child) => visit(child, depth + 1));
  };
  document.content.forEach((node) => visit(node, 1));
  if (count > 2000) errors.push("正文内容块过多。");
  if (letters > 20000) errors.push("正文不能超过20,000字。");
  if (images.size > 20 || videos.size > 5)
    errors.push("每篇最多20张图片和5段视频。");
  if (new TextEncoder().encode(JSON.stringify(document)).length > 512 * 1024)
    errors.push("正文数据不能超过512KB。");
  if (publishing && !documentText(document).trim())
    errors.push("正文需要至少一段文字。");
  return [...new Set(errors)];
}
