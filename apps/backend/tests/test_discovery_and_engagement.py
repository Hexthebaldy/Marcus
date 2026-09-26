from uuid import uuid4

from .helpers import (
    decide_editorial,
    decide_note,
    new_editorial,
    new_note,
    new_place,
    submit_editorial,
    submit_note,
)


async def test_web_session_cookie_origin_guard_and_refresh(api):
    from marcus.config import settings

    _, challenge_id, code = await api.challenge()
    body = {"challenge_id": challenge_id, "code": code, "device_label": "web", "client_type": "editor_web"}
    untrusted = await api.client.post(
        "/v1/auth/verify", json=body, headers={"Origin": "https://elsewhere.invalid"}
    )
    assert untrusted.status_code == 403
    origin = settings.origins[0]
    result = await api.client.post("/v1/auth/verify", json=body, headers={"Origin": origin})
    assert result.status_code == 200
    assert "refresh_token" not in result.json()
    cookie = result.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie and "Path=/v1/auth" in cookie
    headers = {"Authorization": f"Bearer {result.json()['access_token']}"}
    assert (await api.client.patch("/v1/me", json={"bio": "blocked"}, headers=headers)).status_code == 403
    headers["Origin"] = origin
    assert (await api.client.patch("/v1/me", json={"bio": "saved"}, headers=headers)).status_code == 200
    assert (await api.client.post("/v1/auth/refresh", json={})).status_code == 403
    refreshed = await api.client.post("/v1/auth/refresh", json={}, headers={"Origin": origin})
    assert refreshed.status_code == 200 and "refresh_token" not in refreshed.json()
    assert refreshed.headers["set-cookie"] != cookie


async def test_discovery_reactions_bookmarks_reporting_and_blocking(api, db, location):
    author, reader, reviewer = await api.login(), await api.login(), await api.login("moderator")
    note_id, draft = await new_note(api, author, location["city_id"])
    sub = await submit_note(api, author, note_id, draft)
    await decide_note(api, reviewer, sub["submission_id"])
    feed = await api.request("GET", f"/discover/notes?city_id={location['city_id']}", actor=reader)
    assert [item["id"] for item in feed["items"]] == [note_id]
    for _ in range(2):
        reaction = await api.request("PUT", f"/notes/{note_id}/reactions/like", actor=reader)
        assert reaction["like_count"] == 1 and reaction["liked"]
    await api.request("PUT", f"/notes/{note_id}/reactions/bookmark", actor=reader)
    bookmarks = await api.request("GET", "/me/bookmarks", actor=reader)
    assert bookmarks["items"][0]["content_type"] == "note"
    assert bookmarks["items"][0]["content"]["id"] == note_id
    report = await api.request(
        "POST",
        f"/notes/{note_id}/reports",
        actor=reader,
        body={
            "submission_id": sub["submission_id"],
            "reason": "inaccurate",
            "description": "资料需要核实",
        },
        status=201,
    )
    report_id = report["id"]
    await api.request(
        "PATCH",
        f"/admin/note-reports/{report_id}",
        actor=reviewer,
        body={"status": "resolved", "resolution_note": "已经核实"},
    )
    assert await db.scalar("SELECT status FROM note_reports WHERE id=:id", {"id": report_id}) == "resolved"
    await api.request("PUT", f"/users/{author.id}/block", actor=reader, status=204)
    assert not (await api.request("GET", f"/discover/notes?city_id={location['city_id']}", actor=reader))[
        "items"
    ]
    await api.request("GET", f"/notes/{note_id}", actor=reader, status=404)
    await api.request("DELETE", f"/users/{author.id}/block", actor=reader, status=204)
    await api.request("GET", f"/notes/{note_id}", actor=reader)


async def test_article_district_and_tags_follow_publication_not_working_draft(api, db, location):
    editor, reviewer = await api.login("editor"), await api.login("moderator")
    other_district = str(uuid4())
    await db.execute(
        "INSERT INTO districts (id,city_id,code,name,created_at,updated_at) VALUES (:id,:city,'second','徐汇区',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6))",
        {"id": other_district, "city": location["city_id"]},
    )
    old_place = await new_place(api, editor, location)
    new_place_info = await new_place(api, editor, {**location, "district_id": other_district}, "另一家店")
    tag = await api.request(
        "POST", "/admin/tags", actor=editor, body={"slug": "weekend", "name": "周末"}, status=201
    )
    article_id, draft = await new_editorial(api, editor, location, place_id=old_place["id"])
    submitted = await submit_editorial(api, editor, article_id, draft)
    await decide_editorial(api, reviewer, submitted["revision_id"])
    draft = await api.request(
        "PATCH",
        f"/admin/editorials/{article_id}/draft",
        actor=editor,
        body={
            "expected_version": draft["edit_version"],
            "focus_type": "place",
            "primary_place_id": new_place_info["id"],
            "primary_event_id": None,
            "tag_ids": [tag["id"]],
        },
    )
    public = await api.request("GET", f"/editorials/{article_id}", actor=editor)
    assert public["district"]["id"] == location["district_id"] and public["tags"] == []
    submitted = await submit_editorial(api, editor, article_id, draft)
    await decide_editorial(api, reviewer, submitted["revision_id"])
    public = await api.request("GET", f"/editorials/{article_id}", actor=editor)
    assert public["district"]["id"] == other_district and public["tags"][0]["id"] == tag["id"]
    filtered = await api.request(
        "GET",
        f"/discover/editorials?city_id={location['city_id']}&district_id={location['district_id']}",
        actor=editor,
    )
    assert filtered["items"] == []
    await api.request(
        "GET",
        f"/discover/editorials?city_id={location['city_id']}&district_id={uuid4()}",
        actor=editor,
        status=404,
    )


async def test_account_deletion_revokes_sessions_and_hides_public_content(api, db, location):
    author, reader, reviewer = await api.login(), await api.login(), await api.login("moderator")
    note_id, draft = await new_note(api, author, location["city_id"])
    submitted = await submit_note(api, author, note_id, draft)
    await decide_note(api, reviewer, submitted["submission_id"])
    _, challenge_id, code = await api.challenge(author.email, purpose="delete_account", actor=author)
    await api.request(
        "DELETE", "/me", actor=author, body={"challenge_id": challenge_id, "code": code}, status=204
    )
    await api.request("GET", "/me", actor=author, status=401)
    await api.request("GET", f"/notes/{note_id}", actor=reader, status=404)
    row = (
        await db.rows(
            "SELECT status,email_ciphertext,email_lookup_hash FROM users WHERE id=:id", {"id": author.id}
        )
    )[0]
    assert row["status"] == "deleted" and row["email_ciphertext"] is None and row["email_lookup_hash"] is None
