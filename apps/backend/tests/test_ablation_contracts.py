"""Behavioral evidence for removing redundant checks without weakening boundaries."""

import io
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from .helpers import (
    decide_editorial,
    decide_note,
    document,
    new_editorial,
    new_note,
    new_place,
    submit_editorial,
    submit_note,
)
from .test_worker_media import s3_service as s3_service
from .test_worker_media import upload_file


async def test_auth_rejects_invalid_token_without_disguising_programming_errors(api, monkeypatch):
    from marcus.services import authentication_service as auth

    response = await api.client.get("/v1/me", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_access_token"

    def broken_decode(_token):
        raise RuntimeError("decoder programming error")

    monkeypatch.setattr(auth, "decode_token", broken_decode)
    async with AsyncSession() as session:
        with pytest.raises(RuntimeError, match="decoder programming error"):
            await auth.authenticate(session, "Bearer test")


async def test_rate_limit_distinguishes_exhaustion_outage_and_programming_error(api, monkeypatch):
    from redis.exceptions import ConnectionError as RedisConnectionError

    from marcus.core.errors import ServiceError
    from marcus.services import auth_service as identity

    monkeypatch.setattr(identity.settings, "rate_limit_enabled", True)
    redis = AsyncMock()
    monkeypatch.setattr(identity.Redis, "from_url", lambda _url: redis)
    redis.eval.return_value = 21
    with pytest.raises(ServiceError) as exhausted:
        await identity.rate_limit("127.0.0.1")
    assert exhausted.value.status_code == 429
    redis.eval.side_effect = RedisConnectionError("offline")
    with pytest.raises(ServiceError) as offline:
        await identity.rate_limit("127.0.0.1")
    assert offline.value.status_code == 503
    redis.eval.side_effect = RuntimeError("unexpected decoder bug")
    with pytest.raises(RuntimeError, match="unexpected decoder bug"):
        await identity.rate_limit("127.0.0.1")
    assert redis.aclose.await_count == 3


async def test_editor_draft_and_catalog_contracts_are_unambiguous(api, location):
    editor = await api.login("editor")
    created = await api.request(
        "POST", "/admin/editorials", actor=editor, body=location, key=str(uuid4()), status=201
    )
    assert created["article_id"] and created["document"] == {"type": "doc", "content": []}
    assert created["media"] == []
    assert "id" not in created
    draft = await api.request("GET", f"/admin/editorials/{created['article_id']}/draft", actor=editor)
    assert draft["article_id"] == created["article_id"]
    assert draft["document"] == created["document"] and draft["media"] == []
    place = await new_place(api, editor, location)
    detail = await api.request("GET", f"/admin/places/{place['id']}", actor=editor)
    assert detail["district_id"] == location["district_id"]
    assert detail["cover_asset_id"] is None and detail["latitude"] is None and detail["longitude"] is None
    assert detail["gallery"] == []
    await api.request(
        "PATCH",
        f"/admin/places/{place['id']}",
        actor=editor,
        body={"expected_version": place["version"], "latitude": 31.2304, "longitude": 121.4737},
    )
    positioned = await api.request("GET", f"/admin/places/{place['id']}", actor=editor)
    assert float(positioned["latitude"]) == 31.2304
    assert float(positioned["longitude"]) == 121.4737
    event = await api.request(
        "POST",
        "/admin/events",
        actor=editor,
        status=201,
        body={
            "city_id": location["city_id"],
            "title": "展览",
            "place_id": place["id"],
            "price_status": "known",
            "price_min_fen": 5000,
            "price_max_fen": 9000,
        },
    )
    detail = await api.request("GET", f"/admin/events/{event['id']}", actor=editor)
    assert detail["place_id"] == place["id"]
    assert (detail["price_status"], detail["price_min_fen"], detail["price_max_fen"]) == ("known", 5000, 9000)
    assert "price" not in detail


async def test_invalid_document_and_video_place_images_remain_rejected(api, location, asset_factory):
    editor = await api.login("editor")
    place = await new_place(api, editor, location)
    article_id, draft = await new_editorial(api, editor, location, place_id=place["id"])
    await api.request(
        "PATCH",
        f"/admin/editorials/{article_id}/draft",
        actor=editor,
        status=422,
        body={
            "expected_version": draft["edit_version"],
            "document": {"type": "doc", "content": [{"type": "script"}]},
        },
    )
    retained = await api.request("GET", f"/admin/editorials/{article_id}/draft", actor=editor)
    assert retained["document"] == draft["document"]
    video = await asset_factory(editor, kind="video", purpose="editorial_media")
    for endpoint, method, fields in (
        (f"/admin/places/{place['id']}", "PATCH", {"cover_asset_id": video}),
        (f"/admin/places/{place['id']}/images", "PUT", {"asset_ids": [video]}),
    ):
        await api.request(
            method, endpoint, actor=editor, status=403, body={"expected_version": place["version"], **fields}
        )
    unchanged = await api.request("GET", f"/admin/places/{place['id']}", actor=editor)
    assert unchanged["cover_asset_id"] is None and unchanged["gallery"] == []


async def test_editorial_venue_tracks_event_move_and_text_keeps_whitespace(api, location):
    editor, moderator = await api.login("editor"), await api.login("moderator")
    old, new = await new_place(api, editor, location, "旧址"), await new_place(api, editor, location, "新址")
    event = await api.request(
        "POST",
        "/admin/events",
        actor=editor,
        status=201,
        body={"city_id": location["city_id"], "title": "展览", "place_id": old["id"], "status": "published"},
    )
    text = "  前后空格\n换行保留  "
    note_id, draft = await new_note(api, editor, location["city_id"], text)
    assert draft["body_text"] == text
    article_id, draft = await new_editorial(api, editor, location, event_id=event["id"], text=text)
    assert draft["document"] == document(text)
    submission = await submit_editorial(api, editor, article_id, draft)
    await decide_editorial(api, moderator, submission["revision_id"])
    await api.request(
        "PATCH",
        f"/admin/events/{event['id']}",
        actor=editor,
        body={"expected_version": event["version"], "place_id": new["id"]},
    )
    public = await api.request("GET", f"/editorials/{article_id}", actor=editor)
    assert public["place"]["id"] == new["id"]
    assert public["event"]["place"]["id"] == new["id"]
    assert public["document"] == document(text)


async def test_moderation_detail_and_report_keep_media_order_and_revision_shape(
    api, db, location, asset_factory
):
    editor, moderator = await api.login("editor"), await api.login("moderator")
    images = [await asset_factory(editor) for _ in range(3)]
    order = [images[2], images[0], images[1]]
    note_id, draft = await new_note(api, editor, location["city_id"])
    draft = await api.request(
        "PATCH",
        f"/notes/{note_id}/draft",
        actor=editor,
        body={"expected_version": draft["edit_version"], "image_ids": order},
    )
    sub = await submit_note(api, editor, note_id, draft)
    review = await api.request("GET", f"/admin/note-submissions/{sub['submission_id']}", actor=moderator)
    assert review["image_ids"] == order and [a["id"] for a in review["media"]] == order
    await decide_note(api, moderator, sub["submission_id"])
    report = await api.request(
        "POST",
        f"/notes/{note_id}/reports",
        actor=moderator,
        status=201,
        body={"reason": "inaccurate", "submission_id": sub["submission_id"]},
    )
    detail = await api.request("GET", f"/admin/note-reports/{report['id']}", actor=moderator)
    assert detail["submission"]["id"] == sub["submission_id"]
    assert [a["id"] for a in detail["submission"]["media"]] == order
    place = await new_place(api, editor, location)
    article_id, draft = await new_editorial(api, editor, location, place_id=place["id"])
    submitted = await submit_editorial(api, editor, article_id, draft)
    review_id = await db.scalar(
        "SELECT id FROM editor_reviews WHERE revision_id=:id", {"id": submitted["revision_id"]}
    )
    review = await api.request("GET", f"/admin/editorial-reviews/{review_id}", actor=moderator)
    assert review["revision"]["id"] == submitted["revision_id"] and review["media"] == []
    await decide_editorial(api, moderator, submitted["revision_id"])
    report = await api.request(
        "POST",
        f"/editorials/{article_id}/reports",
        actor=moderator,
        status=201,
        body={"reason": "inaccurate", "revision_id": submitted["revision_id"]},
    )
    detail = await api.request("GET", f"/admin/editorial-reports/{report['id']}", actor=moderator)
    assert detail["review"]["revision"]["id"] == submitted["revision_id"]
    assert detail["review"]["media"] == []


async def test_rotated_jpeg_keeps_size_orientation_and_removes_exif(api, db, s3_service):
    from marcus.jobs.worker import claim_job, execute_job

    actor = await api.login()
    await db.execute("UPDATE jobs SET status='cancelled' WHERE kind='send_verification_email'")
    image = Image.new("RGB", (600, 1200), color=(120, 60, 200))
    exif = Image.Exif()
    exif[274] = 6
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif)
    asset_id = await upload_file(api, actor, buffer.getvalue(), mime="image/jpeg")
    await execute_job(await claim_job("orientation-worker"))
    asset = await api.request("GET", f"/media/{asset_id}", actor=actor)
    assert asset["status"] == "ready"
    assert (asset["width"], asset["height"]) == (1200, 600)
    async with httpx.AsyncClient() as client:
        result = await client.get(asset["variants"]["thumb"]["url"])
    assert result.status_code == 200
    with Image.open(io.BytesIO(result.content)) as thumb:
        assert thumb.size == (320, 160)
        assert not thumb.getexif()


