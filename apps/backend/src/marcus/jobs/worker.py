"""MySQL leased work queue. Run with python -m marcus.jobs.worker."""

import asyncio
import io
import json
import logging
import os
import socket
import subprocess
import tempfile
from datetime import timedelta
from email.message import EmailMessage
from pathlib import Path
from uuid import uuid4

import aiosmtplib
from PIL import Image, ImageOps
from sqlalchemy import delete, select, update

from marcus.core.common import data, enqueue
from marcus.core.config import settings
from marcus.core.db import SessionFactory
from marcus.core.security import decrypt, now
from marcus.database import models as m
from marcus.media.api import referenced, storage

log = logging.getLogger("marcus.worker")


async def claim_job(owner, lease_seconds=None):
    """Return one job snapshot; claim transaction ends before external work begins."""
    lease_seconds = lease_seconds or settings.lease_seconds
    async with SessionFactory.begin() as db:
        # Separate index-ordered ranges avoid filesort locking every candidate before LIMIT.
        # This matters on a small queue too: MySQL can otherwise choose a full table scan.
        job = None
        for state, time_column in (("running", m.Job.lease_until), ("queued", m.Job.available_at)):
            columns = ["status", time_column.key]
            if state == "queued":
                columns.append("id")
            index = next(index for index in m.Job.__table__.indexes if list(index.columns.keys()) == columns)
            query = (
                select(m.Job)
                .with_hint(m.Job, f"FORCE INDEX (`{index.name}`)", dialect_name="mysql")
                .where(m.Job.status == state, time_column <= now())
                .order_by(time_column, m.Job.id)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            job = await db.scalar(query)
            if job is not None:
                break
        if not job:
            return None
        if job.attempts >= job.max_attempts:
            job.status = "failed"
            job.finished_at = now()
            job.last_error_code = "attempt_limit"
            return None
        job.status = "running"
        job.attempts += 1
        job.lease_owner = owner
        job.lease_until = now() + timedelta(seconds=lease_seconds)
        await db.flush()
        return data(job)


async def renew_job(id, owner, lease_seconds=None):
    async with SessionFactory.begin() as db:
        result = await db.execute(
            update(m.Job)
            .where(
                m.Job.id == id,
                m.Job.status == "running",
                m.Job.lease_owner == owner,
                m.Job.lease_until > now(),
            )
            .values(lease_until=now() + timedelta(seconds=lease_seconds or settings.lease_seconds))
        )
        return bool(result.rowcount)


async def finish_job(id, owner, error_code=None, retry=True):
    async with SessionFactory.begin() as db:
        job = await db.scalar(select(m.Job).where(m.Job.id == id).with_for_update())
        if (
            not job
            or job.status != "running"
            or job.lease_owner != owner
            or not job.lease_until
            or job.lease_until <= now()
        ):
            return False
        job.last_error_code = error_code
        if error_code and retry and job.attempts < job.max_attempts:
            job.status = "queued"
            job.available_at = now() + timedelta(seconds=min(60, 2**job.attempts))
        else:
            job.status = "failed" if error_code else "succeeded"
            job.finished_at = now()
            if error_code and job.kind == "process_media":
                asset = await db.scalar(
                    select(m.MediaAsset).where(m.MediaAsset.id == job.target_id).with_for_update()
                )
                if asset and asset.status == "processing":
                    asset.status = "rejected"
                    asset.rejection_code = "media_processing_failed"
        job.lease_owner = None
        job.lease_until = None
        return True


async def lease_guard(db, job):
    live = await db.scalar(select(m.Job).where(m.Job.id == job["id"]).with_for_update())
    return bool(
        live
        and live.status == "running"
        and live.lease_owner == job["lease_owner"]
        and live.lease_until > now()
    )


async def heartbeat(job, stop):
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=max(1, settings.lease_seconds // 3))
        except asyncio.TimeoutError:
            if not await renew_job(job["id"], job["lease_owner"]):
                return


def put_image(client, key, image):
    image = image.convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=88, optimize=True)
    client.put_object(Bucket=settings.s3_bucket, Key=key, Body=buffer.getvalue(), ContentType="image/jpeg")
    return {"storage_key": key, "width": image.width, "height": image.height, "mime_type": "image/jpeg"}


def process_file(asset):
    """Use private fixed output keys; no arbitrary remote URLs or shell commands."""
    client = storage()
    response = client.get_object(Bucket=settings.s3_bucket, Key=asset["storage_key"])
    cap = 20 * 1024 * 1024 if asset["kind"] == "image" else 200 * 1024 * 1024
    if response["ContentLength"] > cap:
        raise ValueError("media_too_large")
    with tempfile.TemporaryDirectory(prefix="marcus-media-") as folder:
        original = Path(folder) / "original"
        size = 0
        with original.open("wb") as dest:
            while chunk := response["Body"].read(1024 * 1024):
                size += len(chunk)
                if size > cap:
                    raise ValueError("media_too_large")
                dest.write(chunk)
        if size != asset["size_bytes"]:
            raise ValueError("media_size_mismatch")
        prefix = "derived/" + asset["id"]
        variants = {}
        if asset["kind"] == "image":
            with Image.open(original) as image:
                if image.format not in ("JPEG", "PNG", "WEBP"):
                    raise ValueError("unsupported_image_format")
                mime = Image.MIME[image.format]
                if image.width * image.height > 40_000_000:
                    raise ValueError("image_dimensions_too_large")
                image.load()
                image = ImageOps.exif_transpose(image)
                width, height = image.size
                for name, bound in [("thumb", 320), ("feed", 800), ("detail", 2000)]:
                    copy = image.copy()
                    copy.thumbnail((bound, bound))
                    variants[name] = put_image(client, f"{prefix}/{name}.jpg", copy)
            return {
                "width": width,
                "height": height,
                "verified_mime": mime,
                "variants": variants,
                "size_bytes": size,
            }
        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-protocol_whitelist",
                "file,pipe",
                "-f",
                "mov",
                "-show_format",
                "-show_streams",
                "-of",
                "json",
                str(original),
            ],
            capture_output=True,
            check=True,
            timeout=30,
        )
        metadata = json.loads(probe.stdout)
        fmt = metadata["format"]
        duration = float(fmt.get("duration", 0))
        streams = metadata["streams"]
        video = next((s for s in streams if s["codec_type"] == "video"), None)
        if (
            not video
            or not 0 < duration <= 300
            or not set(fmt.get("format_name", "").split(",")) & {"mov", "mp4"}
        ):
            raise ValueError("unsupported_video")
        if int(video["width"]) * int(video["height"]) > 3840 * 2160:
            raise ValueError("video_dimensions_too_large")
        output = Path(folder) / "playback.mp4"
        poster = Path(folder) / "poster.jpg"
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-protocol_whitelist",
                "file,pipe",
                "-f",
                "mov",
                "-i",
                str(original),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0?",
                "-vf",
                "scale='min(1280,iw)':-2",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "24",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-movflags",
                "+faststart",
                "-map_metadata",
                "-1",
                str(output),
            ],
            capture_output=True,
            check=True,
            timeout=600,
        )
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-protocol_whitelist",
                "file,pipe",
                "-f",
                "mov",
                "-i",
                str(output),
                "-frames:v",
                "1",
                str(poster),
            ],
            capture_output=True,
            check=True,
            timeout=30,
        )
        client.upload_file(
            str(output), settings.s3_bucket, f"{prefix}/playback.mp4", ExtraArgs={"ContentType": "video/mp4"}
        )
        with Image.open(poster) as image:
            variants["poster"] = put_image(client, f"{prefix}/poster.jpg", image)
            width, height = image.size
        variants["playback"] = {
            "storage_key": f"{prefix}/playback.mp4",
            "width": width,
            "height": height,
            "mime_type": "video/mp4",
            "duration_ms": int(duration * 1000),
        }
        return {
            "width": width,
            "height": height,
            "duration_ms": int(duration * 1000),
            "verified_mime": "video/mp4",
            "variants": variants,
            "size_bytes": size,
        }


