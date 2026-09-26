from uuid import uuid4

from .helpers import (
    decide_editorial,
    decide_note,
    document,
    new_editorial,
    new_note,
    new_place,
    object_id,
    submit_editorial,
    submit_note,
)


async def test_private_note_media_acl_and_review_context(api, location, asset_factory):
    owner, stranger = await api.login(), await api.login()
    editor, moderator = await api.login("editor"), await api.login("moderator")
    image_id = await asset_factory(owner)
    owner_response = await api.request("GET", f"/media/{image_id}", actor=owner)
    assert owner_response["id"] == image_id
    for actor in (stranger, editor, moderator):
        response = await api.client.get(f"/v1/media/{image_id}", headers=actor.headers)
        assert response.status_code in (403, 404), response.text
    note_id, draft = await new_note(api, owner, location["city_id"])
    draft = await api.request(
        "PATCH",
        f"/notes/{note_id}/draft",
        actor=owner,
        body={"expected_version": draft["edit_version"], "image_ids": [image_id]},
    )
    submission = await submit_note(api, owner, note_id, draft)
    review = await api.request(
        "GET", f"/admin/note-submissions/{submission['submission_id']}", actor=moderator
    )
    assert image_id in str(review)
    assert "http" in str(review), "Review response must contain authorized short-lived media URLs"
    assert (await api.client.get(f"/v1/media/{image_id}", headers=moderator.headers)).status_code in (
        403,
        404,
    )
    await decide_note(api, moderator, submission["submission_id"])
    public = await api.request("GET", f"/notes/{note_id}", actor=stranger)
    assert public["images"][0]["id"] == image_id


async def test_note_image_order_and_pure_image_post(api, location, asset_factory):
    author, reviewer = await api.login(), await api.login("moderator")
    images = [await asset_factory(author), await asset_factory(author), await asset_factory(author)]
    note_id, draft = await new_note(api, author, location["city_id"], body_text="")
    chosen_order = [images[2], images[0], images[1]]
    draft = await api.request(
        "PATCH",
        f"/notes/{note_id}/draft",
        actor=author,
        body={"expected_version": draft["edit_version"], "image_ids": chosen_order},
    )
    submitted = await submit_note(api, author, note_id, draft)
    await decide_note(api, reviewer, submitted["submission_id"])
    public = await api.request("GET", f"/notes/{note_id}", actor=author)
    assert [image["id"] for image in public["images"]] == chosen_order
    assert public["cover"]["id"] == chosen_order[0]
    assert public["body_text"] == ""


async def test_note_cannot_reference_another_users_image_or_a_video(api, location, asset_factory):
    author, other, editor = await api.login(), await api.login(), await api.login("editor")
    foreign_image = await asset_factory(other)
    video = await asset_factory(editor, kind="video", purpose="editorial_media")
    note_id, draft = await new_note(api, author, location["city_id"])
    for asset_id in (foreign_image, video):
        response = await api.client.patch(
            f"/v1/notes/{note_id}/draft",
            headers=author.headers,
            json={"expected_version": draft["edit_version"], "image_ids": [asset_id]},
        )
        assert response.status_code in (403, 404, 422), response.text
    current = await api.request("GET", f"/notes/{note_id}/draft", actor=author)
    assert current["image_ids"] == []


async def test_editorial_preserves_inline_image_video_and_link_without_cover(api, location, asset_factory):
    editor, reviewer = await api.login("editor"), await api.login("moderator")
    place = await new_place(api, editor, location)
    image_id = await asset_factory(editor, purpose="editorial_media")
    video_id = await asset_factory(editor, kind="video", purpose="editorial_media")
    article_id, draft = await new_editorial(api, editor, location, place_id=object_id(place, "place"))
    rich = document("开篇介绍。")
    rich["content"] += [
        {
            "type": "image",
            "attrs": {
                "asset_id": image_id,
                "alt": "书店入口",
                "caption": "入口图",
                "credit": "编辑摄影",
                "width": "wide",
            },
        },
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": "预约链接",
                    "marks": [{"type": "link", "attrs": {"href": "https://example.com/booking"}}],
                }
            ],
        },
        {
            "type": "video",
            "attrs": {"asset_id": video_id, "caption": "空间导览", "credit": "团队制作", "width": "content"},
        },
        {"type": "paragraph", "content": [{"type": "text", "text": "结尾交通说明。"}]},
    ]
    draft = await api.request(
        "PATCH",
        f"/admin/editorials/{article_id}/draft",
        actor=editor,
        body={"expected_version": draft["edit_version"], "document": rich},
    )
    submitted = await submit_editorial(api, editor, article_id, draft)
    await decide_editorial(api, reviewer, submitted["revision_id"])
    public = await api.request("GET", f"/editorials/{article_id}", actor=editor)
    assert public["document"] == rich
    assert public["cover"] is None
    assert {a["id"] for a in public["media"]} == {image_id, video_id}


async def test_unprocessed_video_blocks_editorial_submission(api, location, asset_factory):
    editor = await api.login("editor")
    place = await new_place(api, editor, location)
    video_id = await asset_factory(editor, kind="video", purpose="editorial_media", status="processing")
    article_id, draft = await new_editorial(api, editor, location, place_id=object_id(place, "place"))
    rich = document()
    rich["content"].append(
        {"type": "video", "attrs": {"asset_id": video_id, "caption": "", "credit": "", "width": "content"}}
    )
    draft = await api.request(
        "PATCH",
        f"/admin/editorials/{article_id}/draft",
        actor=editor,
        body={"expected_version": draft["edit_version"], "document": rich},
    )
    response = await api.client.post(
        f"/v1/admin/editorials/{article_id}/publish",
        headers={**editor.headers, "Idempotency-Key": str(uuid4())},
        json={"expected_edit_version": draft["edit_version"]},
    )
    assert response.status_code in (409, 422), response.text


async def test_referenced_asset_cannot_be_deleted(api, location, asset_factory):
    owner = await api.login()
    image_id = await asset_factory(owner)
    note_id, draft = await new_note(api, owner, location["city_id"])
    await api.request(
        "PATCH",
        f"/notes/{note_id}/draft",
        actor=owner,
        body={"expected_version": draft["edit_version"], "image_ids": [image_id]},
    )
    await api.request("DELETE", f"/media/{image_id}", actor=owner, status=409)
