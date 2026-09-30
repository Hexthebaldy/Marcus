import asyncio
import io
import os
import shutil
import subprocess
from email import policy
from email.parser import BytesParser
from uuid import uuid4

import httpx
import pytest
from PIL import Image


@pytest.fixture
async def smtp_receiver(monkeypatch, db):
    """Minimal local SMTP receiver; the real worker uses a real TCP SMTP connection."""
    from marcus.core.config import settings

    received = []

    async def handle(reader, writer):
        writer.write(b"220 localhost test SMTP\r\n")
        await writer.drain()
        try:
            while command := await reader.readline():
                upper = command.upper()
                if upper.startswith((b"EHLO", b"HELO")):
                    writer.write(b"250-localhost\r\n250 SIZE 1048576\r\n")
                elif upper.startswith((b"MAIL", b"RCPT", b"RSET", b"NOOP")):
                    writer.write(b"250 OK\r\n")
                elif upper.startswith(b"DATA"):
                    writer.write(b"354 End with dot\r\n")
                    await writer.drain()
                    lines = []
                    while line := await reader.readline():
                        if line == b".\r\n":
                            break
                        lines.append(line[1:] if line.startswith(b"..") else line)
                    received.append(BytesParser(policy=policy.default).parsebytes(b"".join(lines)))
                    writer.write(b"250 Accepted\r\n")
                elif upper.startswith(b"QUIT"):
                    writer.write(b"221 Bye\r\n")
                    await writer.drain()
                    break
                else:
                    writer.write(b"502 Unsupported\r\n")
                await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    monkeypatch.setattr(settings, "smtp_host", "127.0.0.1")
    monkeypatch.setattr(settings, "smtp_port", server.sockets[0].getsockname()[1])
    monkeypatch.setattr(settings, "smtp_starttls", False)
    monkeypatch.setattr(settings, "smtp_username", "")
    monkeypatch.setattr(settings, "smtp_password", "")
    async with server:
        yield received


async def test_worker_sends_real_smtp_message_then_erases_delivery_secret(api, db, smtp_receiver):
    from marcus.jobs.worker import claim_job, execute_job

    email, challenge_id, code = await api.challenge()
    job = await claim_job("email-worker")
    assert job is not None
    assert job["kind"] == "send_verification_email"
    await execute_job(job)
    assert len(smtp_receiver) == 1
    message = smtp_receiver[0]
    assert str(message["To"]) == email
    assert code in message.get_body(preferencelist=("plain",)).get_content()
    row = (
        await db.rows(
            "SELECT delivery_status,delivery_code_ciphertext,consumed_at FROM auth_challenges WHERE id=:id",
            {"id": challenge_id},
        )
    )[0]
    assert row["delivery_status"] == "sent" and row["delivery_code_ciphertext"] is None
    assert row["consumed_at"] is None
    assert await db.scalar("SELECT status FROM jobs WHERE id=:id", {"id": job["id"]}) == "succeeded"
    # A duplicate invocation must not send a second email.
    await execute_job(job)
    assert len(smtp_receiver) == 1
    assert (await api.verify(challenge_id, code)).status_code == 200


async def test_worker_does_not_send_superseded_verification_code(api, db, smtp_receiver):
    from marcus.jobs.worker import claim_job, execute_job

    email, old_id, old_code = await api.challenge()
    await db.execute("UPDATE auth_send_limits SET next_allowed_at=UTC_TIMESTAMP(6)-INTERVAL 1 SECOND")
    _, new_id, new_code = await api.challenge(email)
    old_job = await claim_job("email-worker")
    assert old_job is not None
    assert old_job["target_id"] == old_id
    await execute_job(old_job)
    assert smtp_receiver == []
    new_job = await claim_job("email-worker")
    assert new_job is not None
    assert new_job["target_id"] == new_id
    await execute_job(new_job)
    assert len(smtp_receiver) == 1
    assert new_code in smtp_receiver[0].get_body(preferencelist=("plain",)).get_content()
    assert 400 <= (await api.verify(old_id, old_code)).status_code < 500


@pytest.fixture
async def s3_service(db):
    if os.environ.get("MARCUS_TEST_S3_ENABLED") != "1":
        pytest.skip("Enable MARCUS_TEST_S3_ENABLED=1 with a local S3-compatible HTTP service")
    from marcus.core.config import settings
    from marcus.media.service import storage

    assert settings.s3_bucket.endswith("-test"), "External media tests require a dedicated *-test bucket"
    client = storage()
    if settings.s3_bucket not in [b["Name"] for b in client.list_buckets()["Buckets"]]:
        client.create_bucket(Bucket=settings.s3_bucket)
    yield client
    # Only files in the explicit dedicated test bucket are removed.
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=settings.s3_bucket):
        keys = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
        if keys:
            client.delete_objects(Bucket=settings.s3_bucket, Delete={"Objects": keys})


