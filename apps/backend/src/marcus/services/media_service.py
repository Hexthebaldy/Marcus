"""媒体上传和访问业务：执行规则检查、数据库操作及相关任务安排；事务由调用方管理。"""

import asyncio
from datetime import timedelta
from uuid import uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from sqlalchemy import select

from marcus import models as m
from marcus import schemas as s
from marcus.core.common import enqueue, fail, get, idempotency, remember, roles
from marcus.core.config import settings
from marcus.core.security import now


def storage(public=False):
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_public_endpoint_url if public else settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key or None,
        aws_secret_access_key=settings.s3_secret_key or None,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def signed(key):
    return storage(True).generate_presigned_url(
        "get_object", Params={"Bucket": settings.s3_bucket, "Key": key}, ExpiresIn=300
    )


async def validate_assets(db, user, ids, purpose, ready=False, kinds=None):
    result = []
    privileged = bool(await roles(db, user.id) & {"editor", "admin"})
    for id in sorted(set(ids)):
        row = await get(db, m.MediaAsset, id, True)
        if purpose in ("note_image", "avatar"):
            allowed = row.owner_id == user.id and row.purpose == purpose and row.kind == "image"
        else:
            allowed = (
                privileged
                and row.purpose in ("editorial_media", "place_image")
                and (row.kind == "image" or purpose == "editorial_media")
            )
        if not allowed or row.status == "deleted":
            fail(403, "media_not_usable")
        if kinds and row.kind != kinds[id]:
            fail(422, "media_kind_mismatch")
        if ready and row.status != "ready":
            fail(422, "media_not_ready")
        result.append(row)
    return result


async def public_asset(db, id):
    checks = [
        select(m.User.id).where(m.User.avatar_asset_id == id, m.User.status == "active"),
        select(m.Place.id).where(m.Place.cover_asset_id == id, m.Place.status.in_(["active", "closed"])),
        select(m.PlaceAsset.asset_id)
        .join(m.Place, m.Place.id == m.PlaceAsset.place_id)
        .where(m.PlaceAsset.asset_id == id, m.Place.status.in_(["active", "closed"])),
        select(m.NoteImage.asset_id)
        .join(m.Note, m.Note.id == m.NoteImage.note_id)
        .join(m.User, m.User.id == m.Note.author_id)
        .where(m.NoteImage.asset_id == id, m.Note.status == "published", m.User.status == "active"),
        select(m.EditorRevisionAsset.asset_id)
        .join(m.EditorArticle, m.EditorArticle.published_revision_id == m.EditorRevisionAsset.revision_id)
        .join(m.User, m.User.id == m.EditorArticle.author_id)
        .where(
            m.EditorRevisionAsset.asset_id == id,
            m.EditorArticle.status == "published",
            m.User.status == "active",
        ),
    ]
    for q in checks:
        if await db.scalar(q.limit(1)):
            return True
    return False


async def media_response(db, row):
    if not row:
        return None
    result = {
        "id": row.id,
        "kind": row.kind,
        "status": row.status,
        "width": row.width,
        "height": row.height,
        "duration_ms": row.duration_ms,
        "variants": {},
        "error_code": row.rejection_code,
    }
    if row.status == "ready":
        for key, v in row.variants.items():
            info = {k: x for k, x in v.items() if k != "storage_key"}
            info.update(
                url=signed(v["storage_key"]), expires_at=(now() + timedelta(minutes=5)).isoformat() + "Z"
            )
            if key in ("playback", "poster"):
                result[key] = info
            else:
                result["variants"][key] = info
    return result


async def referenced(db, id):
    # JSON arrays and documents are private retained references, not public grants.
    for model, field in [
        (m.User, m.User.avatar_asset_id),
        (m.Place, m.Place.cover_asset_id),
        (m.PlaceAsset, m.PlaceAsset.asset_id),
        (m.NoteImage, m.NoteImage.asset_id),
        (m.EditorRevisionAsset, m.EditorRevisionAsset.asset_id),
        (m.EditorDraft, m.EditorDraft.cover_asset_id),
    ]:
        if await db.scalar(select(field).where(field == id).limit(1)):
            return True
    for model, field in [
        (m.NoteDraft, m.NoteDraft.image_ids),
        (m.NoteSubmission, m.NoteSubmission.image_ids),
    ]:
        from sqlalchemy import func

        if await db.scalar(select(model).where(func.JSON_CONTAINS(field, '"' + id + '"')).limit(1)):
            return True
    from sqlalchemy import func

    return bool(
        await db.scalar(
            select(m.EditorDraft.article_id)
            .where(func.JSON_SEARCH(m.EditorDraft.document, "one", id).is_not(None))
            .limit(1)
        )
    )


async def upload(body: s.UploadInput, user, db, idempotency_key: str | None):
    if body.purpose in ("editorial_media", "place_image") and not await roles(db, user.id) & {
        "editor",
        "admin",
    }:
        fail(403, "editor_required")
    record, fingerprint = await idempotency(db, user, "upload", idempotency_key, body.model_dump())
    if record:
        row = await get(db, m.MediaAsset, record.resource_id)
    else:
        id = str(uuid4())
        row = m.MediaAsset(
            id=id,
            owner_id=user.id,
            kind=body.kind,
            purpose=body.purpose,
            storage_key=f"originals/{id}",
            size_bytes=body.size_bytes,
            upload_expires_at=now() + timedelta(minutes=15),
        )
        db.add(row)
        await db.flush()
        await remember(db, user, "upload", idempotency_key, fingerprint, row.id, 201)
    if row.status != "pending" or row.upload_expires_at <= now():
        fail(409, "upload_expired_or_complete")
    url = storage(True).generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": row.storage_key,
            "ContentType": body.mime_type,
            "ContentLength": body.size_bytes,
        },
        ExpiresIn=max(1, int((row.upload_expires_at - now()).total_seconds())),
    )
    return {
        "asset_id": row.id,
        "upload_url": url,
        "method": "PUT",
        "required_headers": {"Content-Type": body.mime_type},
        "expires_at": row.upload_expires_at.isoformat() + "Z",
    }


async def complete(id: str, user, db):
    row = await get(db, m.MediaAsset, id, True)
    if row.owner_id != user.id:
        fail(403, "media_owner_required")
    if row.status in ("processing", "ready"):
        return await media_response(db, row)
    if row.status != "pending" or row.upload_expires_at <= now():
        fail(409, "upload_expired_or_complete")
    try:
        head = await asyncio.to_thread(storage().head_object, Bucket=settings.s3_bucket, Key=row.storage_key)
    except ClientError as exc:
        if exc.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
            fail(422, "upload_not_found")
        raise
    if head["ContentLength"] != row.size_bytes:
        fail(422, "upload_size_mismatch")
    row.status = "processing"
    await enqueue(db, "process_media", row.id)
    return await media_response(db, row)


async def read(id: str, user, db):
    row = await get(db, m.MediaAsset, id)
    team = row.purpose in ("editorial_media", "place_image") and bool(
        await roles(db, user.id) & {"editor", "admin"}
    )
    if row.status == "deleted" or not (row.owner_id == user.id or team or await public_asset(db, id)):
        fail(404, "not_found")
    return await media_response(db, row)


async def remove(id: str, user, db):
    row = await get(db, m.MediaAsset, id, True)
    if row.owner_id != user.id:
        fail(403, "media_owner_required")
    if await referenced(db, id):
        fail(409, "media_in_use")
    row.status = "deleted"
    row.deleted_at = now()
    await enqueue(db, "cleanup", id, {"type": "media"})
