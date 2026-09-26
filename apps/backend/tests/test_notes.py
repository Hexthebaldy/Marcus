import asyncio
from uuid import uuid4

import pytest

from .helpers import decide_note, new_note, submit_note


async def test_text_only_note_publishes_without_cover_and_draft_is_private(api, location):
    author, reader, reviewer = await api.login(), await api.login(), await api.login("moderator")
    note_id, draft = await new_note(api, author, location["city_id"])
    assert (await api.client.get(f"/v1/notes/{note_id}/draft", headers=reader.headers)).status_code in (
        403,
        404,
    )
    assert (await api.client.get(f"/v1/notes/{note_id}", headers=reader.headers)).status_code == 404
    submission = await submit_note(api, author, note_id, draft)
    await decide_note(api, reviewer, submission["submission_id"])
    public = await api.request("GET", f"/notes/{note_id}", actor=reader)
    assert public["body_text"] == "上海今天的散步记录"
    assert public["cover"] is None and public["images"] == []
    assert public["title"] == ""
    assert "document" not in public


@pytest.mark.parametrize(
    "unsupported",
    [{"document": {"type": "doc", "content": []}}, {"cover_asset_id": None}, {"paragraph_style": "heading"}],
)
async def test_note_rejects_editorial_fields(api, location, unsupported):
    author = await api.login()
    note_id, draft = await new_note(api, author, location["city_id"])
    await api.request(
        "PATCH",
        f"/notes/{note_id}/draft",
        actor=author,
        body={"expected_version": draft["edit_version"], **unsupported},
        status=422,
    )


async def test_only_title_is_not_publishable(api, location):
    author = await api.login()
    note_id, draft = await new_note(api, author, location["city_id"], body_text=" \n ")
    draft = await api.request(
        "PATCH",
        f"/notes/{note_id}/draft",
        actor=author,
        body={"expected_version": draft["edit_version"], "title": "没有正文"},
    )
    response = await api.client.post(
        f"/v1/notes/{note_id}/publish",
        headers={**author.headers, "Idempotency-Key": str(uuid4())},
        json={"expected_edit_version": draft["edit_version"]},
    )
    assert response.status_code == 422, response.text


async def test_old_review_and_rejected_new_submission_preserve_original_public_note(api, location, db):
    author, reviewer = await api.login(), await api.login("moderator")
    note_id, draft = await new_note(api, author, location["city_id"], "已公开版本")
    first = await submit_note(api, author, note_id, draft)
    await decide_note(api, reviewer, first["submission_id"])
    original = await api.request("GET", f"/notes/{note_id}", actor=author)
    second_draft = await api.request(
        "PATCH",
        f"/notes/{note_id}/draft",
        actor=author,
        body={"expected_version": draft["edit_version"], "body_text": "第二次提交"},
    )
    second = await submit_note(api, author, note_id, second_draft)
    third_draft = await api.request(
        "PATCH",
        f"/notes/{note_id}/draft",
        actor=author,
        body={"expected_version": second_draft["edit_version"], "body_text": "第三次提交"},
    )
    third = await submit_note(api, author, note_id, third_draft)
    await decide_note(api, reviewer, second["submission_id"])
    assert (await api.request("GET", f"/notes/{note_id}", actor=author))["body_text"] == "已公开版本"
    await decide_note(api, reviewer, third["submission_id"], "reject")
    public = await api.request("GET", f"/notes/{note_id}", actor=author)
    assert public["body_text"] == "已公开版本"
    assert public["published_submission_id"] == first["submission_id"]
    assert public["first_published_at"] == original["first_published_at"]
    assert await db.scalar("SELECT COUNT(*) FROM note_submissions WHERE note_id=:id", {"id": note_id}) == 3


async def test_parallel_save_only_one_writer_succeeds(api, location):
    author = await api.login()
    note_id, draft = await new_note(api, author, location["city_id"])

    async def save(body):
        return await api.client.patch(
            f"/v1/notes/{note_id}/draft",
            headers=author.headers,
            json={"expected_version": draft["edit_version"], "body_text": body},
        )

    responses = await asyncio.gather(save("来自设备A"), save("来自设备B"))
    assert sorted(r.status_code for r in responses) == [200, 409]
    latest = await api.request("GET", f"/notes/{note_id}/draft", actor=author)
    assert latest["edit_version"] == draft["edit_version"] + 1
    assert latest["body_text"] in ("来自设备A", "来自设备B")