async def process_media(job):
    async with SessionFactory() as db:
        asset = await db.get(m.MediaAsset, job["target_id"])
        if not asset or asset.status == "deleted":
            return
        if asset.status == "ready":
            return
        if asset.status != "processing":
            raise ValueError("media_not_processing")
        snapshot = data(asset)
    try:
        result = await asyncio.to_thread(process_file, snapshot)
    except (ValueError, Image.UnidentifiedImageError, Image.DecompressionBombError) as exc:
        async with SessionFactory.begin() as db:
            if not await lease_guard(db, job):
                return
            asset = await db.scalar(
                select(m.MediaAsset).where(m.MediaAsset.id == job["target_id"]).with_for_update()
            )
            if asset and asset.status != "deleted":
                asset.status = "rejected"
                asset.rejection_code = str(exc)[:80]
        return
    async with SessionFactory.begin() as db:
        if not await lease_guard(db, job):
            return
        asset = await db.scalar(
            select(m.MediaAsset).where(m.MediaAsset.id == job["target_id"]).with_for_update()
        )
        if not asset or asset.status == "deleted":
            return
        for k, v in result.items():
            setattr(asset, k, v)
        asset.status = "ready"
        asset.rejection_code = None


async def send_email(job):
    uncertain = False
    async with SessionFactory.begin() as db:
        if not await lease_guard(db, job):
            return
        c = await db.scalar(
            select(m.AuthChallenge).where(m.AuthChallenge.id == job["target_id"]).with_for_update()
        )
        if (
            not c
            or c.consumed_at
            or c.expires_at <= now()
            or not c.delivery_code_ciphertext
            or c.delivery_status == "sent"
        ):
            return
        if c.delivery_status in ("sending", "failed"):
            c.delivery_status = "failed"
            c.delivery_code_ciphertext = None
            uncertain = True
        else:
            email = decrypt(c.email_ciphertext)
            code = decrypt(c.delivery_code_ciphertext)
            # Commit intent before SMTP. A reclaimed job never repeats an uncertain send.
            c.delivery_status = "sending"
    if uncertain:
        raise RuntimeError("email_delivery_uncertain")
    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = email
    message["Subject"] = "Marcus 邮箱验证码"
    message["Message-ID"] = f"<{job['id']}@marcus.local>"
    message.set_content(f"您的 Marcus 验证码为 {code}，5分钟内有效。如非本人操作，请忽略此邮件。")
    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username or None,
            password=settings.smtp_password or None,
            start_tls=settings.smtp_starttls,
            timeout=20,
        )
    except Exception:
        # SMTP cannot promise idempotent delivery after an uncertain network failure.
        async with SessionFactory.begin() as db:
            if await lease_guard(db, job):
                c = await db.get(m.AuthChallenge, job["target_id"])
                c.delivery_status = "failed"
                c.delivery_code_ciphertext = None
        raise RuntimeError("email_delivery_uncertain")
    async with SessionFactory.begin() as db:
        if not await lease_guard(db, job):
            return
        c = await db.get(m.AuthChallenge, job["target_id"])
        c.delivery_status = "sent"
        c.delivery_code_ciphertext = None


