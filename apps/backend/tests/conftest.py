"""HTTP integration fixtures backed exclusively by a disposable MySQL database."""

import os
from dataclasses import dataclass
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url


@pytest.fixture(scope="session", autouse=True)
def test_environment():
    url = os.environ.get("MARCUS_TEST_DATABASE_URL")
    if not url:
        pytest.fail("Set MARCUS_TEST_DATABASE_URL to a dedicated MySQL database ending in _test")
    parsed = make_url(url)
    if parsed.get_backend_name() != "mysql" or not (parsed.database or "").endswith("_test"):
        pytest.fail("Integration tests require a dedicated MySQL *_test database; SQLite is forbidden")
    os.environ["MARCUS_DATABASE_URL"] = url
    os.environ["MARCUS_ENVIRONMENT"] = "test"
    # Redis and external email delivery are outside this suite; database resend guards remain active.
    os.environ["MARCUS_RATE_LIMIT_ENABLED"] = "false"
    os.environ["MARCUS_AUTO_APPROVE_NOTES"] = "false"
    os.environ.setdefault("MARCUS_S3_ACCESS_KEY", "test-access")
    os.environ.setdefault("MARCUS_S3_SECRET_KEY", "test-secret")


@pytest.fixture
async def db(test_environment):
    from marcus.core.db import engine

    database_name = engine.url.database
    assert database_name is not None and database_name.endswith("_test")
    async with engine.begin() as conn:
        version = await conn.scalar(text("SELECT VERSION()"))
        assert "MariaDB" not in version, f"Expected MySQL, found {version}"
        names = (await conn.execute(text("SHOW TABLES"))).scalars().all()
        assert "users" in names, "Run alembic upgrade head on the test database before pytest"
        await conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        try:
            for name in names:
                if name != "alembic_version":
                    await conn.execute(text(f"DELETE FROM `{name}`"))
        finally:
            await conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    yield Database(engine)
    await engine.dispose()


class Database:
    def __init__(self, engine):
        self.engine = engine

    async def execute(self, sql, params=None):
        async with self.engine.begin() as conn:
            return await conn.execute(text(sql), params or {})

    async def rows(self, sql, params=None):
        async with self.engine.connect() as conn:
            return (await conn.execute(text(sql), params or {})).mappings().all()

    async def scalar(self, sql, params=None):
        async with self.engine.connect() as conn:
            return await conn.scalar(text(sql), params or {})


@dataclass
class Identity:
    id: str
    email: str
    access_token: str
    refresh_token: str
    session_id: str

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.access_token}"}


class Api:
    def __init__(self, client, db):
        self.client = client
        self.db = db

    async def request(self, method, path, *, actor=None, body=None, status=200, key=None, **kwargs):
        headers = dict(actor.headers if actor else {})
        if key:
            headers["Idempotency-Key"] = key
        response = await self.client.request(method, f"/v1{path}", headers=headers, json=body, **kwargs)
        assert response.status_code == status, f"{method} {path}: {response.status_code} {response.text}"
        return response.json() if response.content else None

    async def challenge(self, email=None, purpose="login", actor=None):
        from marcus.core.security import decrypt

        email = email or f"reader-{uuid4().hex}@example.com"
        body = {"email": email, "purpose": purpose}
        if purpose == "login":
            body["terms_version"] = "2026-09-25"
        response = await self.client.post(
            "/v1/auth/challenges", json=body, headers=actor.headers if actor else {}
        )
        assert response.status_code in (200, 201, 202), response.text
        payload = response.json()
        assert "code" not in payload and "delivery_code_ciphertext" not in payload
        ciphertext = await self.db.scalar(
            "SELECT delivery_code_ciphertext FROM auth_challenges WHERE id=:id",
            {"id": payload["challenge_id"]},
        )
        return email, payload["challenge_id"], decrypt(ciphertext)

    async def verify(self, challenge_id, code):
        return await self.client.post(
            "/v1/auth/verify",
            json={
                "challenge_id": challenge_id,
                "code": code,
                "device_label": "integration",
                "client_type": "mobile",
            },
        )

    async def login(self, *roles):
        email, challenge_id, code = await self.challenge()
        response = await self.verify(challenge_id, code)
        assert response.status_code == 200, response.text
        result = response.json()
        actor = Identity(
            result["user"]["id"], email, result["access_token"], result["refresh_token"], result["session_id"]
        )
        for role in roles:
            await self.db.execute(
                "INSERT INTO user_roles (user_id, role, granted_by, created_at, updated_at) VALUES (:id,:role,:id,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6))",
                {"id": actor.id, "role": role},
            )
        return actor


@pytest.fixture
async def api(db):
    from marcus.main import app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield Api(client, db)


@pytest.fixture
async def location(db):
    city_id, district_id = str(uuid4()), str(uuid4())
    await db.execute(
        "INSERT INTO cities (id,code,name,country_code,timezone,enabled,created_at,updated_at) "
        "VALUES (:id,:code,'上海','CN','Asia/Shanghai',1,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6))",
        {"id": city_id, "code": f"shanghai-{uuid4().hex[:12]}"},
    )
    await db.execute(
        "INSERT INTO districts (id,city_id,code,name,created_at,updated_at) "
        "VALUES (:id,:city_id,'jingan','静安区',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6))",
        {"id": district_id, "city_id": city_id},
    )
    return {"city_id": city_id, "district_id": district_id}


@pytest.fixture
def asset_factory(db):
    """Create processed-file metadata; this fixture does not claim to test transcoding."""

    async def create(owner, *, kind="image", purpose="note_image", status="ready"):
        from datetime import timedelta

        from marcus.core.db import SessionFactory
        from marcus.core.security import now
        from marcus.models import MediaAsset

        asset_id = str(uuid4())
        if kind == "image":
            variants = {
                name: {"storage_key": f"tests/{asset_id}/{name}.jpg", "width": 640, "height": 480}
                for name in ("thumb", "feed", "detail")
            }
        else:
            variants = {
                "playback": {
                    "storage_key": f"tests/{asset_id}/playback.mp4",
                    "mime_type": "video/mp4",
                    "video_codec": "h264",
                    "audio_codec": "aac",
                },
                "poster": {"storage_key": f"tests/{asset_id}/poster.jpg", "width": 640, "height": 480},
            }
        async with SessionFactory.begin() as session:
            session.add(
                MediaAsset(
                    id=asset_id,
                    owner_id=owner.id,
                    kind=kind,
                    purpose=purpose,
                    storage_key=f"tests/{asset_id}/original",
                    verified_mime="image/jpeg" if kind == "image" else "video/mp4",
                    size_bytes=1234,
                    width=640,
                    height=480,
                    duration_ms=10000 if kind == "video" else None,
                    status=status,
                    visibility="private",
                    variants=variants,
                    upload_expires_at=now() + timedelta(hours=1),
                )
            )
        return asset_id

    return create