async def upload_file(api, actor, content, kind="image", mime="image/png"):
    upload = await api.request(
        "POST",
        "/media/uploads",
        actor=actor,
        body={
            "kind": kind,
            "purpose": "note_image" if kind == "image" else "editorial_media",
            "file_name": "fixture.png" if kind == "image" else "fixture.mp4",
            "mime_type": mime,
            "size_bytes": len(content),
        },
        key=str(uuid4()),
        status=201,
    )
    async with httpx.AsyncClient() as client:
        response = await client.put(upload["upload_url"], headers=upload["required_headers"], content=content)
        assert response.status_code == 200, response.text
    await api.request("POST", f"/media/{upload['asset_id']}/complete", actor=actor, status=202)
    return upload["asset_id"]


async def test_real_image_upload_process_and_signed_download(api, db, s3_service):
    from marcus.jobs.worker import claim_job, execute_job

    actor = await api.login()
    await db.execute("UPDATE jobs SET status='cancelled' WHERE kind='send_verification_email'")
    buffer = io.BytesIO()
    image = Image.new("RGB", (1200, 600), color=(120, 60, 200))
    image.save(buffer, format="PNG")
    asset_id = await upload_file(api, actor, buffer.getvalue())
    job = await claim_job("image-worker")
    assert job is not None
    assert job["kind"] == "process_media" and job["target_id"] == asset_id
    await execute_job(job)
    asset = await api.request("GET", f"/media/{asset_id}", actor=actor)
    assert asset["status"] == "ready", asset
    assert asset["width"] == 1200 and asset["height"] == 600
    assert set(asset["variants"]) == {"thumb", "feed", "detail"}
    async with httpx.AsyncClient() as client:
        downloaded = await client.get(asset["variants"]["thumb"]["url"])
    assert downloaded.status_code == 200
    with Image.open(io.BytesIO(downloaded.content)) as thumb:
        assert thumb.format == "JPEG" and thumb.size == (320, 160)
        assert not thumb.getexif()
    assert await db.scalar("SELECT status FROM jobs WHERE id=:id", {"id": job["id"]}) == "succeeded"


async def test_upload_claimed_image_with_invalid_bytes_is_rejected(api, db, s3_service):
    from marcus.jobs.worker import claim_job, execute_job

    actor = await api.login()
    await db.execute("UPDATE jobs SET status='cancelled' WHERE kind='send_verification_email'")
    asset_id = await upload_file(api, actor, b"this is not a valid PNG image")
    job = await claim_job("image-worker")
    assert job is not None
    await execute_job(job)
    asset = await api.request("GET", f"/media/{asset_id}", actor=actor)
    assert asset["status"] == "rejected"
    assert asset["error_code"]
    assert asset["variants"] == {}


async def test_real_video_upload_transcode_and_poster(api, db, s3_service, tmp_path):
    import json

    from marcus.jobs.worker import claim_job, execute_job

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("Real video processing requires ffmpeg and ffprobe on PATH")
    source = tmp_path / "source.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=160x120:r=10:d=1",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-t",
            "1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(source),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    actor = await api.login("editor")
    await db.execute("UPDATE jobs SET status='cancelled' WHERE kind='send_verification_email'")
    asset_id = await upload_file(api, actor, source.read_bytes(), kind="video", mime="video/mp4")
    job = await claim_job("video-worker")
    assert job is not None
    await execute_job(job)
    asset = await api.request("GET", f"/media/{asset_id}", actor=actor)
    assert asset["status"] == "ready", asset
    assert 500 <= asset["duration_ms"] <= 1500
    assert asset["width"] == 160 and asset["height"] == 120
    assert "playback" in asset and "poster" in asset
    async with httpx.AsyncClient() as client:
        playback = await client.get(asset["playback"]["url"])
        poster = await client.get(asset["poster"]["url"])
    assert playback.status_code == 200 and poster.status_code == 200
    converted = tmp_path / "converted.mp4"
    converted.write_bytes(playback.content)
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(converted)],
        check=True,
        capture_output=True,
        timeout=30,
    )
    codecs = {stream["codec_type"]: stream["codec_name"] for stream in json.loads(probe.stdout)["streams"]}
    assert codecs["video"] == "h264" and codecs["audio"] == "aac"
    with Image.open(io.BytesIO(poster.content)) as preview:
        assert preview.format == "JPEG" and preview.size == (160, 120)