async def review(job):
    from fastapi import HTTPException

    from marcus.contracts.schemas import DecisionInput
    from marcus.editorials.api import article_validate
    from marcus.moderation.api import decide_note
    from marcus.notes.api import validate_submission

    async with SessionFactory.begin() as db:
        if not await lease_guard(db, job):
            return
        if job["kind"] == "review_note":
            sub = await db.get(m.NoteSubmission, job["target_id"])
            if not sub:
                raise ValueError("note_submission_not_found")
            if sub.status != "pending":
                return
            n = await db.get(m.Note, sub.note_id)
            try:
                await validate_submission(db, n, sub)
            except HTTPException as exc:
                sub.automated_findings = {"status": "needs_attention", "code": exc.detail["code"]}
                return
            sub.automated_findings = {
                "structural_validation": "passed",
                "requires_human_review": not settings.auto_approve_notes,
            }
            if settings.auto_approve_notes:
                await decide_note(
                    db,
                    sub.id,
                    DecisionInput(decision="approve", expected_review_version=sub.review_version),
                    None,
                )
        else:
            r = await db.get(m.EditorReview, job["target_id"])
            if not r or job["payload"].get("revision_id") != r.revision_id:
                raise ValueError("editorial_review_target_mismatch")
            if r.status != "pending":
                return
            rev = await db.get(m.EditorRevision, r.revision_id)
            a = await db.get(m.EditorArticle, rev.article_id)
            u = await db.get(m.User, rev.submitted_by)
            try:
                await article_validate(db, a, rev, u, True)
            except HTTPException as exc:
                r.automated_findings = {"status": "needs_attention", "code": exc.detail["code"]}
                return
            r.automated_findings = {"structural_validation": "passed", "requires_human_review": True}


