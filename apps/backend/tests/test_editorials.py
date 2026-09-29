import asyncio
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from .helpers import decide_editorial, document, new_editorial, new_place, object_id, submit_editorial


async def test_place_editorial_needs_no_event_or_cover_and_generates_summary(api, location, db):
    editor, reviewer, reader = await api.login("editor"), await api.login("moderator"), await api.login()
    place = await new_place(api, editor, location)
    article_id, draft = await new_editorial(api, editor, location, place_id=object_id(place, "place"))
    submitted = await submit_editorial(api, editor, article_id, draft)
    await decide_editorial(api, reviewer, submitted["revision_id"])
    public = await api.request("GET", f"/editorials/{article_id}", actor=reader)
    assert public["focus_type"] == "place"
    assert public["place"]["id"] == object_id(place, "place")
    assert public["event"] is None and public["cover"] is None
    assert public["summary"] and len(public["summary"]) <= 500
    assert public["document"] == document()
    assert await db.scalar("SELECT COUNT(*) FROM events") == 0
    assert await db.scalar("SELECT COUNT(*) FROM notes") == 0


async def test_event_editorial_can_publish_with_unknown_venue(api, location):
    editor, reviewer = await api.login("editor"), await api.login("moderator")
    event = await api.request(
        "POST",
        "/admin/events",
        actor=editor,
        body={
            "city_id": location["city_id"],
            "title": "上海新演出",
            "description": "场地尚未公布",
            "place_id": None,
            "price_status": "unknown",
            "price_min_fen": None,
            "price_max_fen": None,
            "currency": "CNY",
            "status": "published",
        },
        status=201,
    )
    event_id = object_id(event, "event")
    article_id, draft = await new_editorial(
        api, editor, location, event_id=event_id, text="介绍演出作品和演员，场地稍后公布。"
    )
    submitted = await submit_editorial(api, editor, article_id, draft)
    await decide_editorial(api, reviewer, submitted["revision_id"])
    public = await api.request("GET", f"/editorials/{article_id}", actor=editor)
    assert public["focus_type"] == "event"
    assert public["event"]["id"] == event_id
    assert public["place"] is None and public["cover"] is None


async def test_editorial_rejects_two_primary_objects_and_partial_focus_switch(api, location):
    editor = await api.login("editor")
    place = await new_place(api, editor, location)
    article_id, draft = await new_editorial(api, editor, location, place_id=object_id(place, "place"))
    await api.request(
        "PATCH",
        f"/admin/editorials/{article_id}/draft",
        actor=editor,
        body={"expected_version": draft["edit_version"], "focus_type": "event"},
        status=422,
    )
    await api.request(
        "PATCH",
        f"/admin/editorials/{article_id}/draft",
        actor=editor,
        body={
            "expected_version": draft["edit_version"],
            "focus_type": "place",
            "primary_place_id": object_id(place, "place"),
            "primary_event_id": str(uuid4()),
        },
        status=422,
    )
    current = await api.request("GET", f"/admin/editorials/{article_id}/draft", actor=editor)
    assert current["focus_type"] == "place" and current["primary_event_id"] is None
    assert current["edit_version"] == draft["edit_version"]


@pytest.mark.parametrize(
    "node",
    [
        {"type": "iframe", "attrs": {"src": "https://example.com"}},
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": "链接",
                    "marks": [{"type": "link", "attrs": {"href": "javascript:alert(1)"}}],
                }
            ],
        },
        {
            "type": "image",
            "attrs": {"asset_id": str(uuid4()), "width": "absolute", "alt": "", "caption": "", "credit": ""},
        },
    ],
)
async def test_editorial_rejects_unsafe_or_unsupported_nodes(api, location, node):
    editor = await api.login("editor")
    place = await new_place(api, editor, location)
    article_id, draft = await new_editorial(api, editor, location, place_id=object_id(place, "place"))
    await api.request(
        "PATCH",
        f"/admin/editorials/{article_id}/draft",
        actor=editor,
        body={"expected_version": draft["edit_version"], "document": {"type": "doc", "content": [node]}},
        status=422,
    )


async def test_editorial_old_review_does_not_change_public_version(api, location):
    editor, reviewer = await api.login("editor"), await api.login("moderator")
    place = await new_place(api, editor, location)
    article_id, draft = await new_editorial(api, editor, location, place_id=object_id(place, "place"))
    first = await submit_editorial(api, editor, article_id, draft)
    await decide_editorial(api, reviewer, first["revision_id"])
    submitted_versions = []
    for content in ("第二个版本", "第三个版本"):
        draft = await api.request(
            "PATCH",
            f"/admin/editorials/{article_id}/draft",
            actor=editor,
            body={"expected_version": draft["edit_version"], "document": document(content)},
        )
        submitted = await submit_editorial(api, editor, article_id, draft)
        submitted_versions.append(submitted)
    second, third = submitted_versions
    await decide_editorial(api, reviewer, second["revision_id"])
    public = await api.request("GET", f"/editorials/{article_id}", actor=editor)
    assert public["revision_id"] == first["revision_id"]
    await decide_editorial(api, reviewer, third["revision_id"])
    public = await api.request("GET", f"/editorials/{article_id}", actor=editor)
    assert public["revision_id"] == third["revision_id"]
    assert public["document"] == document("第三个版本")


async def test_parallel_editorial_publish_creates_one_revision(api, location, db):
    editor = await api.login("editor")
    place = await new_place(api, editor, location)
    article_id, draft = await new_editorial(api, editor, location, place_id=object_id(place, "place"))
    key = str(uuid4())
    first, second = await asyncio.gather(
        submit_editorial(api, editor, article_id, draft, key),
        submit_editorial(api, editor, article_id, draft, key),
    )
    assert first["revision_id"] == second["revision_id"]
    assert (
        await db.scalar("SELECT COUNT(*) FROM editor_revisions WHERE article_id=:id", {"id": article_id}) == 1
    )


async def test_cross_city_district_rejected_by_api_and_mysql(api, location, db):
    editor = await api.login("editor")
    other_city = str(uuid4())
    await db.execute(
        "INSERT INTO cities (id,code,name,country_code,timezone,enabled,created_at,updated_at) VALUES (:id,'other-test','其他城市','CN','Asia/Shanghai',1,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6))",
        {"id": other_city},
    )
    response = await api.client.post(
        "/v1/admin/places",
        headers=editor.headers,
        json={
            "city_id": other_city,
            "district_id": location["district_id"],
            "name": "跨城错误",
            "address": "错误地址",
            "opening_hours_text": "",
            "summary": "",
            "transport_notes": "",
            "status": "active",
        },
    )
    assert response.status_code == 422, response.text
    place = await new_place(api, editor, location)
    with pytest.raises(IntegrityError):
        await db.execute(
            "UPDATE places SET city_id=:city WHERE id=:id",
            {"city": other_city, "id": object_id(place, "place")},
        )
    response = await api.client.post(
        "/v1/admin/editorials",
        headers={**editor.headers, "Idempotency-Key": str(uuid4())},
        json={"city_id": other_city, "district_id": location["district_id"]},
    )
    assert response.status_code == 422, response.text
