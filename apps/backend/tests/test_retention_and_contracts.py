from .helpers import decide_note, new_note, new_place, submit_note


async def test_retention_removes_expired_secrets_and_keeps_referenced_media(api, db, location, asset_factory):
    from marcus.jobs.worker import sweep_retention

    author = await api.login()
    orphan = await asset_factory(author)
    retained = await asset_factory(author)
    note_id, draft = await new_note(api, author, location["city_id"])
    await api.request(
        "PATCH",
        f"/notes/{note_id}/draft",
        actor=author,
        body={
            "expected_version": draft["edit_version"],
            "image_ids": [retained],
        },
    )
    await db.execute("UPDATE media_assets SET created_at=UTC_TIMESTAMP(6)-INTERVAL 2 DAY")
    await db.execute("UPDATE auth_challenges SET expires_at=UTC_TIMESTAMP(6)-INTERVAL 2 DAY")
    await db.execute("UPDATE idempotency_records SET expires_at=UTC_TIMESTAMP(6)-INTERVAL 1 SECOND")
    await sweep_retention()
    assert await db.scalar("SELECT COUNT(*) FROM auth_challenges") == 0
    assert await db.scalar("SELECT COUNT(*) FROM idempotency_records") == 0
    assert await db.scalar("SELECT status FROM media_assets WHERE id=:id", {"id": orphan}) == "deleted"
    assert await db.scalar("SELECT status FROM media_assets WHERE id=:id", {"id": retained}) == "ready"
    assert (
        await db.scalar("SELECT COUNT(*) FROM jobs WHERE kind='cleanup' AND target_id=:id", {"id": orphan})
        == 1
    )


async def test_deleted_note_retains_then_cleans_payload_and_releases_media(api, db, location, asset_factory):
    from marcus.jobs.worker import claim_job, execute_job, sweep_retention

    author, reviewer = await api.login(), await api.login("moderator")
    image = await asset_factory(author)
    note_id, draft = await new_note(api, author, location["city_id"])
    draft = await api.request(
        "PATCH",
        f"/notes/{note_id}/draft",
        actor=author,
        body={
            "expected_version": draft["edit_version"],
            "image_ids": [image],
        },
    )
    submitted = await submit_note(api, author, note_id, draft)
    await decide_note(api, reviewer, submitted["submission_id"])
    note = await api.request("GET", f"/notes/{note_id}", actor=author)
    await api.request(
        "DELETE", f"/notes/{note_id}", actor=author, body={"expected_version": note["version"]}, status=204
    )
    await db.execute("UPDATE jobs SET status='cancelled' WHERE kind!='cleanup'")
    job = await claim_job("cleanup-worker")
    await execute_job(job)
    assert await db.scalar("SELECT body_text FROM notes WHERE id=:id", {"id": note_id})
    assert await db.scalar("SELECT attempts FROM jobs WHERE id=:id", {"id": job["id"]}) == 0
    await db.execute(
        "UPDATE notes SET deleted_at=UTC_TIMESTAMP(6)-INTERVAL 31 DAY WHERE id=:id", {"id": note_id}
    )
    await db.execute(
        "UPDATE jobs SET available_at=UTC_TIMESTAMP(6)-INTERVAL 1 SECOND WHERE id=:id", {"id": job["id"]}
    )
    await execute_job(await claim_job("cleanup-worker"))
    assert await db.scalar("SELECT body_text FROM notes WHERE id=:id", {"id": note_id}) == ""
    assert await db.scalar("SELECT COUNT(*) FROM note_drafts WHERE note_id=:id", {"id": note_id}) == 0
    await db.execute(
        "UPDATE media_assets SET created_at=UTC_TIMESTAMP(6)-INTERVAL 31 DAY WHERE id=:id", {"id": image}
    )
    await sweep_retention()
    assert await db.scalar("SELECT status FROM media_assets WHERE id=:id", {"id": image}) == "deleted"


async def test_note_dynamic_venue_changes_without_rewriting_submission(api, db, location):
    editor, author, reviewer = await api.login("editor"), await api.login(), await api.login("moderator")
    old = await new_place(api, editor, location, "旧场地")
    new = await new_place(api, editor, location, "新场地")
    event = await api.request(
        "POST",
        "/admin/events",
        actor=editor,
        body={
            "city_id": location["city_id"],
            "title": "场馆调整",
            "place_id": old["id"],
            "status": "published",
        },
        status=201,
    )
    note_id, draft = await new_note(api, author, location["city_id"])
    draft = await api.request(
        "PATCH",
        f"/notes/{note_id}/draft",
        actor=author,
        body={
            "expected_version": draft["edit_version"],
            "event_id": event["id"],
            "place_id": None,
        },
    )
    submitted = await submit_note(api, author, note_id, draft)
    await decide_note(api, reviewer, submitted["submission_id"])
    await api.request(
        "PATCH",
        f"/admin/events/{event['id']}",
        actor=editor,
        body={"expected_version": event["version"], "place_id": new["id"]},
    )
    public = await api.request("GET", f"/notes/{note_id}", actor=author)
    assert public["place"]["id"] == new["id"]
    assert (
        await db.scalar(
            "SELECT place_id FROM note_submissions WHERE id=:id", {"id": submitted["submission_id"]}
        )
        == old["id"]
    )
    assert public["published_at"].endswith("Z")


async def test_public_contract_exposes_two_distinct_content_schemas(api):
    schema = (await api.client.get("/openapi.json")).json()
    objects = schema["components"]["schemas"]
    assert "body_text" in objects["Note"]["properties"]
    assert "document" not in objects["Note"]["properties"]
    assert "document" in objects["Editorial"]["properties"]
    assert "district" in objects["Editorial"]["properties"]
    assert "email_ciphertext" not in objects["User"]["properties"]


async def test_smtp_unknown_prior_send_is_not_repeated(api, db):
    from marcus.jobs.worker import claim_job, execute_job

    _, challenge_id, _ = await api.challenge()
    await db.execute(
        "UPDATE auth_challenges SET delivery_status='sending' WHERE id=:id", {"id": challenge_id}
    )
    job = await claim_job("replacement-worker")
    await execute_job(job)
    assert await db.scalar("SELECT status FROM jobs WHERE id=:id", {"id": job["id"]}) == "failed"
    assert (
        await db.scalar(
            "SELECT delivery_code_ciphertext FROM auth_challenges WHERE id=:id", {"id": challenge_id}
        )
        is None
    )


async def test_commit_failure_returns_error_and_rolls_back(api, db, monkeypatch):
    from sqlalchemy.exc import OperationalError
    from sqlalchemy.ext.asyncio import AsyncSession

    editor = await api.login("editor")
    tag = await api.request(
        "POST",
        "/admin/tags",
        actor=editor,
        body={"slug": "commit-check", "name": "原名称"},
        status=201,
    )

    async def failed_commit(session):
        # Flush first so rollback must undo a real database write.
        await session.flush()
        raise OperationalError("COMMIT", {}, Exception(1213, "simulated deadlock"))

    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "commit", failed_commit)
        result = await api.request(
            "PATCH",
            f"/admin/tags/{tag['id']}",
            actor=editor,
            body={"name": "不应保存"},
            status=409,
        )
    assert result["error"]["code"] == "concurrent_update"
    assert await db.scalar("SELECT name FROM tags WHERE id=:id", {"id": tag["id"]}) == "原名称"
