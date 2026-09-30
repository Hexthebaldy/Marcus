"""Strict, portable editorial blocks; never interpret arbitrary HTML."""

import json
from urllib.parse import urlsplit
from uuid import UUID


def validate_document(doc):
    if (
        not isinstance(doc, dict)
        or set(doc) - {"type", "content"}
        or doc.get("type") != "doc"
        or not isinstance(doc.get("content"), list)
    ):
        raise ValueError("invalid document")
    if len(json.dumps(doc, ensure_ascii=False).encode()) > 512 * 1024:
        raise ValueError("document exceeds 512KB")
    count = 0
    texts = []
    media = {}
    videos = 0

    def fields(obj, allowed):
        if not isinstance(obj, dict) or set(obj) - set(allowed):
            raise ValueError("unsupported attributes")

    def caption(a):
        for key in ["alt", "caption", "credit"]:
            if key in a and (not isinstance(a[key], str) or len(a[key]) > 1000):
                raise ValueError("invalid media caption")

    def asset(a, kind):
        nonlocal videos
        value = a.get("asset_id")
        UUID(value)
        if value in media and media[value] != kind:
            raise ValueError("media type conflict")
        media[value] = kind
        videos += kind == "video"

    def walk(node, depth, parent):
        nonlocal count
        count += 1
        if count > 2000 or depth > 6:
            raise ValueError("document too complex")
        fields(node, {"type", "attrs", "content", "text", "marks"})
        t = node.get("type")
        a = node.get("attrs", {})
        children = node.get("content", [])
        allowed = {
            "doc": {
                "paragraph",
                "heading",
                "blockquote",
                "bulletList",
                "orderedList",
                "image",
                "video",
                "gallery",
                "callout",
                "divider",
            },
            "paragraph": {"text", "hardBreak"},
            "heading": {"text", "hardBreak"},
            "blockquote": {"paragraph"},
            "callout": {"paragraph"},
            "bulletList": {"listItem"},
            "orderedList": {"listItem"},
            "listItem": {"paragraph"},
        }
        if t not in allowed.get(parent, set()):
            raise ValueError("unsupported or nested block")
        if not isinstance(children, list):
            raise ValueError("content must be array")
        if t == "text":
            if set(node) - {"type", "text", "marks"} or not isinstance(node.get("text"), str):
                raise ValueError("invalid text")
            texts.append(node["text"])
            for m in node.get("marks", []):
                fields(m, {"type", "attrs"})
                if m.get("type") not in {"bold", "italic", "strike", "link"}:
                    raise ValueError("unsupported mark")
                if m["type"] == "link":
                    fields(m.get("attrs", {}), {"href"})
                    href = m.get("attrs", {}).get("href", "")
                    if (
                        not isinstance(href, str)
                        or len(href) > 2048
                        or urlsplit(href).scheme not in ("http", "https")
                        or not urlsplit(href).netloc
                    ):
                        raise ValueError("unsafe link")
                elif m.get("attrs"):
                    raise ValueError("unsupported mark attrs")
            return
        if "text" in node or "marks" in node:
            raise ValueError("only text accepts text and marks")
        if t in ("image", "video"):
            fields(
                a,
                {"asset_id", "alt", "caption", "credit", "width"}
                if t == "image"
                else {"asset_id", "caption", "credit", "width"},
            )
            caption(a)
            asset(a, t)
        elif t == "gallery":
            fields(a, {"items", "layout", "width"})
            if (
                a.get("layout") not in {"single", "two_column"}
                or not isinstance(a.get("items"), list)
                or not 1 <= len(a["items"]) <= 20
            ):
                raise ValueError("invalid gallery")
            for item in a["items"]:
                fields(item, {"asset_id", "alt", "caption", "credit"})
                caption(item)
                asset(item, "image")
        elif t == "paragraph":
            fields(a, {"align"})
            if a.get("align", "left") not in {"left", "center", "right"}:
                raise ValueError("invalid alignment")
        elif t == "heading":
            fields(a, {"level"})
            if a.get("level") not in (2, 3):
                raise ValueError("invalid heading")
        elif t == "callout":
            fields(a, {"tone"})
            if a.get("tone") not in {"info", "warning"}:
                raise ValueError("invalid callout")
        else:
            fields(a, set())
        if t in {"image", "video", "gallery"} and a.get("width", "content") not in {
            "content",
            "wide",
            "full",
        }:
            raise ValueError("invalid width")
        if t not in allowed and children:
            raise ValueError("leaf has children")
        for child in children:
            walk(child, depth + 1, t)

    for n in doc["content"]:
        walk(n, 1, "doc")
    plain = "\n".join(texts)
    if len(plain) > 20000 or videos > 5 or sum(k == "image" for k in media.values()) > 20:
        raise ValueError("article exceeds limits")
    return plain, media
