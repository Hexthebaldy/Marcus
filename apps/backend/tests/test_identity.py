import asyncio
from datetime import timedelta
from uuid import uuid4

import jwt
import pytest


async def test_expired_access_token_is_rejected_before_using_claims(api):
    from marcus.core.config import settings
    from marcus.core.security import now

    actor = await api.login()
    token = jwt.encode(
        {
            "sub": actor.id,
            "sid": actor.session_id,
            "iss": "marcus",
            "aud": "marcus-api",
            "iat": now() - timedelta(hours=1),
            "exp": now() - timedelta(seconds=1),
        },
        settings.secret_key,
        algorithm="HS256",
    )
    response = await api.client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_access_token"


@pytest.mark.parametrize("missing", ["session", "user"])
async def test_valid_access_token_referencing_missing_record_is_rejected(api, missing):
    from marcus.core.security import access_token

    actor = await api.login()
    token = access_token(
        str(uuid4()) if missing == "user" else actor.id,
        str(uuid4()) if missing == "session" else actor.session_id,
    )
    response = await api.client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "session_inactive"


async def test_challenge_does_not_register_and_can_be_consumed_once(api, db):
    email, challenge_id, code = await api.challenge("Reader.Name+festival@EXAMPLE.COM")
    assert await db.scalar("SELECT COUNT(*) FROM users") == 0
    responses = await asyncio.gather(api.verify(challenge_id, code), api.verify(challenge_id, code))
    assert sum(r.status_code == 200 for r in responses) == 1
    assert all(r.status_code in (200, 400, 401, 409, 422) for r in responses)
    assert await db.scalar("SELECT COUNT(*) FROM users") == 1
    assert await db.scalar("SELECT COUNT(*) FROM auth_sessions") == 1
    assert await db.scalar("SELECT consumed_at FROM auth_challenges WHERE id=:id", {"id": challenge_id})
    from marcus.core.security import decrypt

    stored = await db.scalar("SELECT email_ciphertext FROM users")
    assert decrypt(stored) == "Reader.Name+festival@example.com"
    assert email == "Reader.Name+festival@EXAMPLE.COM"


async def test_wrong_code_attempts_persist_and_limit_locks_out_correct_code(api, db):
    _, challenge_id, code = await api.challenge()
    wrong = "000000" if code != "000000" else "111111"
    for attempt in range(1, 6):
        response = await api.verify(challenge_id, wrong)
        assert 400 <= response.status_code < 500, response.text
        assert (
            await db.scalar("SELECT attempts FROM auth_challenges WHERE id=:id", {"id": challenge_id})
            == attempt
        )
    response = await api.verify(challenge_id, code)
    assert 400 <= response.status_code < 500
    assert await db.scalar("SELECT COUNT(*) FROM users") == 0


async def test_expired_code_cannot_register(api, db):
    _, challenge_id, code = await api.challenge()
    await db.execute(
        "UPDATE auth_challenges SET expires_at=UTC_TIMESTAMP(6)-INTERVAL 1 SECOND WHERE id=:id",
        {"id": challenge_id},
    )
    response = await api.verify(challenge_id, code)
    assert 400 <= response.status_code < 500
    assert await db.scalar("SELECT COUNT(*) FROM users") == 0


async def test_database_resend_guard_and_new_code_invalidates_old(api, db):
    email, first, old_code = await api.challenge()
    response = await api.client.post(
        "/v1/auth/challenges", json={"email": email, "purpose": "login", "terms_version": "2026-09-25"}
    )
    assert response.status_code == 429, response.text
    await db.execute("UPDATE auth_send_limits SET next_allowed_at=UTC_TIMESTAMP(6)-INTERVAL 1 SECOND")
    _, second, new_code = await api.challenge(email)
    assert first != second
    assert 400 <= (await api.verify(first, old_code)).status_code < 500
    assert (await api.verify(second, new_code)).status_code == 200


async def test_refresh_rotation_and_reuse_revoke_session(api, db):
    actor = await api.login()
    result = await api.request("POST", "/auth/refresh", body={"refresh_token": actor.refresh_token})
    assert result["refresh_token"] != actor.refresh_token
    reused = await api.client.post("/v1/auth/refresh", json={"refresh_token": actor.refresh_token})
    assert reused.status_code == 401, reused.text
    response = await api.client.get("/v1/me", headers={"Authorization": f"Bearer {result['access_token']}"})
    assert response.status_code == 401, response.text
    assert await db.scalar("SELECT revoked_at FROM auth_sessions WHERE id=:id", {"id": actor.session_id})


async def test_logout_revokes_access_and_refresh(api):
    actor = await api.login()
    response = await api.client.post("/v1/auth/logout", headers=actor.headers)
    assert response.status_code in (200, 204), response.text
    assert (await api.client.get("/v1/me", headers=actor.headers)).status_code == 401
    assert (
        await api.client.post("/v1/auth/refresh", json={"refresh_token": actor.refresh_token})
    ).status_code == 401


async def test_delete_account_challenge_cannot_be_used_for_login(api, db):
    actor = await api.login()
    _, challenge_id, code = await api.challenge(actor.email, purpose="delete_account", actor=actor)
    response = await api.verify(challenge_id, code)
    assert 400 <= response.status_code < 500
    assert await db.scalar("SELECT COUNT(*) FROM auth_sessions") == 1
    assert (await api.client.get("/v1/me", headers=actor.headers)).status_code == 200


@pytest.mark.parametrize("extra", [{"phone": "13800000000"}, {"password": "not-supported"}])
async def test_login_rejects_phone_and_password_fields(api, extra):
    response = await api.client.post(
        "/v1/auth/challenges",
        json={"email": "reader@example.com", "purpose": "login", "terms_version": "2026-09-25", **extra},
    )
    assert response.status_code == 422, response.text


async def test_regular_user_cannot_access_editor_or_review_management(api, location):
    actor = await api.login()
    for path in ("/admin/editorials", "/admin/note-submissions", "/admin/editorial-reviews"):
        response = await api.client.get(f"/v1{path}", headers=actor.headers)
        assert response.status_code == 403, response.text
    response = await api.client.post(
        "/v1/admin/editorials",
        headers={**actor.headers, "Idempotency-Key": "forbidden-creation"},
        json=location,
    )
    assert response.status_code == 403, response.text