async def cleanup(job):
    kind = job["payload"].get("type")
    id = job["target_id"]
    async with SessionFactory.begin() as db:
        if not await lease_guard(db, job):
            return
        if kind == "media":
            asset = await db.scalar(select(m.MediaAsset).where(m.MediaAsset.id == id).with_for_update())
            if not asset:
                return
            if await referenced(db, id):
                raise ValueError("media_still_referenced")
            keys = [asset.storage_key] + [v["storage_key"] for v in asset.variants.values()]
            await asyncio.to_thread(
                storage().delete_objects,
                Bucket=settings.s3_bucket,
                Delete={"Objects": [{"Key": key} for key in keys]},
            )
            asset.status = "deleted"
            asset.deleted_at = asset.deleted_at or now()
            asset.variants = {}
        elif kind in ("note", "editor_article", "user"):
            # Hide immediately, retain snapshots for 30 days, then erase private payloads.
            cutoff = now() - timedelta(days=30)
            if kind == "user":
                u = await db.get(m.User, id)
                if not u or u.status != "deleted":
                    return
                if u.deleted_at > cutoff:
                    raise RetainUntil(u.deleted_at + timedelta(days=30))
                note_ids = list((await db.scalars(select(m.Note.id).where(m.Note.author_id == id))).all())
                article_ids = list(
                    (
                        await db.scalars(select(m.EditorArticle.id).where(m.EditorArticle.author_id == id))
                    ).all()
                )
            else:
                note_ids = [id] if kind == "note" else []
                article_ids = [id] if kind == "editor_article" else []
            for nid in note_ids:
                n = await db.get(m.Note, nid)
                if not n or n.status != "deleted":
                    continue
                if n.deleted_at > cutoff:
                    raise RetainUntil(n.deleted_at + timedelta(days=30))
                await db.execute(delete(m.NoteImage).where(m.NoteImage.note_id == nid))
                await db.execute(delete(m.NoteDraft).where(m.NoteDraft.note_id == nid))
                await db.execute(
                    update(m.NoteSubmission)
                    .where(m.NoteSubmission.note_id == nid)
                    .values(title="", body_text="", image_ids=[])
                )
                n.title = ""
                n.body_text = ""
            for aid in article_ids:
                a = await db.get(m.EditorArticle, aid)
                if not a or a.status != "deleted":
                    continue
                if a.deleted_at > cutoff:
                    raise RetainUntil(a.deleted_at + timedelta(days=30))
                rev_ids = select(m.EditorRevision.id).where(m.EditorRevision.article_id == aid)
                await db.execute(
                    delete(m.EditorRevisionAsset).where(m.EditorRevisionAsset.revision_id.in_(rev_ids))
                )
                await db.execute(delete(m.EditorDraft).where(m.EditorDraft.article_id == aid))
                await db.execute(
                    update(m.EditorRevision)
                    .where(m.EditorRevision.article_id == aid)
                    .values(
                        document={"type": "doc", "content": []},
                        plain_text="",
                        title="",
                        subtitle="",
                        summary="",
                        cover_asset_id=None,
                    )
                )
        else:
            raise ValueError("unknown_cleanup_type")


