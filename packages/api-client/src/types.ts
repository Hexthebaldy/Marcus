import type { components } from "./generated";

export type Page<T> = { items: T[]; next_cursor: string | null };
export type City = components["schemas"]["City"];
export type District = components["schemas"]["District"];
export type MediaVariant = components["schemas"]["MediaVariant"];
export type MediaAsset = components["schemas"]["MediaAsset"];
export function mediaUrl(
  asset?: MediaAsset | null,
  variant: "thumb" | "feed" | "detail" = "feed",
): string | undefined {
  return asset?.variants?.[variant]?.url;
}
export type User = components["schemas"]["User"];
export type Reactions = components["schemas"]["Reactions"];
export type Place = components["schemas"]["Place"];
export type EventSession = components["schemas"]["EventSession"];
export type CityEvent = components["schemas"]["Event"];
export type Note = components["schemas"]["Note"];
export type DocumentNode = {
  type: string;
  text?: string;
  attrs?: Record<string, unknown>;
  marks?: { type: string; attrs?: Record<string, unknown> }[];
  content?: DocumentNode[];
};
export type Editorial = Omit<components["schemas"]["Editorial"], "document"> & {
  document: DocumentNode;
};
export type NoteDraft = components["schemas"]["NoteDraft"];
export type Publication = components["schemas"]["Publication"];
