import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Node, Extension, mergeAttributes } from "@tiptap/core";
import {
  EditorContent,
  NodeViewWrapper,
  ReactNodeViewRenderer,
  useEditor,
  type NodeViewProps,
} from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Blockquote from "@tiptap/extension-blockquote";
import ListItem from "@tiptap/extension-list-item";
import {
  documentText,
  normalizeDocument,
  safeHref,
  type EditorialDocument,
  type EditorialNode,
  type GalleryItem,
} from "@marcus/editorial-schema";

export interface EditorialMedia {
  id: string;
  kind: string;
  url?: string;
  poster?: string;
  status?: string;
}
export interface EditorialEditorProps {
  disabled?: boolean;
  value: EditorialDocument;
  onChange: (document: EditorialDocument) => void;
  media: EditorialMedia[];
  upload: (file: File) => Promise<EditorialMedia>;
  onError: (message: string) => void;
}
const ParagraphAlignment = Extension.create({
  name: "paragraphAlignment",
  addGlobalAttributes: () => [
    {
      types: ["paragraph"],
      attributes: {
        align: {
          default: "left",
          parseHTML: (element) => element.style.textAlign || "left",
          renderHTML: (attrs) => ({ style: `text-align:${attrs.align}` }),
        },
      },
    },
  ],
});
const paragraphOnly = Node.create({
  name: "callout",
  group: "block",
  content: "paragraph+",
  defining: true,
  addAttributes: () => ({ tone: { default: "info" } }),
  parseHTML: () => [{ tag: "aside[data-callout]" }],
  renderHTML: ({ HTMLAttributes }) => [
    "aside",
    mergeAttributes(HTMLAttributes, {
      "data-callout": "",
      class: "editor-callout",
    }),
    0,
  ],
});
const divider = Node.create({
  name: "divider",
  group: "block",
  atom: true,
  parseHTML: () => [{ tag: "hr" }],
  renderHTML: () => ["hr"],
});
function MediaNodeView({
  node,
  updateAttributes,
  deleteNode,
  extension,
  selected,
}: NodeViewProps) {
  const media = (
    extension.options.resolveMedia as (id: string) => EditorialMedia | undefined
  )(node.attrs.asset_id);
  const items = (node.attrs.items ?? []) as GalleryItem[];
  const input = (label: string, key: string) => (
    <label>
      {label}
      <input
        maxLength={1000}
        value={String(node.attrs[key] ?? "")}
        onChange={(event) => updateAttributes({ [key]: event.target.value })}
      />
    </label>
  );
  return (
    <NodeViewWrapper
      className={`media-block width-${node.attrs.width} ${selected ? "selected" : ""}`}
    >
      <div contentEditable={false}>
        {node.type.name === "gallery" ? (
          <div className={`gallery ${node.attrs.layout}`}>
            {items.map((item, index) => {
              const asset = (
                extension.options.resolveMedia as (
                  id: string,
                ) => EditorialMedia | undefined
              )(item.asset_id);
              return (
                <figure key={item.asset_id}>
                  {asset?.url ? (
                    <img src={asset.url} alt={item.alt} />
                  ) : (
                    <p>
                      图片 {index + 1} · {asset?.status ?? "加载中"}
                    </p>
                  )}
                  <label>
                    图片说明
                    <input
                      maxLength={1000}
                      value={item.caption}
                      onChange={(event) =>
                        updateAttributes({
                          items: items.map((entry, i) =>
                            i === index
                              ? { ...entry, caption: event.target.value }
                              : entry,
                          ),
                        })
                      }
                    />
                  </label>
                  <label>
                    替代文字
                    <input
                      maxLength={1000}
                      value={item.alt}
                      onChange={(event) =>
                        updateAttributes({
                          items: items.map((entry, i) =>
                            i === index
                              ? { ...entry, alt: event.target.value }
                              : entry,
                          ),
                        })
                      }
                    />
                  </label>
                  <label>
                    摄影 / 来源
                    <input
                      maxLength={1000}
                      value={item.credit}
                      onChange={(event) =>
                        updateAttributes({
                          items: items.map((entry, i) =>
                            i === index
                              ? { ...entry, credit: event.target.value }
                              : entry,
                          ),
                        })
                      }
                    />
                  </label>
                  <div className="inline">
                    <button
                      type="button"
                      disabled={index === 0}
                      onClick={() => {
                        const reordered = [...items];
                        [reordered[index - 1], reordered[index]] = [
                          reordered[index]!,
                          reordered[index - 1]!,
                        ];
                        updateAttributes({ items: reordered });
                      }}
                    >
                      前移
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        items.length === 1
                          ? deleteNode()
                          : updateAttributes({
                              items: items.filter((_, i) => i !== index),
                            })
                      }
                    >
                      移除
                    </button>
                  </div>
                </figure>
              );
            })}
          </div>
        ) : media?.url ? (
          node.type.name === "video" ? (
            <video
              src={media.url}
              poster={media.poster}
              controls
              preload="metadata"
            />
          ) : (
            <img src={media.url} alt={node.attrs.alt ?? ""} />
          )
        ) : (
          <div className="media-placeholder">
            媒体 · {media?.status ?? "加载中"}
          </div>
        )}
        <div className="media-controls">
          {node.type.name !== "gallery" && (
            <>
              {input("说明", "caption")}
              {input("摄影 / 来源", "credit")}
              {node.type.name === "image" && input("替代文字", "alt")}
            </>
          )}
          <label>
            宽度
            <select
              value={node.attrs.width}
              onChange={(event) =>
                updateAttributes({ width: event.target.value })
              }
            >
              <option value="content">正文宽度</option>
              <option value="wide">较宽</option>
              <option value="full">通栏</option>
            </select>
          </label>
          {node.type.name === "gallery" && (
            <label>
              排列
              <select
                value={node.attrs.layout}
                onChange={(event) =>
                  updateAttributes({ layout: event.target.value })
                }
              >
                <option value="single">单列</option>
                <option value="two_column">桌面双列</option>
              </select>
            </label>
          )}
          <button type="button" className="danger-link" onClick={deleteNode}>
            移除此内容块
          </button>
        </div>
      </div>
    </NodeViewWrapper>
  );
}
function createMediaNode(
  name: "image" | "video" | "gallery",
  resolveMedia: (id: string) => EditorialMedia | undefined,
) {
  return Node.create({
    name,
    group: "block",
    atom: true,
    draggable: true,
    addOptions: () => ({ resolveMedia }),
    addAttributes: () =>
      name === "gallery"
        ? {
            items: { default: [] },
            layout: { default: "two_column" },
            width: { default: "wide" },
          }
        : {
            asset_id: { default: "" },
            alt: { default: "" },
            caption: { default: "" },
            credit: { default: "" },
            width: { default: "content" },
          },
    parseHTML: () => [{ tag: `figure[data-editorial-${name}]` }],
    renderHTML: ({ HTMLAttributes }) => [
      "figure",
      mergeAttributes(HTMLAttributes, { [`data-editorial-${name}`]: "" }),
    ],
    addNodeView: () => ReactNodeViewRenderer(MediaNodeView),
  });
}
export function EditorialEditor({
  value,
  onChange,
  media,
  upload,
  onError,
  disabled = false,
}: EditorialEditorProps) {
  const mediaRef = useRef(media);
  mediaRef.current = media;
  const [busy, setBusy] = useState(false);
  const [linkInput, setLinkInput] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const insertKind = useRef<"image" | "video" | "gallery">("image");
  const extensions = useMemo(
    () => [
      StarterKit.configure({
        heading: { levels: [2, 3] },
        blockquote: false,
        listItem: false,
        code: false,
        codeBlock: false,
        horizontalRule: false,
        underline: false,
        link: {
          openOnClick: false,
          autolink: false,
          protocols: ["http", "https"],
          isAllowedUri: (url) => safeHref(url),
        },
        trailingNode: false,
      }),
      Blockquote.extend({ content: "paragraph+" }),
      ListItem.extend({ content: "paragraph+" }),
      ParagraphAlignment,
      paragraphOnly,
      divider,
      ...(["image", "video", "gallery"] as const).map((kind) =>
        createMediaNode(kind, (id) =>
          mediaRef.current.find((asset) => asset.id === id),
        ),
      ),
    ],
    [],
  );
  const editor = useEditor({
    extensions,
    content: value,
    editorProps: {
      attributes: { class: "editor-prose", "aria-label": "文章正文" },
    },
    onUpdate: ({ editor: active }) =>
      onChange(normalizeDocument(active.getJSON())),
  });
  useEffect(() => {
    editor?.setEditable(!disabled && !busy);
  }, [editor, disabled, busy]);
  useEffect(() => {
    if (
      editor &&
      JSON.stringify(normalizeDocument(editor.getJSON())) !==
        JSON.stringify(value)
    )
      editor.commands.setContent(value, { emitUpdate: false });
  }, [value, editor]);
  const addFiles = async (files: FileList | null) => {
    if (!editor || !files?.length) return;
    setBusy(true);
    try {
      const uploaded: EditorialMedia[] = [];
      for (const file of Array.from(files)) uploaded.push(await upload(file));
      const kind = insertKind.current;
      if (kind === "gallery")
        editor
          .chain()
          .focus()
          .insertContent({
            type: "gallery",
            attrs: {
              items: uploaded.map((asset) => ({
                asset_id: asset.id,
                alt: "",
                caption: "",
                credit: "",
              })),
              layout: "two_column",
              width: "wide",
            },
          })
          .run();
      else
        editor
          .chain()
          .focus()
          .insertContent(
            uploaded.map((asset) => ({
              type: kind,
              attrs: {
                asset_id: asset.id,
                caption: "",
                credit: "",
                width: "content",
                ...(kind === "image" ? { alt: "" } : {}),
              },
            })),
          )
          .run();
    } catch (error) {
      onError(error instanceof Error ? error.message : "上传失败，请重试。");
    } finally {
      setBusy(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  };
  if (!editor) return <p>正在准备编辑器…</p>;
  const insert = (kind: "image" | "video" | "gallery") => {
    insertKind.current = kind;
    if (fileInput.current) {
      fileInput.current.accept =
        kind === "video"
          ? "video/mp4,video/quicktime"
          : "image/jpeg,image/png,image/webp";
      fileInput.current.multiple = kind === "gallery";
      fileInput.current.click();
    }
  };
  const button = (label: string, action: () => void, active = false) => (
    <button type="button" aria-pressed={active} onClick={action}>
      {label}
    </button>
  );
  return (
    <div className="professional-editor">
      <fieldset
        disabled={disabled || busy}
        className="editor-toolbar"
        aria-label="正文排版工具"
      >
        {button(
          "正文",
          () => {
            editor.chain().focus().setParagraph().run();
          },
          editor.isActive("paragraph"),
        )}
        {button(
          "小标题",
          () => {
            editor.chain().focus().toggleHeading({ level: 2 }).run();
          },
          editor.isActive("heading", { level: 2 }),
        )}
        {button(
          "次标题",
          () => {
            editor.chain().focus().toggleHeading({ level: 3 }).run();
          },
          editor.isActive("heading", { level: 3 }),
        )}
        {button(
          "粗体",
          () => {
            editor.chain().focus().toggleBold().run();
          },
          editor.isActive("bold"),
        )}
        {button(
          "斜体",
          () => {
            editor.chain().focus().toggleItalic().run();
          },
          editor.isActive("italic"),
        )}
        {button(
          "删除线",
          () => {
            editor.chain().focus().toggleStrike().run();
          },
          editor.isActive("strike"),
        )}
        {button(
          "引用",
          () => {
            editor.chain().focus().toggleBlockquote().run();
          },
          editor.isActive("blockquote"),
        )}
        {button("项目", () => {
          editor.chain().focus().toggleBulletList().run();
        })}
        {button("编号", () => {
          editor.chain().focus().toggleOrderedList().run();
        })}
        {button("链接", () =>
          setLinkInput(String(editor.getAttributes("link").href ?? "")),
        )}
        {button("左对齐", () => {
          editor
            .chain()
            .focus()
            .updateAttributes("paragraph", { align: "left" })
            .run();
        })}
        {button("居中", () => {
          editor
            .chain()
            .focus()
            .updateAttributes("paragraph", { align: "center" })
            .run();
        })}
        {button("右对齐", () => {
          editor
            .chain()
            .focus()
            .updateAttributes("paragraph", { align: "right" })
            .run();
        })}
        {button("分隔线", () => {
          editor.chain().focus().insertContent({ type: "divider" }).run();
        })}
        {button("提示框", () => {
          editor
            .chain()
            .focus()
            .insertContent({
              type: "callout",
              attrs: { tone: "info" },
              content: [
                {
                  type: "paragraph",
                  content: [{ type: "text", text: "到访提示" }],
                },
              ],
            })
            .run();
        })}
        {button("注意框", () => {
          editor
            .chain()
            .focus()
            .insertContent({
              type: "callout",
              attrs: { tone: "warning" },
              content: [
                {
                  type: "paragraph",
                  content: [{ type: "text", text: "请留意" }],
                },
              ],
            })
            .run();
        })}
        <button type="button" disabled={busy} onClick={() => insert("image")}>
          ＋ 图片
        </button>
        <button type="button" disabled={busy} onClick={() => insert("video")}>
          ＋ 视频
        </button>
        <button type="button" disabled={busy} onClick={() => insert("gallery")}>
          ＋ 图片组
        </button>
        {button("撤销", () => {
          editor.chain().focus().undo().run();
        })}
        {button("重做", () => {
          editor.chain().focus().redo().run();
        })}
      </fieldset>
      {linkInput !== null && (
        <div className="inline link-editor">
          <input
            aria-label="完整链接地址"
            placeholder="https://"
            value={linkInput}
            onChange={(event) => setLinkInput(event.target.value)}
          />
          <button
            type="button"
            onClick={() => {
              if (safeHref(linkInput)) {
                editor
                  .chain()
                  .focus()
                  .extendMarkRange("link")
                  .setLink({ href: linkInput })
                  .run();
                setLinkInput(null);
              } else onError("请输入完整的 http 或 https 链接。");
            }}
          >
            应用链接
          </button>
          <button
            type="button"
            onClick={() => {
              editor.chain().focus().unsetLink().run();
              setLinkInput(null);
            }}
          >
            移除链接
          </button>
          <button type="button" onClick={() => setLinkInput(null)}>
            取消
          </button>
        </div>
      )}
      <input
        ref={fileInput}
        hidden
        type="file"
        onChange={(event) => void addFiles(event.target.files)}
      />
      {busy && (
        <p className="notice" role="status">
          正在上传并处理媒体，完成后插入当前正文位置…
        </p>
      )}
      <EditorContent editor={editor} />
      <div className="word-count">
        {documentText(value).length.toLocaleString()} 字 ·
        正文内可拖动图片调整位置
      </div>
    </div>
  );
}
export function EditorialPreview({
  document,
  media,
}: {
  document: EditorialDocument;
  media: EditorialMedia[];
}) {
  const render = (node: EditorialNode, key: string): ReactNode => {
    const children = node.content?.map((child, index) =>
      render(child, `${key}-${index}`),
    );
    if (node.type === "text")
      return (node.marks ?? []).reduce<ReactNode>(
        (text, mark, index) =>
          mark.type === "bold" ? (
            <strong key={`${key}-${index}`}>{text}</strong>
          ) : mark.type === "italic" ? (
            <em key={`${key}-${index}`}>{text}</em>
          ) : mark.type === "strike" ? (
            <s key={`${key}-${index}`}>{text}</s>
          ) : mark.type === "link" && safeHref(mark.attrs.href) ? (
            <a
              key={`${key}-${index}`}
              href={mark.attrs.href}
              target="_blank"
              rel="noopener noreferrer"
            >
              {text}
            </a>
          ) : (
            text
          ),
        node.text,
      );
    if (node.type === "paragraph")
      return (
        <p key={key} style={{ textAlign: node.attrs?.align }}>
          {children?.length ? children : <br />}
        </p>
      );
    if (node.type === "heading")
      return node.attrs?.level === 3 ? (
        <h3 key={key}>{children}</h3>
      ) : (
        <h2 key={key}>{children}</h2>
      );
    if (node.type === "hardBreak") return <br key={key} />;
    if (node.type === "blockquote")
      return <blockquote key={key}>{children}</blockquote>;
    if (node.type === "bulletList") return <ul key={key}>{children}</ul>;
    if (node.type === "orderedList") return <ol key={key}>{children}</ol>;
    if (node.type === "listItem") return <li key={key}>{children}</li>;
    if (node.type === "divider") return <hr key={key} />;
    if (node.type === "callout")
      return (
        <aside key={key} className={`editor-callout ${node.attrs?.tone}`}>
          {children}
        </aside>
      );
    const figure = (
      id: string,
      caption?: string,
      credit?: string,
      alt?: string,
    ) => {
      const asset = media.find((item) => item.id === id);
      return (
        <figure key={id}>
          {asset?.url ? (
            asset.kind === "video" ? (
              <video
                controls
                preload="metadata"
                poster={asset.poster}
                src={asset.url}
              />
            ) : (
              <img src={asset.url} alt={alt ?? ""} />
            )
          ) : (
            <p className="notice">媒体暂不可用</p>
          )}
          {(caption || credit) && (
            <figcaption>
              {caption}
              {credit && <span> · {credit}</span>}
            </figcaption>
          )}
        </figure>
      );
    };
    if (node.type === "gallery")
      return (
        <div
          key={key}
          className={`gallery ${node.attrs?.layout} width-${node.attrs?.width}`}
        >
          {node.attrs?.items?.map((item) =>
            figure(item.asset_id, item.caption, item.credit, item.alt),
          )}
        </div>
      );
    if (node.type === "image" || node.type === "video")
      return (
        <div key={key} className={`width-${node.attrs?.width}`}>
          {figure(
            node.attrs?.asset_id ?? "",
            node.attrs?.caption,
            node.attrs?.credit,
            node.attrs?.alt,
          )}
        </div>
      );
    return null;
  };
  return (
    <div className="editor-prose editorial-preview">
      {document.content.map((node, index) => render(node, String(index)))}
    </div>
  );
}