class RetainUntil(Exception):
    def __init__(self, when):
        self.when = when


async def execute_job(job):
    stop = asyncio.Event()
    beat = asyncio.create_task(heartbeat(job, stop))
    error = None
    retry = True
    try:
        if job["kind"] == "process_media":
            await process_media(job)
        elif job["kind"] == "send_verification_email":
            await send_email(job)
        elif job["kind"] in ("review_note", "review_editorial"):
            await review(job)
        elif job["kind"] == "cleanup":
            await cleanup(job)
        else:
            raise ValueError("unsupported_job_kind")
    except RetainUntil as exc:
        async with SessionFactory.begin() as db:
            if await lease_guard(db, job):
                row = await db.get(m.Job, job["id"])
                row.status = "queued"
                row.available_at = exc.when
                row.attempts -= 1
                row.lease_owner = None
                row.lease_until = None
        return
    except Exception as exc:
        error = str(exc)[:80] if isinstance(exc, (ValueError, RuntimeError)) else type(exc).__name__
        retry = job["kind"] != "send_verification_email"
        log.warning("job %s kind=%s failed code=%s", job["id"], job["kind"], error)
    finally:
        stop.set()
        await beat
    await finish_job(job["id"], job["lease_owner"], error, retry)


async def run_once(owner=None):
    job = await claim_job(owner or socket.gethostname() + ":" + str(uuid4()))
    if not job:
        return False
    await execute_job(job)
    return True


async def sweep_retention():
    """Bounded maintenance; references are checked while holding each media row lock."""
    timestamp = now()
    async with SessionFactory.begin() as db:
        # Remove expired challenge secrets within 24h, even if no email worker handled them.
        await db.execute(
            delete(m.AuthChallenge).where(m.AuthChallenge.expires_at < timestamp - timedelta(hours=1))
        )
        await db.execute(
            delete(m.AuthSendLimit).where(m.AuthSendLimit.next_allowed_at < timestamp - timedelta(days=1))
        )
        await db.execute(delete(m.IdempotencyRecord).where(m.IdempotencyRecord.expires_at < timestamp))
        await db.execute(
            delete(m.Job).where(
                m.Job.status == "succeeded", m.Job.finished_at < timestamp - timedelta(days=7)
            )
        )
    last_id = ""
    while True:
        async with SessionFactory() as db:
            ids = list(
                (
                    await db.scalars(
                        select(m.MediaAsset.id)
                        .where(
                            m.MediaAsset.id > last_id,
                            m.MediaAsset.created_at < timestamp - timedelta(days=1),
                            m.MediaAsset.status.in_(["pending", "ready", "rejected"]),
                        )
                        .order_by(m.MediaAsset.id)
                        .limit(100)
                    )
                ).all()
            )
        if not ids:
            break
        for asset_id in ids:
            async with SessionFactory.begin() as db:
                asset = await db.scalar(
                    select(m.MediaAsset).where(m.MediaAsset.id == asset_id).with_for_update()
                )
                if asset.status not in ("pending", "ready", "rejected") or await referenced(db, asset_id):
                    continue
                asset.status = "deleted"
                asset.deleted_at = timestamp
                await enqueue(db, "cleanup", asset_id, {"type": "media"})
        last_id = ids[-1]


async def run():
    owner = socket.gethostname() + ":" + str(os.getpid()) + ":" + str(uuid4())
    next_sweep = 0.0
    while True:
        try:
            if asyncio.get_running_loop().time() >= next_sweep:
                await sweep_retention()
                next_sweep = asyncio.get_running_loop().time() + 60
            if not await run_once(owner):
                await asyncio.sleep(settings.worker_poll_seconds)
        except Exception:
            log.exception("worker iteration failed")
            await asyncio.sleep(2)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