@pytest.mark.parametrize("failure", ["missing_object", "storage_outage", "programming_error"])
async def test_upload_completion_does_not_label_storage_failures_as_missing_upload(
    api, db, monkeypatch, failure
):
    from unittest.mock import Mock

    from botocore.exceptions import ClientError

    from marcus.main import app
    from marcus.services import media_service as media

    owner = await api.login()
    created = await api.request(
        "POST",
        "/media/uploads",
        actor=owner,
        status=201,
        key=str(uuid4()),
        body={
            "kind": "image",
            "purpose": "note_image",
            "file_name": "upload.jpg",
            "mime_type": "image/jpeg",
            "size_bytes": 123,
        },
    )
    errors = {
        "missing_object": ClientError({"Error": {"Code": "404"}}, "HeadObject"),
        "storage_outage": ClientError({"Error": {"Code": "ServiceUnavailable"}}, "HeadObject"),
        "programming_error": RuntimeError("storage adapter programming error"),
    }
    storage = Mock()
    storage.head_object.side_effect = errors[failure]
    monkeypatch.setattr(media, "storage", lambda: storage)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        response = await client.post(f"/v1/media/{created['asset_id']}/complete", headers=owner.headers)
    assert response.status_code == (422 if failure == "missing_object" else 500)
    assert response.json()["error"]["code"] == (
        "upload_not_found" if failure == "missing_object" else "internal_error"
    )
    assert (
        await db.scalar("SELECT status FROM media_assets WHERE id=:id", {"id": created["asset_id"]})
        == "pending"
    )