async def test_parallel_publish_is_idempotent_in_mysql(api, location, db):
    author = await api.login()
    note_id, draft = await new_note(api, author, location["city_id"])
    key = str(uuid4())
    first, second = await asyncio.gather(
        submit_note(api, author, note_id, draft, key), submit_note(api, author, note_id, draft, key)
    )
    assert first["submission_id"] == second["submission_id"]
    assert first["job_id"] == second["job_id"]
    assert await db.scalar("SELECT COUNT(*) FROM note_submissions WHERE note_id=:id", {"id": note_id}) == 1
    assert await db.scalar("SELECT COUNT(*) FROM jobs WHERE kind='review_note'") == 1


async def test_parallel_publish_with_different_keys_reuses_same_draft_submission(api, location, db):
    author = await api.login()
    note_id, draft = await new_note(api, author, location["city_id"])
    first, second = await asyncio.gather(
        submit_note(api, author, note_id, draft, str(uuid4())),
        submit_note(api, author, note_id, draft, str(uuid4())),
    )
    assert first["submission_id"] == second["submission_id"]
    assert await db.scalar("SELECT COUNT(*) FROM note_submissions WHERE note_id=:id", {"id": note_id}) == 1


async def test_idempotency_key_cannot_be_reused_for_different_request(api, location):
    author = await api.login()
    note_id, draft = await new_note(api, author, location["city_id"])
    key = str(uuid4())
    await submit_note(api, author, note_id, draft, key)
    updated = await api.request(
        "PATCH",
        f"/notes/{note_id}/draft",
        actor=author,
        body={"expected_version": draft["edit_version"], "body_text": "新的提交"},
    )
    await api.request(
        "POST",
        f"/notes/{note_id}/publish",
        actor=author,
        body={"expected_edit_version": updated["edit_version"]},
        key=key,
        status=409,
    )


async def test_parallel_review_decision_changes_publication_once(api, location, db):
    author, reviewer_a, reviewer_b = (
        await api.login(),
        await api.login("moderator"),
        await api.login("moderator"),
    )
    note_id, draft = await new_note(api, author, location["city_id"])
    submission = await submit_note(api, author, note_id, draft)
    submission_id = submission["submission_id"]
    pending = await api.request("GET", f"/admin/note-submissions/{submission_id}", actor=reviewer_a)
    body = {
        "decision": "approve",
        "expected_review_version": pending["review_version"],
        "reason_code": None,
        "note": "parallel",
    }
    responses = await asyncio.gather(
        api.client.post(
            f"/v1/admin/note-submissions/{submission_id}/decision", headers=reviewer_a.headers, json=body
        ),
        api.client.post(
            f"/v1/admin/note-submissions/{submission_id}/decision", headers=reviewer_b.headers, json=body
        ),
    )
    assert sorted(r.status_code for r in responses) == [200, 409]
    assert (
        await db.scalar("SELECT review_version FROM note_submissions WHERE id=:id", {"id": submission_id})
        == pending["review_version"] + 1
    )
    assert (
        await db.scalar("SELECT published_submission_id FROM notes WHERE id=:id", {"id": note_id})
        == submission_id
    )


async def test_hidden_note_cannot_be_republished_by_late_approval(api, location):
    author, reviewer = await api.login(), await api.login("moderator")
    note_id, draft = await new_note(api, author, location["city_id"])
    first = await submit_note(api, author, note_id, draft)
    await decide_note(api, reviewer, first["submission_id"])
    public = await api.request("GET", f"/notes/{note_id}", actor=author)
    draft = await api.request(
        "PATCH",
        f"/notes/{note_id}/draft",
        actor=author,
        body={"expected_version": draft["edit_version"], "body_text": "等待审核"},
    )
    pending = await submit_note(api, author, note_id, draft)
    await api.request(
        "POST",
        f"/admin/notes/{note_id}/hide",
        actor=reviewer,
        body={"expected_version": public["version"], "reason": "integration hide"},
    )
    await decide_note(api, reviewer, pending["submission_id"])
    assert (await api.client.get(f"/v1/notes/{note_id}", headers=author.headers)).status_code == 404
