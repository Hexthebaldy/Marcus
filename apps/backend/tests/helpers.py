from uuid import uuid4


def object_id(payload, kind):
    return payload.get(f"{kind}_id") or payload["id"]


async def new_note(api, actor, city_id, body_text="上海今天的散步记录"):
    created = await api.request(
        "POST", "/notes", actor=actor, body={"city_id": city_id}, status=201, key=str(uuid4())
    )
    note_id = object_id(created, "note")
    draft = await api.request("GET", f"/notes/{note_id}/draft", actor=actor)
    draft = await api.request(
        "PATCH",
        f"/notes/{note_id}/draft",
        actor=actor,
        body={"expected_version": draft["edit_version"], "body_text": body_text},
    )
    return note_id, draft


async def submit_note(api, actor, note_id, draft, key=None):
    return await api.request(
        "POST",
        f"/notes/{note_id}/publish",
        actor=actor,
        body={"expected_edit_version": draft["edit_version"]},
        status=202,
        key=key or str(uuid4()),
    )


async def decide_note(api, reviewer, submission_id, decision="approve"):
    item = await api.request("GET", f"/admin/note-submissions/{submission_id}", actor=reviewer)
    return await api.request(
        "POST",
        f"/admin/note-submissions/{submission_id}/decision",
        actor=reviewer,
        body={
            "decision": decision,
            "expected_review_version": item["review_version"],
            "reason_code": "test_rejected" if decision == "reject" else None,
            "note": "integration review",
        },
    )


async def new_place(api, editor, location, name="测试书店"):
    return await api.request(
        "POST",
        "/admin/places",
        actor=editor,
        body={
            **location,
            "name": name,
            "address": "上海市静安区测试路1号",
            "summary": "一家独立书店",
            "opening_hours_text": "每天10:00-20:00",
            "transport_notes": "步行可达",
            "status": "active",
            "cover_asset_id": None,
        },
        status=201,
    )


def document(text="正文介绍这家书店。"):
    return {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]}


async def new_editorial(api, editor, location, *, place_id=None, event_id=None, text="正文介绍这家书店。"):
    created = await api.request(
        "POST", "/admin/editorials", actor=editor, body=location, status=201, key=str(uuid4())
    )
    article_id = object_id(created, "article")
    draft = await api.request("GET", f"/admin/editorials/{article_id}/draft", actor=editor)
    draft = await api.request(
        "PATCH",
        f"/admin/editorials/{article_id}/draft",
        actor=editor,
        body={
            "expected_version": draft["edit_version"],
            "title": "上海周末精选",
            "summary": "",
            "focus_type": "event" if event_id else "place",
            "primary_place_id": place_id,
            "primary_event_id": event_id,
            "document": document(text),
            "document_schema_version": 1,
            "cover_asset_id": None,
            "tag_ids": [],
        },
    )
    return article_id, draft


async def submit_editorial(api, editor, article_id, draft, key=None):
    return await api.request(
        "POST",
        f"/admin/editorials/{article_id}/publish",
        actor=editor,
        body={"expected_edit_version": draft["edit_version"]},
        status=202,
        key=key or str(uuid4()),
    )


async def decide_editorial(api, reviewer, revision_id, decision="approve"):
    review_id = await api.db.scalar(
        "SELECT id FROM editor_reviews WHERE revision_id=:id", {"id": revision_id}
    )
    item = await api.request("GET", f"/admin/editorial-reviews/{review_id}", actor=reviewer)
    version = item.get("version") or item.get("review_version")
    return await api.request(
        "POST",
        f"/admin/editorial-reviews/{review_id}/decision",
        actor=reviewer,
        body={
            "decision": decision,
            "expected_review_version": version,
            "reason_code": "test_rejected" if decision == "reject" else None,
            "note": "integration review",
        },
    )
